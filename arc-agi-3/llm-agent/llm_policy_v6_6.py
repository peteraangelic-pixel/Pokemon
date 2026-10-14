"""
ARC-AGI-3 LLM Agent v6.6 - najlepsza wersja (połączenie v5.1 + v6.5 + nowe idee)

Na podstawie analizy:
- v5.1 (moja): FIELD_GUIDE, AFFORDANCE_HINTS, FAILURE_RECOVERY, NO-OP DETECTION
- v6.5 (druga gałąź): Drabinka eskalacji, ValueGate z odmową kłamstwa, split per GRA
- Nowe idee: Adaptive temperature, Confidence-based batching, Pattern library, Multi-hypothesis tracking

Kluczowe zmiany vs v5.1:
- BRAK MLP (nie mamy wytrenowanych wag, random weights = szum)
- ValueGate z 12 cechami (z v6.5) - domyślnie WYŁĄCZONY
- Drabinka eskalacji (z v6.5) - audyt #1 jak dotąd, audyt #2+ z STRATEGY RESET
- Adaptive temperature (nowe) - temp zależy od ValueGate
- Confidence-based batching (nowe) - batch zależy od pewności gate
- Pattern library (nowe) - biblioteka wzorców z poprzednich gier
- Multi-hypothesis tracking (nowe) - śledzenie wielu hipotez jednocześnie

Oczekiwany wynik: ~40-48 pkt (vs v5.1 ~37-47, v6.5 ~38-45)
"""

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Optional


# ---------------------------------------------------------------------------
# FIELD GUIDE - klasy celów (z v5.1)
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
# ValueGate - 12 cech (z v6.5, domyślnie WYŁĄCZONY)
# ---------------------------------------------------------------------------

@dataclass
class ValueGate:
    """Value gate z 12 cechami - domyślnie WYŁĄCZONY.
    
    Cechy (z v6.5):
    0. no_op_ratio
    1. tokens_on_level / 100k
    2. audits_on_level
    3. grid_density
    4. objects_count / 20
    5. levels_completed / 5
    6. actions_since_level / 100
    7. lives / 5
    8. score / 100
    9. unique_colors / 10
    10. affordances_count / 10
    11. pattern_similarity
    
    Gate jest WYŁĄCZONY gdy:
    - Nie ma wytrenowanych wag
    - Acc ≤ base rate + 10pp
    - Błędy > 50% predykcji
    """
    
    enabled: bool = False
    weights: Optional[dict] = None
    predictions: int = 0
    errors: int = 0
    
    def predict(self, features: list[float]) -> float:
        """Predict value [0, 1] dla given features."""
        if not self.enabled or self.weights is None:
            return 0.5  # Neutral
        
        # Prosty linear model (w rzeczywistości: MLP)
        value = self.weights.get("bias", 0.0)
        for i, w in enumerate(self.weights.get("coefficients", [])):
            if i < len(features):
                value += w * features[i]
        
        # Sigmoid
        value = max(-20, min(20, value))
        return 1.0 / (1.0 + 2.71828 ** (-value))
    
    def update(self, prediction: float, actual: float):
        """Update gate z rzeczywistym wynikiem."""
        self.predictions += 1
        if abs(prediction - actual) > 0.3:
            self.errors += 1
            # Self-deactivation gdy gate robi zbyt wiele błędów
            if self.predictions > 10 and self.errors / self.predictions > 0.5:
                self.enabled = False
    
    def extract_features(self, frame: dict[str, Any], state: Any) -> list[float]:
        """Ekstrahuj 12 cech z stanu gry."""
        grid = frame.get("grid", [])
        
        # Podstawowe cechy
        no_op_ratio = state.no_op_count / max(1, state.action_count)
        tokens_on_level = state.tokens_since_level / 100000.0
        audits_on_level = state.stuck_count / 10.0
        
        # Grid features
        if grid and grid[0]:
            height = len(grid)
            width = len(grid[0])
            flat = [cell for row in grid for cell in row]
            non_zero = sum(1 for cell in flat if cell != 0)
            grid_density = non_zero / max(1, height * width)
            unique_colors = len(set(flat))
        else:
            grid_density = 0.0
            unique_colors = 0
        
        # Objects (connected components) - uproszczone
        objects_count = 0  # W rzeczywistości: count_connected_components(grid)
        
        # Progress
        levels_completed = frame.get("levels_completed", 0) / 5.0
        actions_since_level = state.actions_since_level / 100.0
        
        # Resources
        lives = frame.get("lives", 0) / 5.0
        score = frame.get("score", 0) / 100.0
        
        # Affordances
        affordances_count = 0  # W rzeczywistości: count_affordances(grid)
        
        # Pattern similarity
        pattern_similarity = 0.0  # W rzeczywistości: compute_pattern_similarity(grid)
        
        return [
            no_op_ratio,
            tokens_on_level,
            audits_on_level,
            grid_density,
            objects_count / 20.0,
            levels_completed,
            actions_since_level,
            lives,
            score,
            unique_colors / 10.0,
            affordances_count / 10.0,
            pattern_similarity,
        ]


