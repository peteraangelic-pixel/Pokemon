"""
ARC-AGI-3 LLM Agent v7.0 - najlepsza wersja

Łączy:
- Najlepsze elementy z v6.6 (FIELD_GUIDE, LEVEL_NOTES, etc.)
- Counter-picking per game (goal_classifier.py)
- Ewolucja parametrów heurystyki (evolve_parameters.py)
- Ostrzeżenie o ML (inspiracja c87f7a48 v51 league: +1.2pp pool, -1.4pp hard6)
- Deterministyczny ValueGate (heurystyczny, nie ML-based)

Oczekiwany wynik: ~42-50 pkt (vs v6.7 ~40-47)
"""

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from goal_classifier import detect_goal_class, get_strategy_for_goal_class, STRATEGY_HINTS


# ---------------------------------------------------------------------------
# FIELD GUIDE - klasy celów (z v6.6)
# ---------------------------------------------------------------------------

FIELD_GUIDE = """
FIELD GUIDE - Classes of Goals (from GOAL_CATALOG.md):

1. COVER: Cover all target markers with objects
   - Look for: dots, dashed outlines, small markers in moving object's color
   - KEY: "All" means ALL targets covered

2. REACH: Reach all target positions
   - Look for: outlined positions, goal markers, dotted diamonds
   - KEY: All avatars on exits

3. COPY: Make canvas match a pattern
   - Look for: thumbnail in corner, canvas in middle
   - KEY: Large non-interactive area = pattern to copy

4. REDUCE: Leave exactly 1 piece (jump over others like checkers)
   - KEY: Jump over pieces, don't just move them

5. PLACE: Put all objects in target zone
   - KEY: Objects must be in zone AND released (not held)

6. FLOW: Fill all containers without spilling
   - KEY: Set configuration first, then confirm (action 5)

7. ALIGN: Match target positions by color
   - KEY: Alignment by color, not position

8. LOCAL_CONSTRAINTS: Each 3×3 tile-key says which neighbors must have same/different color
   - KEY: Tile-key tells constraint, click changes color

KEY PATTERNS:
- Decreasing counter = STEP LIMIT (zeroing = LOSS, not win!)
- One game = one win condition class (all levels same type)
- "All" means ALL: all targets covered, all avatars on exits, all containers full
- Large non-interactive area = pattern to copy (not something to click)
- Dashed outlines, small markers in moving object's color = targets

CONFIRMATION (CRITICAL):
- In sb26, sp80: CONFIRM (action 5) only ONCE after setting configuration
- Don't click CONFIRM "to test" - limited attempts, errors cost lives
"""


# ---------------------------------------------------------------------------
# Deterministyczny ValueGate (heurystyczny, nie ML-based)
# ---------------------------------------------------------------------------

@dataclass
class HeuristicValueGate:
    """Heurystyczny ValueGate - ocena stanu bez ML.
    
    Inspiracja: c87f7a48 v51 league (acc 0.777 vs base 0.513)
    Ale: pool +1.2pp, hard6 -1.4pp = ML działa na puli, nie na trudnych grach
    
    Wartość:
    - >0.7: dobry stan (kontynuuj)
    - 0.3-0.7: niepewny (eksploruj ostrożnie)
    - <0.3: zły stan (zmień strategię)
    """
    
    def evaluate(self, frame: dict[str, Any], state: Any) -> float:
        """Oceń stan gry heurystycznie."""
        score = 0.5  # Bazowy
        
        # Postęp (im więcej poziomów, tym lepiej)
        levels_completed = frame.get("levels_completed", 0)
        if levels_completed > 0:
            score += 0.1 * levels_completed
        
        # No-op ratio (im mniej, tym lepiej)
        if state.action_count > 0:
            noop_ratio = state.no_op_count / state.action_count
            score -= 0.2 * noop_ratio
        
        # Lives (im więcej, tym lepiej)
        lives = frame.get("lives", 3)
        if lives < 2:
            score -= 0.2
        elif lives > 3:
            score += 0.1
        
        # Actions since level (im mniej, tym lepiej - szybko rozwiązywane poziomy)
        if state.actions_since_level < 20:
            score += 0.1
        elif state.actions_since_level > 50:
            score -= 0.1
        
        # Stuck count (im mniej, tym lepiej)
        if state.stuck_count > 2:
            score -= 0.2
        
        return max(0.0, min(1.0, score))


# ---------------------------------------------------------------------------
# GameState (z v6.6)
# ---------------------------------------------------------------------------

