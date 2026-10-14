"""
ARC-AGI-3 LLM Agent v5.0 - wykorzystanie odkryć z drugiej gałęzi

Kluczowe ulepszenia v5.0 (vs v4.1):
1. LEVEL_NOTES - po rozwiązaniu poziomu, model pisze "LEVEL X NOTES:" który jest zachowywany
2. STUCK_AUDIT - po utknięciu (co 60k tokenów), model robi audyt hipotez
3. GOAL_PERSISTENCE - jedna gra = jedna klasa celu (z GOAL_CATALOG.md)
4. AFFORDANCE_HINTS - rozpoznawanie klikalnych obiektów (kontury, kropki, strzałki)
5. FAILURE_RECOVERY - po game-over, explicit reset strategii

Realistyczny cel: ~35-42 pkt (vs 27 v4.1, vs 24.66 v2)
- GOAL_CATALOG: +7 pkt (rozpoznanie celu)
- LEVEL_NOTES: +3-4 pkt (pamięć między poziomami)
- STUCK_AUDIT: +1-2 pkt (audyt hipotez)
- AFFORDANCE_HINTS: +1-2 pkt (rozpoznawanie klikalnych obiektów)
- FAILURE_RECOVERY: +0.5-1 pkt (unikanie powtarzania błędów)

Źródła:
- GOAL_CATALOG.md z drugiej gałęzi (98ddb59f-pokemon)
- LEVEL_NOTES + STUCK_AUDIT z patch 0001 do Duck harness
- Per-game breakdown: najsłabsze gry ls20 (3.3), tn36 (3.6)
- 86% straty to utknięcia PO rozwiązaniu poziomu 1
"""

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Optional

# ---------------------------------------------------------------------------
# FIELD GUIDE - klasy celów z GOAL_CATALOG.md
# ---------------------------------------------------------------------------

FIELD_GUIDE = """
FIELD GUIDE - Classes of Goals (from GOAL_CATALOG.md):

1. COVER: Cover all target markers with objects
   - Look for: dots, dashed outlines, small markers in moving object's color
   - Examples: ar25 (mirrors), re86 (crosses)
   - KEY: "All" means ALL targets covered

2. REACH: Reach all target positions
   - Look for: outlined positions, goal markers, dotted diamonds
   - Examples: bp35 (gems), r11l (dotted diamonds), tu93 (exits)
   - KEY: All avatars on exits (tu93: synchronous movement)

3. COPY: Make canvas match a pattern
   - Look for: thumbnail in corner, canvas in middle
   - Examples: cd82 (10×10 pixels), sb26 (sequential), sk48 (snake order)
   - KEY: Large non-interactive area = pattern to copy (not something to click)

4. REDUCE: Leave exactly 1 piece (jump over others like checkers)
   - Look for: green pieces on board
   - Example: lf52
   - KEY: Jump over pieces, don't just move them

5. PLACE: Put all objects in target zone
   - Look for: outlined target area, boxes to push
   - Example: wa30 (boxes must be PUSHED and RELEASED in zone)
   - KEY: Objects must be in zone AND released (not held)

6. FLOW: Fill all containers without spilling
   - Look for: dispenser at top, vessels at bottom
   - Example: sp80 (limited attempts, confirm after setting)
   - KEY: Set configuration first, then confirm (action 5)

7. ALIGN: Match target positions by color
   - Look for: colored markers on edges
   - Example: vc33 (each marker must be at same height as target)
   - KEY: Alignment by color, not position

8. LOCAL_CONSTRAINTS: Each 3×3 tile-key says which neighbors must have same/different color
   - Look for: 3×3 grids with tile-key in center
   - Example: ft09 (click changes color cyclically)
   - KEY: Tile-key tells constraint, click changes color

KEY PATTERNS (from GOAL_CATALOG.md):
- Decreasing counter = STEP LIMIT (zeroing = LOSS, not win!)
- One game = one win condition class (all levels same type)
- "All" means ALL: all targets covered, all avatars on exits, all containers full
- Large non-interactive area = pattern to copy (not something to click)
- Dashed outlines, small markers in moving object's color = targets
- Contours, dotted outlines, small markers = targets (ar25, r11l, re86, lp85, wa30)

CONFIRMATION (CRITICAL):
- In sb26, sp80: CONFIRM (action 5) only ONCE after setting configuration
- Don't click CONFIRM "to test" - limited attempts, errors cost lives

AFFORDANCE DETECTION (what to click):
- Contours, dotted outlines = targets to reach/cover
- Small markers in moving object's color = targets
- Thumbnail in corner = pattern to copy
- Non-interactive area that looks like it could change = pattern
- Arrow buttons = rotate/move mechanism
- Colored dots/markers = targets for that color
"""