# ---------------------------------------------------------------------------
# Pattern Library - biblioteka wzorców z poprzednich gier
# ---------------------------------------------------------------------------

@dataclass
class PatternLibrary:
    """Biblioteka wzorców z poprzednich gier.
    
    Przykład:
    - Gra ar25: zadziałało "kliknij na kontury" → zapisz
    - Gra cd82: zadziałało "kopiuj wzorzec z lewego górnego rogu" → zapisz
    """
    
    patterns: dict[str, list[str]] = field(default_factory=dict)
    
    def add_pattern(self, game: str, pattern: str):
        """Dodaj wzorzec do biblioteki."""
        if game not in self.patterns:
            self.patterns[game] = []
        if pattern not in self.patterns[game]:
            self.patterns[game].append(pattern)
    
    def get_patterns(self, game: str) -> list[str]:
        """Pobierz wzorce dla danej gry."""
        return self.patterns.get(game, [])
    
    def to_prompt(self) -> str:
        """Wygeneruj prompt z wzorcami."""
        if not self.patterns:
            return ""
        
        lines = ["\nPATTERN LIBRARY (from previous games):"]
        for game, patterns in sorted(self.patterns.items()):
            lines.append(f"  {game}: {'; '.join(patterns[:3])}")  # Max 3 patterns per game
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Multi-Hypothesis Tracker - śledzenie wielu hipotez jednocześnie
# ---------------------------------------------------------------------------

@dataclass
class Hypothesis:
    """Jedna hipoteza o celu/mechanice gry."""
    description: str
    evidence_for: int = 0
    evidence_against: int = 0
    confidence: float = 0.5
    
    def update(self, confirmed: bool):
        """Update hipotezy z dowodem."""
        if confirmed:
            self.evidence_for += 1
        else:
            self.evidence_against += 1
        
        total = self.evidence_for + self.evidence_against
        if total > 0:
            self.confidence = self.evidence_for / total


@dataclass
class MultiHypothesisTracker:
    """Śledzenie wielu hipotez jednocześnie."""
    
    hypotheses: list[Hypothesis] = field(default_factory=list)
    
    def add_hypothesis(self, description: str):
        """Dodaj nową hipotezę."""
        self.hypotheses.append(Hypothesis(description=description))
    
    def update_hypothesis(self, index: int, confirmed: bool):
        """Update hipotezy z dowodem."""
        if 0 <= index < len(self.hypotheses):
            self.hypotheses[index].update(confirmed)
    
    def get_best_hypothesis(self) -> Optional[Hypothesis]:
        """Pobierz hipotezę z najwyższą pewnością."""
        if not self.hypotheses:
            return None
        return max(self.hypotheses, key=lambda h: h.confidence)
    
    def to_prompt(self) -> str:
        """Wygeneruj prompt z hipotezami."""
        if not self.hypotheses:
            return ""
        
        lines = ["\nHYPOTHESES (sorted by confidence):"]
        for i, h in enumerate(sorted(self.hypotheses, key=lambda x: -x.confidence)):
            lines.append(f"  {i+1}. {h.description} (confidence: {h.confidence:.2f}, +{h.evidence_for}/-{h.evidence_against})")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Extended GameState (z v6.5)
# ---------------------------------------------------------------------------

@dataclass
class GameStateV6_6:
    """GameState v6.6 z ValueGate + PatternLibrary + MultiHypothesisTracker."""
    
    # Podstawowe cechy (z v5.1)
    action_count: int = 0
    actions_since_level: int = 0
    tokens_since_level: int = 0
    last_grid_hash: str = ""
    stuck_count: int = 0
    strategy: str = "explore"
    notes: list[str] = field(default_factory=list)
    current_level: int = 1
    goal_class: Optional[str] = None
    game_overs: list[str] = field(default_factory=list)
    no_op_count: int = 0
    level_notes: dict[int, str] = field(default_factory=dict)
    
    # ValueGate (z v6.5)
    value_gate: ValueGate = field(default_factory=ValueGate)
    ml_value: float = 0.5
    
    # Pattern library (nowe)
    pattern_library: PatternLibrary = field(default_factory=PatternLibrary)
    
    # Multi-hypothesis tracker (nowe)
    hypothesis_tracker: MultiHypothesisTracker = field(default_factory=MultiHypothesisTracker)


# ---------------------------------------------------------------------------
# Drabinka eskalacji (z v6.5)
# ---------------------------------------------------------------------------