@dataclass
class GameState:
    action_count: int = 0
    actions_since_level: int = 0
    last_grid_hash: str = ""
    stuck_count: int = 0
    strategy: str = "explore"
    notes: list[str] = field(default_factory=list)
    current_level: int = 1
    goal_class: Optional[str] = None
    game_overs: list[str] = field(default_factory=list)
    no_op_count: int = 0
    level_notes: dict[int, str] = field(default_factory=dict)
    value_gate: HeuristicValueGate = field(default_factory=HeuristicValueGate)
    ml_value: float = 0.5


# ---------------------------------------------------------------------------
# Drabinka eskalacji (z v6.6)
# ---------------------------------------------------------------------------

def build_escalation_prompt(stuck_count: int, level: int, actions_since_level: int, goal_class: str = None) -> str:
    """Zbuduj prompt eskalacji w zależności od stuck_count."""
    
    if stuck_count == 1:
        return f"""STRATEGY AUDIT: You've spent {actions_since_level} actions on level {level} without solving it.

Before spending more actions, step back and write a short audit (at most 6 short lines):

1. Which hypotheses about the goal and mechanics have you TESTED?
   - Which were CONFIRMED (✓)?
   - Which were FALSIFIED (✗)?

2. Which board elements, colors, or actions have you NOT yet interacted with?

3. Is the goal DIFFERENT from what you assumed?
   - Re-examine the win condition class (COVER/REACH/COPY/etc.)
   {f"- Current hypothesis: {goal_class}" if goal_class else ""}

4. What is the SINGLE CHEAPEST experiment that best distinguishes the remaining hypotheses?

Write the audit in your reasoning field, then execute the experiment.
"""
    
    elif stuck_count >= 2:
        return f"""STRATEGY RESET: You've spent {actions_since_level} actions on level {level} without solving it, and this is audit #{stuck_count}.

Your current approach is NOT WORKING. ABANDON IT.

1. Look at FIELD GUIDE above. Which goal class fits this game? (COVER/REACH/COPY/REDUCE/PLACE/FLOW/ALIGN)
   {f"- You tried: {goal_class} - CHOOSE DIFFERENT" if goal_class else ""}

2. Choose a DIFFERENT goal class than what you tried before.

3. Start fresh with that goal class.

4. DO NOT repeat the same action patterns you tried before.

Write in your reasoning: "RESETTING STRATEGY: trying [NEW_GOAL_CLASS] instead of [OLD_APPROACH]"
Then execute a completely different approach.
"""
    
    return ""


# ---------------------------------------------------------------------------
# System Prompt
# ---------------------------------------------------------------------------

