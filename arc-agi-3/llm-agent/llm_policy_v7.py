"""LLM-based policy v7 for ARC-AGI-3.

Kombinacja najlepszych elementów v6.9 + v7-abandon:
- Goal classifier (z v6.9) - detekcja klasy gry w runtime
- Early abandon (z v7-abandon) - porzucaj gry martwe (0 poziomów po 60k tokenów)
- Goal class retry - jeśli UNKNOWN, spróbuj ponownie po 10k tokenów
- Token budget tracking - śledź zużycie tokenów per gra
- Adaptive exploration - hotter temp gdy utkniesz, cooler gdy progresujesz
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.request
import urllib.error
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Sequence

from goal_classifier import detect_goal_class, STRATEGY_HINTS
from grid_utils import (
    ARC_COLOR_CHARS,
    ARC_COLOR_LEGEND,
    format_grid_ascii,
    segment_grid,
    compact_segmentation_summary,
    grid_to_png_bytes,
)

# ---------------------------------------------------------------------------
# Action protocol
# ---------------------------------------------------------------------------
RESET = "RESET"
ACTION_NAMES = (RESET, *(f"ACTION{i}" for i in range(1, 8)))
COMPLEX_ACTION = "ACTION6"
DIRECTIONAL_ACTIONS = ("ACTION1", "ACTION2", "ACTION3", "ACTION4")
DIRECTION_NAMES = {
    "ACTION1": "UP", "ACTION2": "DOWN",
    "ACTION3": "LEFT", "ACTION4": "RIGHT",
}
MODEL_TO_ENGINE = {
    "UP": "ACTION1", "DOWN": "ACTION2",
    "LEFT": "ACTION3", "RIGHT": "ACTION4",
    "MOUSE": "ACTION6", "CLICK": "ACTION6",
}
ENGINE_TO_MODEL = {v: k for k, v in MODEL_TO_ENGINE.items()}
ENGINE_TO_MODEL.update(DIRECTION_NAMES)

# ---------------------------------------------------------------------------
# Environment knobs (defaults from v6.9)
# ---------------------------------------------------------------------------
KNOBS = {
    # Token limits
    "ABANDON_TOKENS": int(os.environ.get("ARC3_ABANDON_TOKENS", "60000")),
    "ABANDON_ACTIONS": int(os.environ.get("ARC3_ABANDON_ACTIONS", "100")),
    "GOAL_CLASS_RETRY_TOKENS": int(os.environ.get("ARC3_GOAL_CLASS_RETRY_TOKENS", "10000")),
    
    # Exploration
    "TEMP_STUCK": float(os.environ.get("ARC3_TEMP_STUCK", "0.9")),
    "TEMP_FRESH": float(os.environ.get("ARC3_TEMP_FRESH", "0.7")),
    "TEMP_FRESH_ACTIONS": int(os.environ.get("ARC3_TEMP_FRESH_ACTIONS", "20")),
    "AUDIT_ESCALATE_FROM": int(os.environ.get("ARC3_AUDIT_ESCALATE_FROM", "2")),
    
    # Planning
    "QUEUE_MAX": int(os.environ.get("ARC3_QUEUE_MAX", "10")),
    "PROMPT_BATCH_MAX": int(os.environ.get("ARC3_PROMPT_BATCH_MAX", "10")),
    
    # Memory
    "LESSONS_MAX": int(os.environ.get("ARC3_LESSONS_MAX", "5")),
    "NOOP_WINDOW": int(os.environ.get("ARC3_NOOP_WINDOW", "8")),
    "PROBE_MAX": int(os.environ.get("ARC3_PROBE_MAX", "4")),
    
    # Goal class
    "GOAL_CLASS": int(os.environ.get("ARC3_GOAL_CLASS", "1")),
}


# ---------------------------------------------------------------------------
# LLM Client
# ---------------------------------------------------------------------------
@dataclass
class LLMConfig:
    base_url: str = ""
    model_id: str = ""
    api_key: str = "EMPTY"
    max_output_tokens: int = 2048
    temperature: float = 0.6
    top_p: float = 0.95
    top_k: int = 20
    timeout: float = 120.0
    context_window: int = 32768
    enable_thinking: bool = True
    multimodal: bool = False
    upscale: int = 4

    @classmethod
    def from_env(cls) -> LLMConfig:
        return cls(
            base_url=os.environ.get("LLM_BASE_URL", "http://127.0.0.1:1234/v1"),
            model_id=os.environ.get("LLM_MODEL_ID", ""),
            api_key=os.environ.get("LLM_API_KEY", "EMPTY"),
            max_output_tokens=int(os.environ.get("LLM_MAX_OUTPUT", "2048")),
            temperature=float(os.environ.get("LLM_TEMPERATURE", "0.6")),
            top_p=float(os.environ.get("LLM_TOP_P", "0.95")),
            top_k=int(os.environ.get("LLM_TOP_K", "20")),
            timeout=float(os.environ.get("LLM_TIMEOUT", "120")),
            context_window=int(os.environ.get("LLM_CONTEXT_WINDOW", "32768")),
            enable_thinking=os.environ.get("LLM_ENABLE_THINKING", "1").lower() in ("1", "true", "yes"),
            multimodal=os.environ.get("LLM_MULTIMODAL", "0").lower() in ("1", "true", "yes"),
            upscale=int(os.environ.get("LLM_UPSCALE", "4")),
        )


class LLMClient:
    """Minimal OpenAI-compatible chat completion client (no dependencies)."""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.total_tokens = 0
        self.total_calls = 0
        self.total_time = 0.0
    
    def chat(self, messages: list[dict], temperature: float | None = None) -> dict:
        """Call chat completions. Returns the message dict.

        `temperature` overrides the configured value for THIS call only
        (adaptive exploration: hotter when deeply stuck, cooler when on a roll).
        """
        url = f"{self.config.base_url.rstrip('/')}/chat/completions"
        
        payload: dict[str, Any] = {
            "model": self.config.model_id,
            "messages": messages,
            "max_tokens": self.config.max_output_tokens,
            "temperature": self.config.temperature if temperature is None else temperature,
            "top_p": self.config.top_p,
            "stream": False,
        }
        
        if self.config.enable_thinking:
            payload["chat_template_kwargs"] = {"enable_thinking": True}
        
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.api_key}",
            },
        )
        
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print(f"[LLM] Request failed after {time.time()-t0:.1f}s: {e}")
            return {"role": "assistant", "content": ""}
        finally:
            self.total_time += time.time() - t0
        
        self.total_calls += 1
        usage = result.get("usage", {})
        self.total_tokens += usage.get("total_tokens", 0)
        
        choices = result.get("choices", [])
        if choices:
            return choices[0].get("message", {"role": "assistant", "content": ""})
        return {"role": "assistant", "content": ""}


# ---------------------------------------------------------------------------
# System prompt (optimized for structured JSON output)
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = f"""You are an expert puzzle solver playing a grid-based game. You see the game board as a 64×64 color grid and must figure out the mechanics through experimentation.