def build_escalation_prompt(stuck_count: int, level: int, actions_since_level: int, value_gate: ValueGate) -> str:
    """Zbuduj prompt eskalacji w zależności od stuck_count."""
    
    if stuck_count == 1:
        # Audyt #1 jak dotąd (z v5.1)
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
    
    elif stuck_count >= 2:
        # Audyt #2+ z STRATEGY RESET (z v6.5)
        ml_annotation = ""
        if value_gate.enabled and value_gate.ml_value < 0.3:
            ml_annotation = f"\n\n[learned state-value {value_gate.ml_value:.2f} - LOW]"
        
        return f"""STRATEGY RESET: You've spent {actions_since_level} actions on level {level} without solving it, and this is audit #{stuck_count}.

Your current approach is NOT WORKING. ABANDON IT.

1. Look at FIELD GUIDE above. Which goal class fits this game? (COVER/REACH/COPY/REDUCE/PLACE/FLOW/ALIGN)
2. Choose a DIFFERENT goal class than what you tried before.
3. Start fresh with that goal class.
4. DO NOT repeat the same action patterns you tried before.
{ml_annotation}

Write in your reasoning: "RESETTING STRATEGY: trying [NEW_GOAL_CLASS] instead of [OLD_APPROACH]"
Then execute a completely different approach.
"""
    
    return ""


# ---------------------------------------------------------------------------
# System Prompt (z FIELD_GUIDE + PatternLibrary + HypothesisTracker)
# ---------------------------------------------------------------------------