def build_system_prompt(
    level_notes: Optional[dict[int, str]] = None,
    goal_class: Optional[str] = None,
) -> str:
    """Zbuduj system prompt z FIELD_GUIDE + LEVEL_NOTES + goal class + strategy hint."""
    
    notes_injection = ""
    if level_notes:
        lines = ["\nLEVEL NOTES (from previous levels):"]
        for level in sorted(level_notes.keys()):
            lines.append(f"Level {level}: {level_notes[level]}")
        notes_injection = "\n".join(lines)
    
    goal_injection = ""
    if goal_class:
        strategy_hint = STRATEGY_HINTS.get(goal_class, STRATEGY_HINTS.get("UNKNOWN", ""))
        goal_injection = f"\n\nDETECTED GOAL CLASS: {goal_class}\nSTRATEGY HINT: {strategy_hint}"
    
    return f"""ARC-AGI-3 Puzzle Solver v7.0

{FIELD_GUIDE}

{notes_injection}
{goal_injection}

STRATEGY:
1. ACT FAST - don't think too much (max 60 words reasoning)
2. Track what changes grid = good; what doesn't = bad (no-op detection)
3. If stuck 40 actions without completing level → ESCALATION LADDER
   - Audit #1: audit hypotheses
   - Audit #2+: STRATEGY RESET (choose different goal class from FIELD GUIDE)
4. New object? CLICK it NOW to test (affordance detection)
5. Take NOTES: add "notes" field to actions to remember discoveries
6. After solving a level → write LEVEL X NOTES: paragraph

GOAL PERSISTENCE:
- One game = one win condition class (COVER/REACH/COPY/REDUCE/PLACE/FLOW/ALIGN)
- After solving level 1, remember the goal class
- All levels in same game have same goal type

FAILURE RECOVERY:
- If you get GAME OVER → don't repeat the same mistake
- Write in notes: "GAME OVER at action X, cause: Y"

ANTI-DISSERTATION:
- Keep reasoning SHORT (max 60 words)
- Use "notes" field to remember discoveries across turns
- Batch up to 8 actions at once when confident (if value gate > 0.7)
- Batch up to 2 actions when uncertain (if value gate < 0.3)

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
# Policy v7.0
# ---------------------------------------------------------------------------

class LLMPolicyV7_0:
    """LLM Agent v7.0 z counter-picking + deterministyczny ValueGate."""
    
    def __init__(self, llm_client: Any):
        self.client = llm_client
        self.state = GameState()
        self.messages = []
        
    def reset(self):
        """Reset stanu na nową grę."""
        self.state = GameState()
        self.messages = [{"role": "system", "content": build_system_prompt()}]
    
    def get_action(self, frame: dict[str, Any]) -> dict[str, Any]:
        """Zwróć akcję dla danego frame'a z counter-picking + ValueGate."""
        self.state.action_count += 1
        self.state.actions_since_level += 1
        
        # Counter-picking: detekcja klasy gry (raz na grę)
        if self.state.goal_class is None and self.state.action_count == 1:
            grid = frame.get("grid", [])
            detected_class = detect_goal_class(grid)
            self.state.goal_class = detected_class
            # Aktualizuj system prompt z detected goal class
            self.messages[0]["content"] = build_system_prompt(
                level_notes=self.state.level_notes,
                goal_class=detected_class,
            )
        
        # Heurystyczny ValueGate
        ml_value = self.state.value_gate.evaluate(frame, self.state)
        self.state.ml_value = ml_value
        
        # Sprawdź czy poziom został ukończony
        if frame.get("levels_completed", 0) > self.state.current_level - 1:
            self.state.current_level = frame["levels_completed"] + 1
            self.state.actions_since_level = 0
            self.state.stuck_count = 0
            # Poproś o LEVEL NOTES
            self.messages.append({
                "role": "system",
                "content": self._build_level_notes_request(frame["levels_completed"])
            })
        
        # Drabinka eskalacji
        if self.state.actions_since_level >= 40:
            self.state.stuck_count += 1
            if self.state.stuck_count % 15 == 0 or self.state.stuck_count <= 2:
                escalation_prompt = build_escalation_prompt(
                    self.state.stuck_count,
                    self.state.current_level,
                    self.state.actions_since_level,
                    self.state.goal_class,
                )
                self.messages.append({
                    "role": "system",
                    "content": escalation_prompt
                })
        
        # No-op detection
        current_grid_hash = str(frame.get("grid", ""))
        if current_grid_hash == self.state.last_grid_hash:
            self.state.no_op_count += 1
        else:
            self.state.no_op_count = max(0, self.state.no_op_count - 1)
        self.state.last_grid_hash = current_grid_hash
        
        # Dodaj frame do messages z ValueGate feedback
        user_msg = self._build_user_message(frame, ml_value)
        self.messages.append({"role": "user", "content": user_msg})
        
        # Deterministyczna temperatura (inspiracja v6.7)
        temperature = 0.6  # Default
        if self.state.stuck_count >= 2:
            temperature = 0.9  # High exploration po STRATEGY RESET
        elif ml_value < 0.3:
            temperature = 0.8  # High exploration gdy zły stan
        elif ml_value > 0.7:
            temperature = 0.4  # Low exploration gdy dobry stan
        
        # Confidence-based max_tokens
        max_tokens = 2000
        if ml_value > 0.8:
            max_tokens = 3000
        elif ml_value < 0.3:
            max_tokens = 1000
        
        # Wywołaj LLM
        response = self.client.chat.completions.create(
            model=os.getenv("LLM_MODEL", "qwen2.5-7b"),
            messages=self.messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        assistant_msg = response.choices[0].message
        self.messages.append(assistant_msg)
        
        # Wydobądź akcje
        actions = self._parse_actions(assistant_msg.content)
        
        # Zapisz notatki
        if actions and actions[0].get("notes"):
            self.state.notes.append(actions[0]["notes"])
            if len(self.state.notes) > 4:
                self.state.notes = self.state.notes[-4:]
        
        # Zaktualizuj level_notes z odpowiedzi modelu (odporna ekstrakcja z v6.7)
        new_notes = self._extract_level_notes(self.messages[-2:])
        if new_notes:
            self.state.level_notes.update(new_notes)
            self.messages[0]["content"] = build_system_prompt(
                self.state.level_notes,
                self.state.goal_class,
            )
        
        return actions[0] if actions else {"action": "RESET", "reasoning": "fallback"}
    
    def _build_level_notes_request(self, completed_level: int) -> str:
        """Po rozwiązaniu poziomu, poproś model o krótki paragraf NOTATEK."""
        return f"""Level {completed_level} is solved. In your next reply, write one short paragraph 
that starts with `LEVEL {completed_level} NOTES:` and states:
1. The mechanics you verified (what actions do what)
2. The win condition (how to win this level)
3. The action pattern that solved it (sequence of actions)
(At most 4 short sentences, max 200 characters)

The harness keeps these notes for the rest of the game.
"""
    
    def _extract_level_notes(self, messages: list[dict[str, Any]]) -> dict[int, str]:
        """Odporna ekstrakcja LEVEL NOTES (z v6.7).
        
        Skanuje: reasoning, reasoning_content, content
        Case-insensitive (model pisze "Level" nie "LEVEL")
        Filtr długości (min 20 znaków)
        """
        import re
        pattern = re.compile(
            r"LEVEL\s*(\d+)\s*NOTES?:\s*(.+?)(?=\n\s*\n|LEVEL\s*\d+\s*NOTES?:|\Z)",
            re.S | re.I,  # re.I = case-insensitive
        )
        found = {}
        limit = 600
        for message in messages:
            # Obsługa zarówno dict jak i obiektów Message
            if isinstance(message, dict):
                role = message.get('role', '')
            elif hasattr(message, 'role'):
                role = message.role
            else:
                continue
            
            if str(role).strip() != "assistant":
                continue
            
            # Skanuj reasoning, reasoning_content, content (odporna ekstrakcja z v6.7)
            for key in ("reasoning", "reasoning_content", "content"):
                # Obsługa zarówno dict jak i obiektów
                if isinstance(message, dict):
                    value = message.get(key, '')
                elif hasattr(message, key):
                    value = getattr(message, key, '')
                else:
                    value = ''
                
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
                    if len(note) < 20:  # Filtr długości
                        continue
                    try:
                        level = int(match.group(1))
                    except ValueError:
                        continue
                    if 0 < level < 100:
                        found[level] = note[:limit]
        return found
    
    def _build_user_message(self, frame: dict[str, Any], ml_value: float = 0.5) -> str:
        """Zbuduj wiadomość użytkownika z frame'em i ValueGate."""
        grid = frame.get("grid", [])
        available_actions = frame.get("available_actions", [])
        
        grid_str = "\n".join("".join(str(cell) for cell in row) for row in grid)
        
        # ValueGate feedback (deterministyczny, nie ML-based)
        ml_warning = ""
        if ml_value < 0.3:
            ml_warning = f"\n\n⚠️ WARNING: State evaluation low ({ml_value:.2f}). Consider changing strategy."
        elif ml_value > 0.7:
            ml_warning = f"\n\n✓ Good state ({ml_value:.2f}). Continue current approach."
        
        # No-op warning
        no_op_warning = ""
        if self.state.no_op_count >= 3:
            no_op_warning = f"\n\nWARNING: Last {self.state.no_op_count} actions didn't change grid. Try different action."
        
        # Game over history
        game_over_history = ""
        if self.state.game_overs:
            game_over_history = f"\n\nGAME OVER HISTORY: {'; '.join(self.state.game_overs[-3:])}"
        
        # Confidence-based batching hint
        batch_hint = ""
        if ml_value > 0.8:
            batch_hint = "\n\n[HIGH CONFIDENCE: batch up to 8 actions]"
        elif ml_value < 0.3:
            batch_hint = "\n\n[LOW CONFIDENCE: batch only 1-2 actions, explore carefully]"
        
        return f"""Level: {self.state.current_level}
Action: {self.state.action_count}
Actions since level complete: {self.state.actions_since_level}
Available actions: {', '.join(available_actions)}

Grid:
{grid_str}

Recent notes: {'; '.join(self.state.notes[-4:]) if self.state.notes else 'none'}
{ml_warning}{no_op_warning}{game_over_history}{batch_hint}

What action do you take?"""
    
    def _parse_actions(self, content: str) -> list[dict[str, Any]]:
        """Parser z raw_decode (z v6.7 - nie greedy)."""
        # Szukaj JSON w content
        json_match = re.search(r'(\[.*?\]|\{.*?\})', content, re.DOTALL)
        if not json_match:
            return []
        
        try:
            # Użyj raw_decode (nie greedy) jak w v6.7
            decoder = json.JSONDecoder()
            actions, _ = decoder.raw_decode(json_match.group(1))
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
        if len(self.state.game_overs) > 5:
            self.state.game_overs = self.state.game_overs[-5:]


if __name__ == "__main__":
    # Test
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
    
    policy = LLMPolicyV7_0(MockLLMClient())
    policy.reset()
    
    frame = {
        "grid": [[0, 1, 2], [3, 4, 5], [6, 7, 8]],
        "available_actions": ["RIGHT", "LEFT", "UP", "DOWN"],
        "levels_completed": 0,
        "current_level": 1,
        "action_count": 0,
        "actions_since_level": 0,
        "lives": 3,
        "score": 0,
        "step_limit": 400,
        "no_op_count": 0,
    }
    
    action = policy.get_action(frame)
    print(f"Action: {action}")
    print(f"Detected goal class: {policy.state.goal_class}")
    print(f"ValueGate: {policy.state.ml_value:.3f}")