COLOR LEGEND: {ARC_COLOR_LEGEND}

HOW THE GAME WORKS:
- You control an avatar/agent on a colored grid
- You take actions to move, interact, or manipulate objects
- Levels are completed when you achieve the goal (often reaching a target, solving a puzzle, or clearing enemies)
- GAME_OVER means you died; the game auto-resets
- WIN means you beat the entire game

AVAILABLE ACTIONS (may vary per game):
- UP / DOWN / LEFT / RIGHT — move in a direction
- MOUSE(row=N, col=M) — click/interact at position (row, col)
- Other game-specific actions may appear in valid_actions

YOUR TASK EACH TURN:
1. Observe the current board state
2. Consider what changed since last turn (if history available)
3. Form/update a hypothesis about the game mechanics and goal
4. Choose the BEST next action

STRATEGIES:
- Start by exploring: move in different directions to understand the world
- Identify the player avatar (usually a distinct colored shape that moves)
- Identify obstacles, enemies, targets, and interactive objects
- For navigation puzzles, plan a path using BFS mentally
- If you die repeatedly, try a different approach
- Don't click on HUD elements (bars at edges that change each step)
- Objects are multi-tile connected components of the same color

IMPORTANT:
- Be decisive. Don't waste actions on indecision.
- If you've been stuck for 10+ actions, radically change strategy.
- Track what worked and what didn't (use "notes").
- Compact reasoning is fine, but always output a valid action.
- Deliberate LESS, act MORE: actions are cheap (~1.5x headroom before extra moves cost
  points), thinking tokens are the scarce resource. Max ~60 words per response.

