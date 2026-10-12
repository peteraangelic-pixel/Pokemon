"""Build the T4-compatible Kaggle notebook for ARC-AGI-3 LLM agent."""
import base64
import json
from pathlib import Path


def make_cell(source: str, cell_type: str = "code") -> dict:
    lines = source.split("\n")
    formatted = [line + "\n" for line in lines[:-1]]
    if lines:
        formatted.append(lines[-1])
    return {
        "cell_type": cell_type,
        "metadata": {"trusted": True},
        "source": formatted,
        "outputs": [],
        "execution_count": None,
    }


def build_notebook(output_path: str) -> None:
    cells = []

    # Markdown
    cells.append({
        "cell_type": "markdown",
        "metadata": {"trusted": True},
        "source": [
            "# ARC-AGI-3 LLM Agent (Qwen2.5-7B NF4 for T4)\n",
            "\n",
            "LLM agent using Qwen2.5-7B-Instruct with NF4 quantization via bitsandbytes.\n",
            "Designed for Tesla T4 GPU (15GB VRAM).\n",
        ],
    })

    # Cell 1: Setup
    cells.append(make_cell('''import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

TRUE_SUBMISSION = os.environ.get("KAGGLE_IS_COMPETITION_RERUN", "").strip().lower() in {"1", "true", "yes"}
NOTEBOOK_START = time.time()
os.environ["MPLBACKEND"] = "Agg"
os.environ["PYDEVD_DISABLE_FILE_VALIDATION"] = "1"

WORKING = Path("/kaggle/working")
WORKING.mkdir(parents=True, exist_ok=True)

print(f"TRUE_SUBMISSION={TRUE_SUBMISSION}")
print("GPU check:")
subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,memory.free", "--format=csv,noheader"])'''))

    # Cell 2: Install ARC + bitsandbytes
    cells.append(make_cell('''# Install ARC runtime
subprocess.check_call([
    sys.executable, "-m", "pip", "install", "--quiet",
    "--no-index", "--no-warn-conflicts", "--disable-pip-version-check",
    "--find-links", "/kaggle/input/competitions/arc-prize-2026-arc-agi-3/arc_agi_3_wheels",
    "arc-agi", "python-dotenv",
], stdout=subprocess.DEVNULL)
print("ARC runtime installed")

# Check bitsandbytes
try:
    import bitsandbytes
    print(f"bitsandbytes already installed: {bitsandbytes.__version__}")
except ImportError:
    print("bitsandbytes not found, installing from dataset...")
    # Find bitsandbytes dataset
    bnb_path = None
    for p in Path("/kaggle/input").iterdir():
        if "bitsandbytes" in p.name.lower():
            bnb_path = p
            print(f"Found bitsandbytes at: {bnb_path}")
            break
    
    if bnb_path and bnb_path.exists():
        # Install from local wheel files
        wheels = list(bnb_path.glob("*.whl"))
        if wheels:
            print(f"Installing from {len(wheels)} wheel(s)...")
            subprocess.check_call([
                sys.executable, "-m", "pip", "install",
                "--no-index", "--no-deps",
                *[str(w) for w in wheels],
                "--quiet"
            ])
            import bitsandbytes
            print(f"bitsandbytes installed: {bitsandbytes.__version__}")
        else:
            # Try pip install --find-links
            subprocess.check_call([
                sys.executable, "-m", "pip", "install",
                "--no-index", "--find-links", str(bnb_path),
                "bitsandbytes", "--quiet"
            ])
            import bitsandbytes
            print(f"bitsandbytes installed: {bitsandbytes.__version__}")
    else:
        print("ERROR: bitsandbytes dataset not found!")
        raise RuntimeError("bitsandbytes not available")'''))

    # Cell 3: Find model
    cells.append(make_cell('''# Find model path
print("Searching for Qwen2.5-7B-Instruct...")
MODEL_PATH = None
for root, dirs, files in os.walk("/kaggle/input"):
    if "config.json" in files:
        config_path = os.path.join(root, "config.json")
        try:
            cfg = json.load(open(config_path))
            if cfg.get("model_type") in ("qwen2", "qwen"):
                MODEL_PATH = Path(root)
                print(f"Found Qwen2 model at: {MODEL_PATH}")
                break
        except Exception:
            pass

if MODEL_PATH is None:
    for p in sorted(Path("/kaggle/input").iterdir()):
        if p.is_dir() and (p / "config.json").exists():
            MODEL_PATH = p
            print(f"Found model at: {MODEL_PATH}")
            break

if MODEL_PATH is None:
    MODEL_PATH = Path("/kaggle/input/qwen2-5-7b-instruct")
    print(f"Fallback: {MODEL_PATH}")

print(f"Model path: {MODEL_PATH}")
print(f"Exists: {MODEL_PATH.exists()}")
if MODEL_PATH.exists():
    files = sorted(f.name for f in MODEL_PATH.iterdir())
    print(f"Files ({len(files)}): {files[:15]}")
    total = sum(f.stat().st_size for f in MODEL_PATH.iterdir() if f.is_file())
    print(f"Total: {total / 1e9:.1f} GB")'''))

    # Cell 4: Load model
    cells.append(make_cell('''import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

print("Loading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(str(MODEL_PATH), trust_remote_code=True)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

print("Configuring NF4...")
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_use_double_quant=True,
    bnb_4bit_compute_dtype=torch.float16,
)

print("Loading model with NF4...")
model = AutoModelForCausalLM.from_pretrained(
    str(MODEL_PATH),
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True,
    torch_dtype=torch.float16,
)
model.eval()

print("\\nModel loaded! GPU memory:")
subprocess.run(["nvidia-smi", "--query-gpu=memory.used,memory.free", "--format=csv,noheader"])
print(f"Config: {model.config.num_hidden_layers} layers, {model.config.hidden_size} hidden")

# Smoke test
print("\\nSmoke test...")
test_input = tokenizer("Hello!", return_tensors="pt").to(model.device)
with torch.no_grad():
    output = model.generate(**test_input, max_new_tokens=15, do_sample=False)
response = tokenizer.decode(output[0], skip_special_tokens=True)
print(f"Response: {response!r}")
print("\\nMODEL READY!")'''))

    # Cell 5: Deploy agent code (base64 encoded)
    agent_code = r'''"""LLM agent for ARC-AGI-3 using Qwen2.5-7B on T4."""
import hashlib
import json
import os
import random
import re
import time
import threading
from typing import Any

from arcengine import ActionInput, FrameData, GameAction, GameState
from agents.agent import Agent

RESET = "RESET"
COMPLEX_ACTION = "ACTION6"
MODEL_TO_ENGINE = {
    "UP": "ACTION1", "DOWN": "ACTION2", "LEFT": "ACTION3", "RIGHT": "ACTION4",
    "MOUSE": "ACTION6", "CLICK": "ACTION6",
}
ENGINE_TO_MODEL = {v: k for k, v in MODEL_TO_ENGINE.items()}
ENGINE_TO_MODEL.update({"ACTION1": "UP", "ACTION2": "DOWN", "ACTION3": "LEFT", "ACTION4": "RIGHT"})

ARC_COLOR_CHARS = "WwgGcBMPRbSYOrNp"
ARC_COLOR_LEGEND = (
    "W=white, w=light gray, g=gray, G=dark gray, c=charcoal, B=black, "
    "M=magenta, P=pink, R=red, b=blue, S=sky blue, Y=yellow, O=orange, "
    "r=dark red, N=light green, p=purple"
)


def format_grid_ascii(grid):
    if not grid:
        return "(empty grid)"
    lines = []
    for row in grid:
        chars = [ARC_COLOR_CHARS[max(0, min(15, int(v)))] for v in row]
        lines.append("".join(chars))
    return "\n".join(lines)


SYSTEM_PROMPT = (
    "You are an expert puzzle solver playing a grid-based game.\n\n"
    f"COLOR LEGEND: {ARC_COLOR_LEGEND}\n\n"
    "The game board is a 64x64 color grid. You take actions to solve puzzles.\n\n"
    "AVAILABLE ACTIONS:\n"
    "- UP/DOWN/LEFT/RIGHT: move in a direction\n"
    "- MOUSE(row=N,col=M): click at position\n\n"
    "Each turn, output a JSON action on the LAST line:\n"
    '```json\n{"action": "UP", "reasoning": "brief explanation"}\n```\n'
    'For MOUSE: {"action": "MOUSE", "row": 5, "col": 10, "reasoning": "..."}\n\n'
    "STRATEGIES:\n"
    "- Explore by moving in different directions\n"
    "- Identify the player avatar (distinct colored shape that moves)\n"
    "- Find obstacles, targets, and interactive objects\n"
    "- For navigation, plan paths mentally\n"
    "- If stuck for 10+ actions, change strategy radically\n"
    "- Do not click on HUD elements (bars at edges)\n"
    "- Objects are multi-tile connected components of the same color\n\n"
    "Be decisive. Always output exactly one JSON action block."
)


def extract_grid(frame_data):
    for attr_fn in [
        lambda f: f.raw_state.data,
        lambda f: f.raw_state.planes[0] if f.raw_state.planes else None,
        lambda f: f.planes[0] if hasattr(f, "planes") and f.planes else None,
    ]:
        try:
            data = attr_fn(frame_data)
            if data is None:
                continue
            if hasattr(data, "tolist"):
                rows = data.tolist()
            else:
                rows = list(data)
            if rows and rows[0]:
                return tuple(tuple(int(c) for c in row) for row in rows)
        except Exception:
            continue
    return ((0,) * 64,) * 64


def frame_to_info(frame_data):
    grid = extract_grid(frame_data)
    try:
        state = frame_data.state
        state_name = state.name if hasattr(state, "name") else str(state)
    except Exception:
        state_name = "PLAYING"
    try:
        levels_completed = int(frame_data.levels_completed)
    except Exception:
        levels_completed = 0
    available = []
    try:
        for act_id in frame_data.available_actions:
            try:
                act = GameAction.from_id(int(act_id))
                if act.name != "RESET":
                    available.append(act.name)
            except Exception:
                pass
    except Exception:
        available = ["ACTION1", "ACTION2", "ACTION3", "ACTION4", "ACTION5", "ACTION6", "ACTION7"]
    try:
        step = int(frame_data.step)
    except Exception:
        step = 0
    return {
        "grid": grid, "step": step, "level": levels_completed + 1,
        "state_name": state_name, "levels_completed": levels_completed,
        "available_actions": available,
    }


class LLMAgent(Agent):
    _ACTION_LOCK = threading.RLock()
    ACTION_BUDGET = 400
    MAX_ACTIONS = ACTION_BUDGET
    GAME_TIME_LIMIT = 240

    _model = None
    _tokenizer = None
    _conversation = []
    _game_over_count = 0
    _total_actions = 0
    _unique_states = set()
    _recent_sigs = []
    _recent_actions = []
    _last_level = 0
    _game_start = 0
    _actions_in_game = 0
    _first_action = True

    @classmethod
    def set_model(cls, model, tokenizer):
        cls._model = model
        cls._tokenizer = tokenizer

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def name(self):
        return f"{super().name}.llm-t4-v1"

    def is_done(self, frames, latest_frame):
        if self._actions_in_game >= self.ACTION_BUDGET:
            return True
        try:
            if latest_frame.state is GameState.WIN:
                return True
        except Exception:
            pass
        if time.time() - self._game_start > self.GAME_TIME_LIMIT:
            return True
        return False

    @staticmethod
    def _to_game_action(proposal):
        action_name = proposal.get("name", "RESET")
        try:
            action = GameAction[action_name]
        except KeyError:
            action = GameAction.RESET
        if action.is_complex():
            x = proposal.get("x", 0) or 0
            y = proposal.get("y", 0) or 0
            action.set_data({"x": max(0, min(63, int(x))), "y": max(0, min(63, int(y)))})
        else:
            action.set_data({})
        action.reasoning = proposal.get("reasoning", {})
        return action

    def _state_sig(self, frame_info):
        grid = frame_info["grid"]
        sampled = []
        for r in range(0, len(grid), 4):
            row_s = [grid[r][c] for c in range(0, len(grid[r]), 4)]
            sampled.append(tuple(row_s))
        payload = f'{frame_info["level"]}:{frame_info["state_name"]}:{sampled}'.encode()
        return hashlib.md5(payload).hexdigest()[:12]

    def _is_looped(self):
        if len(self._recent_sigs) < 6:
            return False
        last6 = self._recent_sigs[-6:]
        if last6[0] == last6[2] == last6[4] and last6[1] == last6[3] == last6[5]:
            return True
        if len(self._recent_actions) >= 6 and len(set(self._recent_actions[-6:])) == 1:
            return True
        if len(self._recent_sigs) >= 4 and len(set(self._recent_sigs[-4:])) == 1:
            return True
        return False

    def _build_user_turn(self, frame_info):
        parts = [
            f'=== Turn {self._total_actions + 1} | Level {frame_info["level"]} | '
            f'Step {frame_info["step"]} | State: {frame_info["state_name"]} ===',
            f'Valid actions: {", ".join(ENGINE_TO_MODEL.get(a, a) for a in frame_info["available_actions"])}',
        ]
        if self._total_actions > 0:
            parts.append(
                f"Stats: {self._total_actions} actions, {len(self._unique_states)} unique states, "
                f"{self._game_over_count} deaths"
            )
        rows = len(frame_info["grid"])
        cols = len(frame_info["grid"][0]) if frame_info["grid"] else 0
        if rows <= 40 and cols <= 40:
            parts.append(f"\nBoard ({rows}x{cols}):\n{format_grid_ascii(frame_info['grid'])}")
        else:
            parts.append(f"\nBoard is {rows}x{cols} (large)")
        if self._recent_actions:
            recent = self._recent_actions[-5:]
            parts.append(f'\nRecent: {" -> ".join(ENGINE_TO_MODEL.get(a, a) for a in recent)}')
        if self._is_looped():
            parts.append("\nWARNING: Stuck in a loop! Try a COMPLETELY different approach.")
        return "\n".join(parts)

    def _call_llm(self, frame_info):
        if not self._conversation:
            self._conversation.append({"role": "system", "content": SYSTEM_PROMPT})

        user_content = self._build_user_turn(frame_info)
        self._conversation.append({"role": "user", "content": user_content})

        if len(self._conversation) > 20:
            system = [m for m in self._conversation if m["role"] == "system"]
            others = [m for m in self._conversation if m["role"] != "system"]
            self._conversation = system + others[-16:]

        text = self._tokenizer.apply_chat_template(
            self._conversation, tokenize=False, add_generation_prompt=True
        )
        inputs = self._tokenizer(text, return_tensors="pt").to(self._model.device)

        with torch.no_grad():
            outputs = self._model.generate(
                **inputs, max_new_tokens=256, do_sample=True,
                temperature=0.6, top_p=0.95, pad_token_id=self._tokenizer.eos_token_id,
            )

        new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
        response = self._tokenizer.decode(new_tokens, skip_special_tokens=True)
        self._conversation.append({"role": "assistant", "content": response})

        return self._parse_response(response, frame_info)

    def _parse_response(self, text, frame_info):
        json_blocks = re.findall(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
        if not json_blocks:
            json_blocks = re.findall(r'\{[^{}]*"action"[^{}]*\}', text)

        for block in json_blocks:
            try:
                parsed = json.loads(block)
                action_name = str(parsed.get("action", "")).upper().strip()
                if not action_name:
                    continue
                engine_name = MODEL_TO_ENGINE.get(action_name, action_name)
                valid = set(frame_info["available_actions"]) | {"RESET"}
                if engine_name not in valid:
                    for avail in frame_info["available_actions"]:
                        if avail in action_name or action_name in avail:
                            engine_name = avail
                            break
                    else:
                        continue
                result = {"name": engine_name, "reasoning": {}}
                if engine_name == COMPLEX_ACTION:
                    row = parsed.get("row", parsed.get("y", 0))
                    col = parsed.get("col", parsed.get("x", 0))
                    result["x"] = int(col)
                    result["y"] = int(row)
                reasoning = parsed.get("reasoning", "")
                if reasoning:
                    result["reasoning"]["llm"] = str(reasoning)[:200]
                return result
            except (json.JSONDecodeError, ValueError):
                continue

        text_upper = text.upper()
        for pattern, engine_name in [
            (r'\bUP\b', "ACTION1"), (r'\bDOWN\b', "ACTION2"),
            (r'\bLEFT\b', "ACTION3"), (r'\bRIGHT\b', "ACTION4"),
            (r'\bRESET\b', "RESET"),
        ]:
            if re.search(pattern, text_upper):
                if engine_name in frame_info["available_actions"] or engine_name == "RESET":
                    return {"name": engine_name, "reasoning": {"from_text": True}}
        return {"name": "RESET", "reasoning": {"parse_failed": True}}

    def choose_action(self, frames, latest_frame):
        self._ACTION_LOCK.acquire()
        try:
            frame_info = frame_to_info(latest_frame)

            if self._first_action:
                self._first_action = False
                self._game_start = time.time()
                self._game_over_count = 0
                self._total_actions = 0
                self._unique_states.clear()
                self._recent_sigs.clear()
                self._recent_actions.clear()
                self._conversation.clear()
                self._last_level = 0
                self._actions_in_game = 0

            if frame_info["state_name"] == "GAME_OVER":
                self._game_over_count += 1
                action = GameAction.RESET
                action.set_data({})
                action.reasoning = {"auto_reset": True}
                return action

            sig = self._state_sig(frame_info)
            self._recent_sigs.append(sig)
            if len(self._recent_sigs) > 12:
                self._recent_sigs = self._recent_sigs[-12:]

            if frame_info["levels_completed"] != self._last_level:
                self._last_level = frame_info["levels_completed"]
                if self._conversation:
                    self._conversation.append({
                        "role": "user",
                        "content": f"[LEVEL COMPLETED! Now on level {frame_info['levels_completed'] + 1}. Re-assess.]"
                    })

            if self._is_looped():
                available = [a for a in frame_info["available_actions"] if a != "RESET"]
                if available:
                    choice = random.choice(available)
                    self._recent_actions.append(choice)
                    if len(self._recent_actions) > 12:
                        self._recent_actions = self._recent_actions[-12:]
                    self._total_actions += 1
                    self._unique_states.add(sig)
                    self._actions_in_game += 1
                    return {"name": choice, "reasoning": {"anti_loop": True}}

            action_dict = self._call_llm(frame_info)
            self._total_actions += 1
            self._unique_states.add(sig)
            self._recent_actions.append(action_dict.get("name", "RESET"))
            if len(self._recent_actions) > 12:
                self._recent_actions = self._recent_actions[-12:]
            self._actions_in_game += 1

            return self._to_game_action(action_dict)

        except Exception as e:
            import traceback
            print(f"[LLMAgent] Error: {e}")
            traceback.print_exc()
            action = GameAction.RESET
            action.set_data({})
            action.reasoning = {"error": str(e)}
            return action
        finally:
            try:
                self._ACTION_LOCK.release()
            except RuntimeError:
                pass

    def take_action(self, action):
        try:
            frame = super().take_action(action)
            if frame is not None:
                frame.action_input = ActionInput(
                    id=action,
                    data=action.action_data.model_dump(),
                    reasoning=getattr(action, "reasoning", None),
                )
            return frame
        finally:
            pass

    def finalize_diagnostics(self):
        elapsed = time.time() - self._game_start
        print(f"[LLMAgent] Game done: {self._actions_in_game} actions in {elapsed:.0f}s, "
              f"{len(self._unique_states)} unique states, {self._game_over_count} deaths")
'''

    agent_b64 = base64.b64encode(agent_code.encode()).decode()
    cells.append(make_cell(f'''# Deploy agent code (base64 encoded)
import base64
agent_b64 = "{agent_b64}"
agent_code = base64.b64decode(agent_b64).decode()
agent_dir = Path("/tmp/arc_llm_t4")
agent_dir.mkdir(parents=True, exist_ok=True)
(agent_dir / "__init__.py").write_text("")
(agent_dir / "llm_agent.py").write_text(agent_code)
print(f"Agent deployed to {{agent_dir}} ({{len(agent_code)}} chars)")
# Verify it compiles
compile(agent_code, "llm_agent.py", "exec")
print("Agent code compiles OK")'''))

    # Cell 6: Run
    cells.append(make_cell('''import torch
import shutil
import urllib.request

if TRUE_SUBMISSION:
    framework_src = Path("/kaggle/input/competitions/arc-prize-2026-arc-agi-3/ARC-AGI-3-Agents")
    framework = WORKING / "ARC-AGI-3-Agents"
    if framework.exists():
        shutil.rmtree(framework)
    shutil.copytree(framework_src, framework)

    target = framework / "agents" / "templates"
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path("/tmp/arc_llm_t4/llm_agent.py"), target / "llm_agent.py")
    (target / "__init__.py").write_text("")

    # Register agent
    NEWLINE = chr(10)
    init_py = NEWLINE.join([
        '"""Agent registry."""',
        'from typing import Type',
        'from dotenv import load_dotenv',
        'from .agent import Agent, Playback',
        'from .recorder import Recorder',
        'from .swarm import Swarm',
        'from .templates.random_agent import Random',
        'from .templates.my_agent import MyAgent',
        'from .templates.llm_agent import LLMAgent',
        '',
        'load_dotenv()',
        'AVAILABLE_AGENTS = {"random": Random, "myagent": MyAgent, "llmagent": LLMAgent}',
        'for recording in Recorder.list():',
        '    AVAILABLE_AGENTS[recording] = Playback',
    ]) + NEWLINE
    (framework / "agents" / "__init__.py").write_text(init_py)

    env_content = "\\n".join([
        "SCHEME=http", "HOST=gateway", "PORT=8001",
        "ARC_API_KEY=competition-gateway",
        "ARC_BASE_URL=http://gateway:8001/",
        "OPERATION_MODE=online", "ENVIRONMENTS_DIR=",
        f"RECORDINGS_DIR={WORKING}/recordings",
    ]) + "\\n"
    (framework / ".env").write_text(env_content)

    # Set model on agent class
    sys.path.insert(0, str(target))
    from llm_agent import LLMAgent as AgentClass
    AgentClass.set_model(model, tokenizer)

    # Wait for gateway
    print("Waiting for gateway...")
    deadline = time.time() + 600
    while time.time() < deadline:
        try:
            with urllib.request.urlopen("http://gateway:8001/api/games", timeout=10) as r:
                if r.status < 500:
                    break
        except Exception:
            pass
        time.sleep(5)

    run_env = os.environ.copy()
    run_env["MPLBACKEND"] = "Agg"
    run_env["PYDEVD_DISABLE_FILE_VALIDATION"] = "1"

    print("Starting LLM agent run...")
    result = subprocess.run(
        [sys.executable, "main.py", "--agent", "llmagent"],
        cwd=framework, env=run_env,
        capture_output=True, text=True, timeout=32000,
    )
    print("STDOUT:", result.stdout[-3000:] if result.stdout else "(empty)")
    print("STDERR:", result.stderr[-3000:] if result.stderr else "(empty)")
    print(f"Return code: {result.returncode}")
else:
    import pandas as pd
    placeholder = pd.DataFrame(
        [["placeholder_0", "placeholder", True, 0.0]],
        columns=["row_id", "game_id", "end_of_game", "score"],
    )
    placeholder.to_parquet(WORKING / "submission.parquet", index=False)
    print("Wrote save-phase placeholder submission.parquet")'''))

    # Cell 7: Diagnostics
    cells.append(make_cell('''elapsed = time.time() - NOTEBOOK_START
print(f"Notebook elapsed: {elapsed:.0f}s ({elapsed/60:.1f} min)")'''))

    # Build
    notebook = {
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.12.0"},
        },
        "nbformat": 4,
        "nbformat_minor": 4,
        "cells": cells,
    }

    for cell in notebook["cells"]:
        lines = cell["source"]
        if isinstance(lines, list) and lines:
            fixed = []
            for i, line in enumerate(lines):
                if i < len(lines) - 1 and not line.endswith("\n"):
                    fixed.append(line + "\n")
                else:
                    fixed.append(line)
            cell["source"] = fixed

    Path(output_path).write_text(json.dumps(notebook, indent=1))
    print(f"Notebook written to {output_path} ({len(cells)} cells)")


if __name__ == "__main__":
    import sys
    output = sys.argv[1] if len(sys.argv) > 1 else "arc-agi-3-llm-agent-t4.ipynb"
    build_notebook(output)