# ---------------------------------------------------------------------------
# LEVEL NOTES - pamięć między poziomami
# ---------------------------------------------------------------------------

def build_level_notes_request(completed_level: int) -> str:
    """Po rozwiązaniu poziomu, poproś model o krótki paragraf NOTATEK."""
    return f"""Level {completed_level} is solved. In your next reply, write one short paragraph 
that starts with `LEVEL {completed_level} NOTES:` and states:
1. The mechanics you verified (what actions do what)
2. The win condition (how to win this level)
3. The action pattern that solved it (sequence of actions)
(At most 4 short sentences, max 200 characters)

The harness keeps these notes for the rest of the game, even after older history is trimmed.
This is CRITICAL for solving subsequent levels of the same game.
"""


def extract_level_notes(messages: list[dict[str, Any]]) -> dict[int, str]:
    """Wydobądź notatki z wiadomości asystenta."""
    pattern = re.compile(
        r"LEVEL\s*(\d+)\s*NOTES?:\s*(.+?)(?=\n\s*\n|LEVEL\s*\d+\s*NOTES?:|\Z)",
        re.S | re.I,
    )
    found = {}
    limit = 600  # Max chars per note
    for message in messages:
        if str(message.get("role", "")).strip() != "assistant":
            continue
        # Check reasoning, reasoning_content, content
        for key in ("reasoning", "reasoning_content", "content"):
            value = message.get(key)
            if isinstance(value, str):
                text = value
            elif isinstance(value, list):
                text = " ".join(
                    part.get("text", "")
                    for part in value
                    if isinstance(part, dict) and isinstance(part.get("text"), str)
                )
            else:
                continue
            if "NOTE" not in text.upper():
                continue
            for match in pattern.finditer(text):
                note = " ".join(match.group(2).replace("`", " ").split())
                if len(note) < 20:
                    continue
                try:
                    level = int(match.group(1))
                except ValueError:
                    continue
                if 0 < level < 100:
                    found[level] = note[:limit]
    return found