FIELD GUIDE (patterns observed across ARC-AGI-3 training games — treat as priors, verify on the board):
- The win condition is almost always "ALL of something": all goal markers covered, all
  avatars on exits, all vessels filled, exactly one peg left. Partial progress gives NO
  signal — don't stop working because "most" of it is done.
- Dotted outlines, hollow contours, and small markers sharing the color of a movable
  object are usually the targets.
- A large area that no action seems to affect, yet looks like it should be editable, is
  almost always a PATTERN to copy, complete, or translate (≈40% of games).
- Some games check the result only after a CONFIRM action and give very few attempts:
  set the whole configuration up first, then confirm exactly once. Never confirm "to test".
- A counter that decreases every action is a step/lives LIMIT: it reaching 0 is a LOSS,
  never a win. Keep a margin; when it runs low, spend actions only on the safest known
  progress toward the goal.

LESSONS BETWEEN GAMES: at the start of a game you may see "Lessons from earlier
games in this run" — your own findings from sibling games (patterns common across
ARC games). Apply them as priors and verify against the new board.

GOAL PERSISTENCE: one game = one win condition for ALL its levels. Once you solve a
level, you almost certainly know the goal — record it in "notes". Later levels add
mechanics but do NOT change the goal class. If a level seems to contradict your goal,
re-check what actually changed on screen; do not invent extra objects to fit an old rule.

STUCK PROTOCOL: if many actions produce no level completion, stop re-trying variants of
the same idea. In "notes", list win-condition hypotheses you tested and FALSIFIED (✗),
form a different one, and run the cheapest experiment (1–2 actions) that distinguishes it.

OUTPUT FORMAT — end your response with one or more JSON action objects.
Single action (when uncertain or after an unexpected result):
```json
{{"action": "ACTION_NAME", "reasoning": "brief explanation"}}
```
Plan several actions at once (preferred for routine sequences, up to
{KNOBS["PROMPT_BATCH_MAX"]}) —
they run in order until the next LLM call:
```json
{{"action": "UP", "reasoning": "step 1 of path"}}
{{"action": "LEFT", "reasoning": "step 2 of path"}}
```
or as one JSON array: `[{{"action": "UP"}}, {{"action": "LEFT"}}]`
For MOUSE actions: {{"action": "MOUSE", "row": 5, "col": 10, "reasoning": "..."}}
On the FIRST action object you may add a "notes" field — your compact memory for
this game: the current goal hypothesis, learned rules, falsified hypotheses (✗).
It is returned to you every turn; keep it under ~40 words, rewrite it when it changes:
```json
{{"action": "UP", "reasoning": "...", "notes": "GOAL: cover all dotted targets with the red cross. ✗ pushing boxes does nothing"}}
```
Do not output any other JSON objects.

BATCHING RULES:
- Plan a whole path or repetition (e.g. "move LEFT 5 times") as multiple
  action objects in ONE response — this saves thinking time for later.
- Stop the plan early (single action) if the next step depends on what a
  previous step reveals.
- The step counter shown in the HUD is the STEP LIMIT for the level, not a
  timer; nothing bad happens over time, only wasted steps. If it is running
  low, prioritize the safest known progress toward the goal.