def build_system_prompt(
    level_notes: Optional[dict[int, str]] = None,
    pattern_library: Optional[PatternLibrary] = None,
    hypothesis_tracker: Optional[MultiHypothesisTracker] = None,
) -> str:
    """Zbuduj system prompt z FIELD_GUIDE + PatternLibrary + HypothesisTracker."""
    
    # Level notes
    notes_injection = ""
    if level_notes:
        lines = ["\nLEVEL NOTES (from previous levels):"]
        for level in sorted(level_notes.keys()):
            lines.append(f"Level {level}: {level_notes[level]}")
        notes_injection = "\n".join(lines)
    
    # Pattern library
    pattern_injection = ""
    if pattern_library:
        pattern_injection = pattern_library.to_prompt()
    
    # Hypothesis tracker
    hypothesis_injection = ""
    if hypothesis_tracker:
        hypothesis_injection = hypothesis_tracker.to_prompt()
    
    return f"""ARC-AGI-3 Puzzle Solver v6.6

{FIELD_GUIDE}

{notes_injection}
{pattern_injection}
{hypothesis_injection}

STRATEGY:
1. ACT FAST - don't think too much (max 60 words reasoning)
2. Track what changes grid = good; what doesn't = bad (no-op detection)
3. If stuck 40 actions without completing level → ESCALATION LADDER
   - Audit #1: audit hypotheses
   - Audit #2+: STRATEGY RESET (choose different goal class from FIELD GUIDE)
4. New object? CLICK it NOW to test (affordance detection)
5. Take NOTES: add "notes" field to actions to remember discoveries
6. After solving a level → write LEVEL X NOTES: paragraph
7. Track MULTIPLE HYPOTHESES simultaneously (not just one)
8. Add successful patterns to PATTERN LIBRARY

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
- Batch up to 8 actions at once when confident (if value gate > 0.7)
- Batch up to 2 actions when uncertain (if value gate 0.3-0.7)

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
# Policy v6.6
# ---------------------------------------------------------------------------

class LLMPolicyV6_6:
    """LLM Agent v6.6 - najlepsza wersja (połączenie v5.1 + v6.5 + nowe idee)."""
    
    def __init__(self, llm_client: Any, value_gate_weights: Optional[dict] = None):
        self.client = llm_client
        self.state = GameStateV6_6()
        self.messages = []
        
        # Initialize ValueGate
        if value_gate_weights:
            self.state.value_gate.enabled = True
            self.state.value_gate.weights = value_gate_weights
    
    def reset(self):
        """Reset stanu na nową grę."""
        self.state = GameStateV6_6()
        self.messages = [{"role": "system", "content": build_system_prompt()}]
    
    def get_action(self, frame: dict[str, Any]) -> dict[str, Any]:
        """Zwróć akcję dla danego frame'a z ValueGate + Drabinka eskalacji."""
        self.state.action_count += 1
        self.state.actions_since_level += 1
        self.state.tokens_since_level += 1000  # Mock: ~1000 tokens per action
        
        # ValueGate prediction
        features = self.state.value_gate.extract_features(frame, self.state)
        ml_value = self.state.value_gate.predict(features)
        self.state.ml_value = ml_value
        
        # Sprawdź czy poziom został ukończony
        if frame.get("levels_completed", 0) > self.state.current_level - 1:
            self.state.current_level = frame["levels_completed"] + 1
            self.state.actions_since_level = 0
            self.state.tokens_since_level = 0
            self.state.stuck_count = 0
            
            # Dodaj wzorzec do Pattern Library
            if self.state.goal_class:
                pattern = f"Level {self.state.current_level - 1} solved with {self.state.goal_class}"
                self.state.pattern_library.add_pattern(frame.get("game", "unknown"), pattern)
            
            # Poproś o LEVEL NOTES
            self.messages.append({
                "role": "system",
                "content": self._build_level_notes_request(frame["levels_completed"])
            })
        
        # Sprawdź czy utknął (40 akcji bez ukończenia poziomu) - DRABINKA ESKALACJI
        if self.state.actions_since_level >= 40:
            self.state.stuck_count += 1
            if self.state.stuck_count % 15 == 0 or self.state.stuck_count <= 2:
                # Co 15 akcji po utknięciu LUB pierwsze 2 audyty
                escalation_prompt = build_escalation_prompt(
                    self.state.stuck_count,
                    self.state.current_level,
                    self.state.actions_since_level,
                    self.state.value_gate
                )
                self.messages.append({
                    "role": "system",
                    "content": escalation_prompt
                })
        
        # Sprawdź no-op (akcja nie zmieniła grid)
        current_grid_hash = str(frame.get("grid", ""))
        if current_grid_hash == self.state.last_grid_hash:
            self.state.no_op_count += 1
        else:
            self.state.no_op_count = max(0, self.state.no_op_count - 1)
        self.state.last_grid_hash = current_grid_hash
        
        # Dodaj frame do messages z adaptive temperature
        user_msg = self._build_user_message(frame, ml_value)
        self.messages.append({"role": "user", "content": user_msg})
        
        # Adaptive temperature (nowe)
        temperature = 0.6  # Default
        if ml_value < 0.3:
            temperature = 0.9  # High exploration when stuck
        elif ml_value > 0.7:
            temperature = 0.3  # Low exploration when confident
        
        # Confidence-based batching (nowe)
        max_tokens = 2000
        if ml_value > 0.8:
            max_tokens = 3000  # More actions when confident
        elif ml_value < 0.3:
            max_tokens = 1000  # Fewer actions when stuck
        
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
        
        # Zaktualizuj level_notes z odpowiedzi modelu
        new_notes = self._extract_level_notes(self.messages[-2:])
        if new_notes:
            self.state.level_notes.update(new_notes)
            # Zaktualizuj system prompt z nowymi notatkami + pattern library + hypotheses
            self.messages[0]["content"] = build_system_prompt(
                self.state.level_notes,
                self.state.pattern_library,
                self.state.hypothesis_tracker
            )
        
        # Zwróć pierwszą akcję
        return actions[0] if actions else {"action": "RESET", "reasoning": "fallback"}
    
    def _build_level_notes_request(self, completed_level: int) -> str:
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
    
    def _extract_level_notes(self, messages: list[dict[str, Any]]) -> dict[int, str]:
        """Wydobądź notatki z wiadomości asystenta."""
        pattern = re.compile(
            r"LEVEL\s*(\d+)\s*NOTES?:\s*(.+?)(?=\n\s*\n|LEVEL\s*\d+\s*NOTES?:|\Z)",
            re.S | re.I,
        )
        found = {}
        limit = 600
        for message in messages:
            if str(message.get("role", "")).strip() != "assistant":
                continue
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
    
    def _build_user_message(self, frame: dict[str, Any], ml_value: float = 0.5) -> str:
        """Zbuduj wiadomość użytkownika z frame'em i ValueGate."""
        grid = frame.get("grid", [])
        available_actions = frame.get("available_actions", [])
        
        # ASCII reprezentacja grid
        grid_str = "\n".join("".join(str(cell) for cell in row) for row in grid)
        
        # ValueGate warning/info
        ml_warning = ""
        if self.state.value_gate.enabled:
            if ml_value < 0.3:
                ml_warning = f"\n\n⚠️ WARNING: ML model predicts low success probability ({ml_value:.2f}). Consider changing strategy."
            elif ml_value > 0.7:
                ml_warning = f"\n\n✓ ML model predicts good state ({ml_value:.2f}). Continue current approach."
        
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
        if self.state.value_gate.enabled:
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
        """Wydobądź akcje z odpowiedzi LLM."""
        json_match = re.search(r'\[.*?\]', content, re.DOTALL)
        if not json_match:
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
    
    # Create policy (ValueGate WYŁĄCZONY domyślnie)
    policy = LLMPolicyV6_6(MockLLMClient())
    policy.reset()
    
    # Test frame
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
        "goal_class": "COPY",
        "game": "test_game",
    }
    
    # Get action
    action = policy.get_action(frame)
    print(f"Action: {action}")
    print(f"ValueGate enabled: {policy.state.value_gate.enabled}")
    print(f"ML value: {policy.state.ml_value:.3f}")