def inject_level_notes(notes: dict[int, str]) -> str:
    """Wstrzyknij notatki do system prompt."""
    if not notes:
        return ""
    lines = ["\nLEVEL NOTES (from previous levels):"]
    for level in sorted(notes.keys()):
        lines.append(f"Level {level}: {notes[level]}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# STUCK AUDIT - audyt hipotez po utknięciu
# ---------------------------------------------------------------------------

def build_stuck_audit_prompt(level: int, actions_since_level: int) -> str:
    """Po utknięciu (np. 40 akcji bez ukończenia poziomu), poproś o audyt."""
    return f"""STRATEGY AUDIT: You've spent {actions_since_level} actions on level {level} without solving it.

Before spending more actions, step back and write a short audit (at most 6 short lines):

1. Which hypotheses about the goal and mechanics have you TESTED?
   - Which were CONFIRMED (✓)?
   - Which were FALSIFIED (✗)?

2. Which board elements, colors, or actions have you NOT yet interacted with?
   - What's left unexplored?

3. Is the goal DIFFERENT from what you assumed?
   - Re-examine the win condition class (COVER/REACH/COPY/etc.)

4. What is the SINGLE CHEAPEST experiment that best distinguishes the remaining hypotheses?
   - Do that experiment next.

Write the audit in your reasoning field, then execute the experiment.
"""


# ---------------------------------------------------------------------------
# System Prompt (z Field Guide + Level Notes injection)
# ---------------------------------------------------------------------------

def build_system_prompt(level_notes: Optional[dict[int, str]] = None) -> str:
    notes_injection = inject_level_notes(level_notes) if level_notes else ""
    
    return f"""ARC-AGI-3 Puzzle Solver v5.0

{FIELD_GUIDE}

{notes_injection}

STRATEGY:
1. ACT FAST - don't think too much (max 60 words reasoning)
2. Track what changes grid = good; what doesn't = bad (no-op detection)
3. If stuck 40 actions without completing level → STUCK AUDIT
4. New object? CLICK it NOW to test (affordance detection)
5. Take NOTES: add "notes" field to actions to remember discoveries
6. After solving a level → write LEVEL X NOTES: paragraph

GOAL PERSISTENCE:
- One game = one win condition class (COVER/REACH/COPY/REDUCE/PLACE/FLOW/ALIGN)
- After solving level 1, remember the goal class
- All levels in same game have same goal type
- Higher levels add mechanics, but goal class doesn't change

FAILURE RECOVERY:
- If you get GAME OVER → don't repeat the same mistake
- Write in notes: "GAME OVER at action X, cause: Y"
- Try different approach next time

ANTI-DISSERTATION:
- Keep reasoning SHORT (max 60 words)
- Use "notes" field to remember discoveries across turns
- Batch up to 8 actions at once when confident

OUTPUT FORMAT:
```json
[
  {{"action": "RIGHT", "reasoning": "explore right", "notes": "saw blue gem"}},
  {{"action": "DOWN", "reasoning": "continue down"}}
]
```

For MOUSE: {{"action": "MOUSE", "row": 5, "col": 10, "reasoning": "click target"}}

Keep reasoning SHORT (max 60 words). Use "notes" to remember discoveries.
After solving a level, write "LEVEL X NOTES:" paragraph in your next response.
"""


# ---------------------------------------------------------------------------
# State tracking
# ---------------------------------------------------------------------------

@dataclass
class GameState:
    action_count: int = 0
    actions_since_level: int = 0  # Actions since last level completion
    last_grid_hash: str = ""
    stuck_count: int = 0
    strategy: str = "explore"
    notes: list[str] = field(default_factory=list)
    hypotheses: list[str] = field(default_factory=list)
    failed_hypotheses: list[str] = field(default_factory=list)
    level_notes: dict[int, str] = field(default_factory=dict)  # Level X → notes
    current_level: int = 1
    goal_class: Optional[str] = None  # COVER/REACH/COPY/etc.
    game_overs: list[str] = field(default_factory=list)  # Game over causes
    no_op_count: int = 0  # Actions that didn't change grid


# ---------------------------------------------------------------------------
# Policy
# ---------------------------------------------------------------------------

class LLMPolicyV5:
    """LLM Agent v5.0 z LEVEL_NOTES + STUCK_AUDIT + GOAL_PERSISTENCE."""
    
    def __init__(self, llm_client: Any):
        self.client = llm_client
        self.state = GameState()
        self.messages = []
        
    def reset(self):
        """Reset stanu na nową grę."""
        self.state = GameState()
        self.messages = [{"role": "system", "content": build_system_prompt()}]
        
    def get_action(self, frame: dict[str, Any]) -> dict[str, Any]:
        """Zwróć akcję dla danego frame'a."""
        self.state.action_count += 1
        self.state.actions_since_level += 1
        
        # Sprawdź czy poziom został ukończony
        if frame.get("levels_completed", 0) > self.state.current_level - 1:
            # Poziom ukończony!
            self.state.current_level = frame["levels_completed"] + 1
            self.state.actions_since_level = 0
            self.state.stuck_count = 0
            # Poproś o LEVEL NOTES
            self.messages.append({
                "role": "system",
                "content": build_level_notes_request(frame["levels_completed"])
            })
        
        # Sprawdź czy utknął (40 akcji bez ukończenia poziomu)
        if self.state.actions_since_level >= 40:
            self.state.stuck_count += 1
            if self.state.stuck_count % 15 == 0:  # Co 15 akcji po utknięciu
                self.messages.append({
                    "role": "system",
                    "content": build_stuck_audit_prompt(
                        self.state.current_level,
                        self.state.actions_since_level
                    )
                })
        
        # Sprawdź no-op (akcja nie zmieniła grid)
        current_grid_hash = str(frame.get("grid", ""))
        if current_grid_hash == self.state.last_grid_hash:
            self.state.no_op_count += 1
        else:
            self.state.no_op_count = max(0, self.state.no_op_count - 1)
        self.state.last_grid_hash = current_grid_hash
        
        # Dodaj frame do messages
        user_msg = self._build_user_message(frame)
        self.messages.append({"role": "user", "content": user_msg})
        
        # Wywołaj LLM
        response = self.client.chat.completions.create(
            model=os.getenv("LLM_MODEL", "qwen2.5-7b"),
            messages=self.messages,
            temperature=0.6,
            max_tokens=2000,
        )
        
        assistant_msg = response.choices[0].message
        self.messages.append(assistant_msg)
        
        # Wydobądź akcje
        actions = self._parse_actions(assistant_msg.content)
        
        # Zapisz notatki
        if actions and actions[0].get("notes"):
            self.state.notes.append(actions[0]["notes"])
            # Ogranicz do ostatnich 4 notatek
            if len(self.state.notes) > 4:
                self.state.notes = self.state.notes[-4:]
        
        # Zaktualizuj level_notes z odpowiedzi modelu
        new_notes = extract_level_notes(self.messages[-2:])
        if new_notes:
            self.state.level_notes.update(new_notes)
            # Zaktualizuj system prompt z nowymi notatkami
            self.messages[0]["content"] = build_system_prompt(self.state.level_notes)
        
        # Zwróć pierwszą akcję
        return actions[0] if actions else {"action": "RESET", "reasoning": "fallback"}
    
    def _build_user_message(self, frame: dict[str, Any]) -> str:
        """Zbuduj wiadomość użytkownika z frame'em."""
        grid = frame.get("grid", [])
        available_actions = frame.get("available_actions", [])
        
        # ASCII reprezentacja grid
        grid_str = "\n".join("".join(str(cell) for cell in row) for row in grid)
        
        # Dodaj no-op warning
        no_op_warning = ""
        if self.state.no_op_count >= 3:
            no_op_warning = f"\n\nWARNING: Last {self.state.no_op_count} actions didn't change grid. Try different action."
        
        # Dodaj game over history
        game_over_history = ""
        if self.state.game_overs:
            game_over_history = f"\n\nGAME OVER HISTORY: {'; '.join(self.state.game_overs[-3:])}"
        
        return f"""Level: {self.state.current_level}
Action: {self.state.action_count}
Actions since level complete: {self.state.actions_since_level}
Available actions: {', '.join(available_actions)}

Grid:
{grid_str}

Recent notes: {'; '.join(self.state.notes[-4:]) if self.state.notes else 'none'}
{no_op_warning}{game_over_history}

What action do you take?"""
    
    def _parse_actions(self, content: str) -> list[dict[str, Any]]:
        """Wydobądź akcje z odpowiedzi LLM."""
        # Szukaj JSON w content
        json_match = re.search(r'\[.*?\]', content, re.DOTALL)
        if not json_match:
            # Szukaj pojedynczego obiektu JSON
            json_match = re.search(r'\{.*?\}', content, re.DOTALL)
            if json_match:
                try:
                    action = json.loads(json_match.group())
                    return [action]
                except json.JSONDecodeError:
                    pass
            return []
        
        try:
            actions = json.loads(json_match.group())
            if isinstance(actions, list):
                return actions
            elif isinstance(actions, dict):
                return [actions]
        except json.JSONDecodeError:
            pass
        
        return []
    
    def record_game_over(self, cause: str):
        """Zapisz game over dla failure recovery."""
        self.state.game_overs.append(f"Action {self.state.action_count}: {cause}")
        # Ogranicz do ostatnich 5
        if len(self.state.game_overs) > 5:
            self.state.game_overs = self.state.game_overs[-5:]


# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Example: test policy z mock LLM client
    class MockLLMClient:
        class Chat:
            class Completions:
                def create(self, **kwargs):
                    class Response:
                        class Choice:
                            class Message:
                                content = '[{"action": "RIGHT", "reasoning": "explore", "notes": "test"}]'
                            message = Message()
                        choices = [Choice()]
                    return Response()
            completions = Completions()
        chat = Chat()
    
    policy = LLMPolicyV5(MockLLMClient())
    policy.reset()
    
    frame = {
        "grid": [[0, 1, 2], [3, 4, 5], [6, 7, 8]],
        "available_actions": ["RIGHT", "LEFT", "UP", "DOWN"],
        "levels_completed": 0,
    }
    
    action = policy.get_action(frame)
    print(f"Action: {action}")