- Experiment to learn mechanics, but prefer cheap experiments (one or two
  steps) over long deliberation. Always keep some budget to finish the level."""


# ---------------------------------------------------------------------------
# Frame info
# ---------------------------------------------------------------------------
@dataclass
class FrameInfo:
    grid: tuple[tuple[int, ...], ...]
    step: int
    level: int
    state_name: str
    levels_completed: int
    available_actions: list[str]
    
    @property
    def ascii(self) -> str:
        return format_grid_ascii(self.grid)
    
    @property
    def shape(self) -> tuple[int, int]:
        rows = len(self.grid)
        cols = max((len(r) for r in self.grid), default=0)
        return (rows, cols)
    
    def segmentation_summary(self) -> str:
        try:
            seg = segment_grid(self.grid)
            return compact_segmentation_summary(seg, max_nodes=15)
        except Exception:
            return "segmentation unavailable"


# ---------------------------------------------------------------------------
# State tracking for anti-loop
# ---------------------------------------------------------------------------
@dataclass
class StateTracker:
    """Track state transitions to detect loops."""
    
    state_signatures: list[str] = field(default_factory=list)
    action_history: list[str] = field(default_factory=list)
    state_action_counts: Counter = field(default_factory=Counter)
    game_over_count: int = 0
    total_actions: int = 0
    unique_states_seen: set = field(default_factory=set)
    
    # Recent window for loop detection
    _recent_sigs: list[str] = field(default_factory=list)
    _recent_actions: list[str] = field(default_factory=list)
    
    def record(self, state_sig: str, action: str, *,
               game_over: bool = False) -> None:
        self.state_signatures.append(state_sig)
        self.action_history.append(action)
        self.state_action_counts[(state_sig, action)] += 1
        self.total_actions += 1
        self.unique_states_seen.add(state_sig)
        
        self._recent_sigs.append(state_sig)
        if len(self._recent_sigs) > 12:
            self._recent_sigs = self._recent_sigs[-12:]
        
        self._recent_actions.append(action)
        if len(self._recent_actions) > 12:
            self._recent_actions = self._recent_actions[-12:]
        
        if game_over:
            self.game_over_count += 1
    
    def is_looped(self) -> bool:
        """Check if we're stuck repeating."""
        if len(self._recent_sigs) < 6:
            return False
        
        # Oscillation: same state appearing at positions 0,2,4
        last6 = self._recent_sigs[-6:]
        if last6[0] == last6[2] == last6[4] and last6[1] == last6[3] == last6[5]:
            return True
        
        # Same action repeated 6+ times
        if len(self._recent_actions) >= 6:
            last6a = self._recent_actions[-6:]
            if len(set(last6a)) == 1:
                return True
        
        # Same state repeated 4+ times
        if len(self._recent_sigs) >= 4:
            last4 = self._recent_sigs[-4:]
            if len(set(last4)) == 1:
                return True
        
        return False
    
    def repeated_in_state(self, state_sig: str, action: str) -> int:
        return self.state_action_counts.get((state_sig, action), 0)
    
    def reset(self) -> None:
        self.state_signatures.clear()
        self.action_history.clear()
        self.state_action_counts.clear()
        self.game_over_count = 0
        self.total_actions = 0
        self.unique_states_seen.clear()
        self._recent_sigs.clear()
        self._recent_actions.clear()


# ---------------------------------------------------------------------------
# Main LLM Policy v7
# ---------------------------------------------------------------------------
def _extract_action_objects(content: str) -> list[dict]:
    """Return every action dict found in `content`."""
    decoder = json.JSONDecoder()
    found: list[dict] = []

    def next_pos(p: int) -> int:
        brace = content.find("{", p)
        bracket = content.find("[", p)
        if brace == -1:
            return bracket
        if bracket == -1:
            return brace
        return min(brace, bracket)

    pos = 0
    while True:
        start = next_pos(pos)
        if start == -1:
            break
        try:
            obj, end = decoder.raw_decode(content, start)
        except json.JSONDecodeError:
            pos = start + 1
            continue
        if isinstance(obj, dict) and "action" in obj:
            found.append(obj)
        elif isinstance(obj, list):
            for item in obj:
                if isinstance(item, dict) and "action" in item:
                    found.append(item)
        pos = end
    return found


class LLMPolicyV7:
    """LLM-based policy v7 with early abandon + goal classifier + adaptive exploration."""
    
    def __init__(self, config: LLMConfig | None = None):
        self.config = config or LLMConfig.from_env()
        self.client = LLMClient(self.config)
        self.tracker = StateTracker()
        
        # Conversation history for the current game
        self._messages: list[dict] = []
        self._initialized = False
        
        # Action cache: actions planned by LLM to execute without re-calling
        self._action_queue: list[dict] = []
        self._last_level = 0
        self._actions_since_last_llm = 0
        self._max_actions_per_plan = KNOBS["QUEUE_MAX"]
        
        # Game notes (agent's own compact memory, from the "notes" field)
        self._game_notes: list[str] = []
        self._actions_on_level = 0
        self._last_audit_at = 0
        
        # Level whose "probe opening" was already queued
        self._probe_level: int | None = None
        
        # No-op detection
        self._noop_recent: list[tuple[str, bool]] = []
        self._last_exec: str | None = None
        self._last_grid: tuple[tuple[int, ...], ...] | None = None
        
        # Run-level lessons harvested from finished games
        self._run_lessons: list[str] = []
        
        # Token accounting per level
        self._level_start_tokens = 0
        self._audit_level_tokens = 0
        
        # Level whose structured notes are requested
        self._pending_notes: int | None = None
        
        # Structured notes per solved level
        self._level_notes: dict[int, str] = {}
        
        # Game-over history for failure recovery
        self._game_overs: list[str] = []
        
        # v7: runtime-detected goal class (counter-picking)
        self._goal_class: str | None = None
        self._goal_class_detected_at_tokens = 0
        
        # v7: Token budget tracking for early abandon
        self._game_start_tokens = 0
        self._actions_in_game = 0
        
        # v7: Should we abandon this game?
        self._should_abandon = False
    
    def reset_game(self) -> None:
        """Reset for a new game."""
        self._messages.clear()
        self._initialized = False
        self.tracker.reset()
        self._action_queue.clear()
        self._last_level = 0
        self._actions_since_last_llm = 0
        
        # Harvest this game's notes into run-level lessons
        for note in self._game_notes:
            if note not in self._run_lessons:
                self._run_lessons.append(note)
        if len(self._run_lessons) > KNOBS["LESSONS_MAX"]:
            del self._run_lessons[:len(self._run_lessons) - KNOBS["LESSONS_MAX"]]
        self._game_notes.clear()
        self._actions_on_level = 0
        self._last_audit_at = 0
        self._probe_level = None
        self._noop_recent.clear()
        self._last_exec = None
        self._last_grid = None
        self._level_start_tokens = self.total_tokens
        self._audit_level_tokens = 0
        self._pending_notes = None
        self._level_notes.clear()
        self._game_overs.clear()
        self._audits_on_level = 0
        self._goal_class = None
        self._goal_class_detected_at_tokens = 0
        
        # v7: Token budget tracking
        self._game_start_tokens = self.total_tokens
        self._actions_in_game = 0
        self._should_abandon = False
    
    def should_abandon(self) -> bool:
        """Check if this game should be abandoned (early abandon logic)."""
        tokens_used = self.total_tokens - self._game_start_tokens
        
        # Abandon if:
        # 1. Used > ABANDON_TOKENS (60k) tokens AND
        # 2. Used > ABANDON_ACTIONS (100) actions AND
        # 3. Solved 0 levels
        if (tokens_used > KNOBS["ABANDON_TOKENS"] and
            self._actions_in_game > KNOBS["ABANDON_ACTIONS"] and
            self._last_level == 0):
            return True
        
        return False
    
    def choose_action(self, frame: FrameInfo) -> dict:
        """Choose an action for the current frame.
        
        Returns dict: {name: str, x: int|None, y: int|None, reasoning: dict}
        """
        # v7: Check if we should abandon this game
        # FIX BUG 2: Return special ABANDON action instead of RESET
        # RESET restarts the game in same server slot (doesn't free slot)
        # ABANDON signals notebook to stop this game and move to next
        if self.should_abandon():
            self._should_abandon = True
            return {"name": "ABANDON", "reasoning": {"abandon": True, "tokens": self.total_tokens - self._game_start_tokens, "actions": self._actions_in_game, "levels": self._last_level}}
        
        state_sig = self._state_signature(frame)
        
        # v7: Goal class detection with retry
        tokens_since_start = self.total_tokens - self._game_start_tokens
        if int(KNOBS.get("GOAL_CLASS", 1)) and self._goal_class is None:
            try:
                detected = detect_goal_class(frame.grid)
                if detected != "UNKNOWN":
                    self._goal_class = detected
                    self._goal_class_detected_at_tokens = self.total_tokens
                elif tokens_since_start > KNOBS["GOAL_CLASS_RETRY_TOKENS"]:
                    # Retry after 10k tokens
                    self._goal_class = ""  # Stop retrying
            except Exception:
                self._goal_class = ""  # Stop retrying on error
        
        # Attribute the previous action's effect (no-op detection)
        if self._last_exec is not None and self._last_grid is not None:
            self._noop_recent.append((self._last_exec, frame.grid != self._last_grid))
            if len(self._noop_recent) > KNOBS["NOOP_WINDOW"]:
                del self._noop_recent[0]
        
        # Check for level change — re-plan immediately
        if frame.levels_completed != self._last_level:
            solved = frame.levels_completed > self._last_level
            self._last_level = frame.levels_completed
            self._action_queue.clear()
            self._actions_since_last_llm = 0
            self._actions_on_level = 0
            self._last_audit_at = 0
            self._audits_on_level = 0
            self._level_start_tokens = self.total_tokens
            self._audit_level_tokens = 0
            if solved:
                self._pending_notes = max(0, frame.levels_completed - 1)
        
        # Scripted probe opening
        if self._probe_level != frame.levels_completed:
            self._probe_level = frame.levels_completed
            self._action_queue.extend(self._probe_actions(frame))
            if self._messages:
                self._messages.append({
                    "role": "user",
                    "content": f"[LEVEL COMPLETED! Now on level {frame.levels_completed + 1}. Re-assess the new board.]"
                })
        
        # Check for loop
        if self.tracker.is_looped():
            self._action_queue.clear()
            return self._anti_loop_action(frame)
        
        # Try to use cached action
        if self._action_queue and self._actions_since_last_llm < self._max_actions_per_plan:
            action = self._action_queue.pop(0)
            self._actions_since_last_llm += 1
            self._actions_on_level += 1
            self._actions_in_game += 1
            self.tracker.record(state_sig, action.get("name", RESET))
            self._mark_executed(frame, action.get("name", RESET))
            return action
        
        # Need to call LLM
        self._action_queue.clear()
        self._actions_since_last_llm = 0
        
        # Build user turn
        user_content = self._build_user_turn(frame)
        
        if not self._messages:
            # v7: System prompt z goal class hint
            sys_text = SYSTEM_PROMPT
            gc = self._goal_class
            if gc:
                hint = STRATEGY_HINTS.get(gc, "")
                sys_text += (
                    f"\n\nRUNTIME GOAL-CLASS DETECTION: the first board most "
                    f"resembles the \"{gc}\" class. Working hypothesis: {hint}. "
                    "Treat it as a starting point — falsify it in your notes "
                    "if the board disagrees (mark ✗ CLASS)."
                )
            self._messages.append({"role": "system", "content": sys_text})
        
        self._messages.append({"role": "user", "content": user_content})
        
        # Trim context if too long
        self._trim_context()
        
        # Adaptive temperature
        temperature: float | None = None
        if self._audits_on_level >= int(KNOBS["AUDIT_ESCALATE_FROM"]):
            temperature = KNOBS["TEMP_STUCK"]
        elif self._actions_on_level < KNOBS["TEMP_FRESH_ACTIONS"]:
            temperature = KNOBS["TEMP_FRESH"]
        
        # Call LLM
        response = self.client.chat(self._messages, temperature=temperature)
        content = response.get("content", "") or ""
        
        # Structured per-level notes survive
        self._absorb_level_notes(response)
        
        # Add assistant response to history
        self._messages.append({"role": "assistant", "content": content})
        
        # Parse action(s) from response
        actions = self._parse_response(content, frame)
        self._absorb_notes(actions)
        
        if not actions:
            # Fallback: try different directions
            action = self._fallback_action(frame)
            self.tracker.record(state_sig, action.get("name", RESET))
            self._actions_on_level += 1
            self._actions_in_game += 1
            self._mark_executed(frame, action.get("name", RESET))
            return action
        
        # First action is immediate, rest go to queue
        immediate = actions[0]
        self._action_queue = actions[1:]
        self._actions_since_last_llm = 1
        self._actions_on_level += 1
        self._actions_in_game += 1
        
        self.tracker.record(state_sig, immediate.get("name", RESET))
        self._mark_executed(frame, immediate.get("name", RESET))
        return immediate
    
    def _mark_executed(self, frame: FrameInfo, name: str) -> None:
        """Remember the executed action and the board it acted on."""
        self._last_exec = name
        self._last_grid = frame.grid
    
    @staticmethod
    def _probe_actions(frame: FrameInfo) -> list[dict]:
        """Safe scripted opening for a fresh level: each direction once."""
        probes = []
        for engine in ("ACTION1", "ACTION2", "ACTION3", "ACTION4"):
            if engine in frame.available_actions and len(probes) < int(KNOBS["PROBE_MAX"]):
                probes.append({"name": engine, "reasoning": {"probe": True}})
        return probes
    
    _LEVEL_NOTES_RE = re.compile(
        r"LEVEL\s*(\d+)\s*NOTES?:\s*(.+?)(?=\n\s*\n|LEVEL\s*\d+\s*NOTES?:|\Z)",
        re.DOTALL | re.IGNORECASE,
    )
    
    def _absorb_level_notes(self, response: Any) -> None:
        """Extract structured LEVEL N NOTES from model response."""
        text = ""
        if hasattr(response, "get"):
            text = response.get("content", "") or ""
        elif hasattr(response, "content"):
            text = str(response.content or "")
        
        for m in self._LEVEL_NOTES_RE.finditer(text):
            lvl = int(m.group(1))
            notes = m.group(2).strip()
            if notes:
                self._level_notes[lvl] = notes[:200]  # Trim to 200 chars
    
    def _build_user_turn(self, frame: FrameInfo) -> str:
        """Build the user message for the LLM."""
        parts = []
        
        # Header
        parts.append(f"Step {frame.step} | Level {frame.level + 1} | "
                    f"State: {frame.state_name} | Levels completed: {frame.levels_completed}")
        
        # Board
        parts.append(f"\nCurrent board ({frame.shape[0]}×{frame.shape[1]}):\n{frame.ascii}")
        
        # Segmentation
        try:
            parts.append(f"\nSegmentation:\n{frame.segmentation_summary()}")
        except Exception:
            pass
        
        # Available actions
        parts.append(f"\nAvailable actions: {', '.join(frame.available_actions)}")
        
        # Game notes (agent's memory)
        if self._game_notes:
            parts.append(f"\nYour notes: {' | '.join(self._game_notes[-2:])}")
        
        # Level notes (from previous levels)
        if self._level_notes:
            notes_str = " | ".join(f"L{i+1}: {n}" for i, n in sorted(self._level_notes.items())[-3:])
            parts.append(f"\nLevel notes: {notes_str}")
        
        # Run-level lessons
        if self._run_lessons:
            parts.append(f"\nLessons from earlier games: {' | '.join(self._run_lessons[-2:])}")
        
        # Game-over history
        if self._game_overs:
            parts.append(f"\nRecent game-overs: {' | '.join(self._game_overs[-3:])}")
        
        # No-op detection
        if self._noop_recent:
            noop_count = sum(1 for _, changed in self._noop_recent if not changed)
            if noop_count > 3:
                parts.append(f"\nNote: last {noop_count} actions had no effect on the board.")
        
        # Pending notes request
        if self._pending_notes is not None:
            parts.append(f"\nYou just completed level {self._pending_notes + 1}. "
                        "In your notes, briefly state the win condition and any rules you learned.")
            self._pending_notes = None
        
        return "\n".join(parts)
    
    def _parse_response(self, content: str, frame: FrameInfo) -> list[dict]:
        """Parse action(s) from the LLM response."""
        actions = []
        for obj in _extract_action_objects(content):
            action_name = obj.get("action", "").upper()
            
            # Normalize action names
            if action_name in ("UP", "DOWN", "LEFT", "RIGHT"):
                action_name = MODEL_TO_ENGINE.get(action_name, action_name)
            
            if action_name in ACTION_NAMES:
                action = {"name": action_name}
                
                # Handle MOUSE action
                if action_name == "MOUSE" or action_name == "ACTION6":
                    row = obj.get("row")
                    col = obj.get("col")
                    if row is not None and col is not None:
                        action["x"] = col
                        action["y"] = row
                
                # Handle reasoning
                if "reasoning" in obj:
                    action["reasoning"] = {"text": str(obj["reasoning"])}
                
                actions.append(action)
        
        return actions
    
    def _anti_loop_action(self, frame: FrameInfo) -> dict:
        """Force a RESET when stuck in a loop."""
        self._audits_on_level = getattr(self, "_audits_on_level", 0) + 1
        self._game_overs.append(f"Stuck at level {self._last_level}")
        return {"name": RESET, "reasoning": {"loop": True}}
    
    def _fallback_action(self, frame: FrameInfo) -> dict:
        """Fallback: try different directions."""
        for engine in ("ACTION1", "ACTION2", "ACTION3", "ACTION4"):
            if engine in frame.available_actions:
                return {"name": engine, "reasoning": {"fallback": True}}
        return {"name": RESET, "reasoning": {"fallback": True}}
    
    def _trim_context(self) -> None:
        """Trim conversation history to stay within context window."""
        # Keep system message + last N messages
        if len(self._messages) > 10:
            self._messages = [self._messages[0]] + self._messages[-9:]
    
    def _absorb_notes(self, actions: list[dict]) -> None:
        """Extract notes from the first action."""
        if actions and "notes" in actions[0]:
            notes = str(actions[0]["notes"]).strip()
            if notes:
                # Keep only last 2 notes
                self._game_notes.append(notes)
                if len(self._game_notes) > 2:
                    self._game_notes = self._game_notes[-2:]
    
    def _state_signature(self, frame: FrameInfo) -> str:
        """Generate a signature for the current state."""
        return hashlib.md5(
            json.dumps(frame.grid).encode() + str(frame.level).encode()
        ).hexdigest()[:12]
    
    @property
    def total_tokens(self) -> int:
        """Total tokens used across all LLM calls."""
        return self.client.total_tokens
    
    @property
    def total_calls(self) -> int:
        """Total LLM calls made."""
        return self.client.total_calls
    
    def record_result(self, result: dict) -> None:
        """Record the result of a game (for run-level lessons)."""
        # This is called after a game ends
        pass


# ---------------------------------------------------------------------------
# Entry point for testing
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Simple test
    config = LLMConfig.from_env()
    policy = LLMPolicyV7(config)
    
    # Create a dummy frame
    grid = tuple(tuple(0 for _ in range(10)) for _ in range(10))
    frame = FrameInfo(
        grid=grid,
        step=0,
        level=0,
        state_name="PLAYING",
        levels_completed=0,
        available_actions=["ACTION1", "ACTION2", "ACTION3", "ACTION4"],
    )
    
    print("v7 policy created successfully")
    print(f"KNOBS: {KNOBS}")
