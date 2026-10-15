#!/usr/bin/env python3
"""Build the Kaggle notebook for LLM agent v7.

Combines best of v6.9 (goal classifier + counter-picking) with v7-abandon
(early abandon for dead games) + improvements:
- Goal class retry (if UNKNOWN, retry after 10k tokens)
- Early abandon (0 levels after 60k tokens → abandon game)
- Token budget tracking
- Adaptive exploration

Usage:
    python3 build_notebook_v7.py [output.ipynb]
"""
import base64
import json
import os
import sys
from pathlib import Path


def make_cell(source: str, cell_type: str = "code") -> dict:
    """Create a notebook cell."""
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


def encode_file(path: str) -> str:
    """Read a file and return base64-encoded content."""
    return base64.b64encode(Path(path).read_bytes()).decode("ascii")


def build_notebook(output_path: str) -> None:
    """Build the complete Kaggle notebook."""
    
    agent_dir = Path(__file__).parent
    
    # Encode source files
    grid_utils_b64 = encode_file(str(agent_dir / "grid_utils.py"))
    goal_classifier_b64 = encode_file(str(agent_dir / "goal_classifier.py"))
    llm_policy_v7_b64 = encode_file(str(agent_dir / "llm_policy_v7.py"))
    llm_agent_b64 = encode_file(str(agent_dir / "llm_agent_v6.py"))
    
    cells = []
    
    # Cell 1: Markdown intro
    cells.append({
        "cell_type": "markdown",
        "metadata": {"trusted": True},
        "source": [
            "# ARC-AGI-3 LLM Agent v7\n",
            "\n",
            "Kombinacja najlepszych elementów:\n",
            "- **v6.9**: Goal classifier + counter-picking (12 mechanizmów)\n",
            "- **v7-abandon**: Early abandon dla martwych gier (0 poziomów po 60k tokenów)\n",
            "- **Nowości**: Goal class retry, token budget tracking, adaptive exploration\n",
            "\n",
            "**Architektura**: Qwen3.6-27B-FP8 via vLLM, tool-calling REPL z Python sandbox,\n",
            "anti-loop detection, context management.\n",
            "\n",
            "**Datasets**:\n",
            "- `driessmit1/arc3-vllm-h100-wheelhouse-v3` (vLLM + torch wheels)\n",
            "- `driessmit1/vrfai-qwen3-6-27b-fp8-hf-snapshot` (Qwen3.6-27B-FP8 model)\n",
            "\n",
            "**Expected**: LB ~31-35 (vs v6.9 = 24.66, v7-abandon = ~31)\n",
        ],
    })
    
    # Cell 2: Setup
    cells.append(make_cell('''\
import base64
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

TRUE_SUBMISSION = os.environ.get("KAGGLE_IS_COMPETITION_RERUN", "").strip().lower() in {"1", "true", "yes"}
NOTEBOOK_START = time.time()

os.environ["MPLBACKEND"] = "Agg"

cuda_path = "/usr/local/nvidia/lib64"
os.environ["LIBRARY_PATH"] = os.pathsep.join(
    e for e in [cuda_path, *os.environ.get("LIBRARY_PATH", "").split(os.pathsep)] if e
)

WORKING = Path("/kaggle/working")
WORKING.mkdir(parents=True, exist_ok=True)

print(f"TRUE_SUBMISSION={TRUE_SUBMISSION}")
print("GPU check:")
subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"], check=False)
'''))
    
    # Cell 3: Install ARC runtime
    cells.append(make_cell('''\
# Install ARC runtime
print("Installing ARC runtime...")
subprocess.run([
    "pip", "install", "--quiet", "--no-deps",
    "/kaggle/input/arc3-vllm-h100-wheelhouse-v3/arcengine-1.0.0-cp311-cp311-linux_x86_64.whl"
], check=True)
print("✓ ARC runtime installed")
'''))
    
    # Cell 4: Install vLLM
    cells.append(make_cell('''\
# Install vLLM from wheelhouse
print("Installing vLLM from wheelhouse...")
wheelhouse = Path("/kaggle/input/arc3-vllm-h100-wheelhouse-v3")
wheels = list(wheelhouse.glob("*.whl"))
for whl in wheels:
    if whl.name.startswith("arcengine"):
        continue
    subprocess.run(["pip", "install", "--quiet", "--no-deps", str(whl)], check=True)
print(f"✓ Installed {len(wheels)} wheels")
'''))
    
    # Cell 5: Start vLLM server
    cells.append(make_cell('''\
# Start vLLM server
model_path = "/kaggle/input/vrfai-qwen3-6-27b-fp8-hf-snapshot/Qwen3.6-27B-FP8"
print(f"Starting vLLM server with {model_path}...")

vllm_cmd = [
    sys.executable, "-m", "vllm.entrypoints.openai.api_server",
    "--model", model_path,
    "--served-model-name", "qwen3.6-27b-fp8",
    "--host", "127.0.0.1",
    "--port", "8000",
    "--dtype", "bfloat16",
    "--max-model-len", "32768",
    "--gpu-memory-utilization", "0.90",
    "--tensor-parallel-size", "1",
    "--disable-log-requests",
]

server_log = WORKING / "vllm.log"
server_proc = subprocess.Popen(
    vllm_cmd,
    stdout=open(server_log, "w"),
    stderr=subprocess.STDOUT,
    env={**os.environ, "VLLM_ATTENTION_BACKEND": "FLASHINFER"},
)
print(f"vLLM server PID: {server_proc.pid}")

# Wait for server
import time
for i in range(120):
    try:
        import urllib.request
        with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=2):
            print("✓ vLLM server ready")
            break
    except Exception:
        time.sleep(1)
else:
    print("ERROR: vLLM server failed to start")
    sys.exit(1)
'''))
    
    # Cell 6: Deploy agent code
    cells.append(make_cell(f'''
# Deploy agent code
print("Deploying agent code...")

# Grid utilities
grid_utils_src = base64.b64decode("{grid_utils_b64}").decode("utf-8")
(WORKING / "grid_utils.py").write_text(grid_utils_src)

# Goal classifier
goal_classifier_src = base64.b64decode("{goal_classifier_b64}").decode("utf-8")
(WORKING / "goal_classifier.py").write_text(goal_classifier_src)

# LLM policy v7
llm_policy_src = base64.b64decode("{llm_policy_v7_b64}").decode("utf-8")
(WORKING / "llm_policy_v7.py").write_text(llm_policy_src)

# LLM agent adapter
llm_agent_src = base64.b64decode("{llm_agent_b64}").decode("utf-8")
(WORKING / "llm_agent.py").write_text(llm_agent_src)

print("✓ Agent code deployed")
'''))
    
    # Cell 7: Import and configure
    cells.append(make_cell('''\
# Import and configure
sys.path.insert(0, str(WORKING))

from llm_policy_v7 import LLMPolicyV7, LLMConfig
from llm_agent import LLMAgent

# Configure LLM
config = LLMConfig(
    base_url="http://127.0.0.1:8000/v1",
    model_id="qwen3.6-27b-fp8",
    api_key="EMPTY",
    max_output_tokens=2048,
    temperature=0.6,
    enable_thinking=True,
)

print(f"LLM config: {config.base_url} / {config.model_id}")
print("✓ LLM policy v7 ready")
'''))
    
    # Cell 8: Run agent on competition games
    cells.append(make_cell('''\
# Run agent on competition games
import arcengine
from pathlib import Path

games_dir = Path("/kaggle/input/arc-prize-2026-arc-agi-3/games")
games = sorted(games_dir.glob("*.game"))
print(f"Found {len(games)} games")

results = []
for game_path in games:
    print(f"\\n{'='*60}")
    print(f"Game: {game_path.name}")
    print('='*60)
    
    # Load game
    with open(game_path) as f:
        game_data = json.load(f)
    
    env = arcengine.Environment(game_data)
    policy = LLMPolicyV7(config)
    
    # Run game
    max_actions = 400
    for step in range(max_actions):
        frame = env.render()
        
        # Check if game is over
        if frame.state_name in ("WIN", "GAME_OVER"):
            break
        
        # Check if should abandon
        if policy.should_abandon():
            print(f"  [ABANDON] 0 levels after {policy.total_tokens} tokens")
            break
        
        # Get action from policy
        action = policy.choose_action(frame)
        
        # FIX BUG 2: Handle ABANDON action (early abandon)
        # ABANDON means policy wants to stop this game and move to next
        # (not RESET which restarts in same server slot)
        if action.get("name") == "ABANDON":
            print(f"  [ABANDON] 0 levels after {policy.total_tokens} tokens, {step+1} actions")
            break
        
        # Execute action
        env.step(action["name"])
        
        # Progress indicator
        if step % 50 == 0:
            print(f"  Step {step} | Level {frame.level+1} | Tokens: {policy.total_tokens}")
    
    # Record result
    final_frame = env.render()
    result = {
        "game": game_path.name,
        "levels_completed": final_frame.levels_completed,
        "total_actions": step + 1,
        "total_tokens": policy.total_tokens,
        "abandoned": policy._should_abandon,
    }
    results.append(result)
    
    print(f"  Result: {final_frame.levels_completed} levels | {step+1} actions | {policy.total_tokens} tokens")
    
    # Reset for next game
    policy.reset_game()
    env.reset()

print(f"\\n{'='*60}")
print(f"Completed {len(results)} games")
print('='*60)
'''))
    
    # Cell 9: Generate submission
    cells.append(make_cell('''\
# Generate submission.parquet
print("Generating submission.parquet...")

submission = {
    "game_id": [r["game"] for r in results],
    "levels_completed": [r["levels_completed"] for r in results],
    "total_actions": [r["total_actions"] for r in results],
    "total_tokens": [r["total_tokens"] for r in results],
}

import pandas as pd
df = pd.DataFrame(submission)
df.to_parquet(WORKING / "submission.parquet", index=False)

print(f"✓ submission.parquet generated ({len(results)} games)")
print(f"\\nSummary:")
print(f"  Games completed: {len(results)}")
print(f"  Games abandoned: {sum(1 for r in results if r['abandoned'])}")
print(f"  Total levels: {sum(r['levels_completed'] for r in results)}")
print(f"  Total actions: {sum(r['total_actions'] for r in results)}")
print(f"  Total tokens: {sum(r['total_tokens'] for r in results)}")

if TRUE_SUBMISSION:
    print("\\n✓ TRUE_SUBMISSION mode - submission.parquet ready for Kaggle")
else:
    print("\\n⚠ Not in TRUE_SUBMISSION mode - this was a test run")
'''))
    
    # Write notebook
    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "codemirror_mode": {"name": "ipython", "version": 3},
                "file_extension": ".py",
                "mimetype": "text/x-python",
                "name": "python",
                "nbconvert_exporter": "python",
                "pygments_lexer": "ipython3",
                "version": "3.11.0",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 4,
    }
    
    with open(output_path, "w") as f:
        json.dump(notebook, f, indent=2)
    
    print(f"✓ Notebook written to {output_path}")


if __name__ == "__main__":
    output = sys.argv[1] if len(sys.argv) > 1 else "arc-agi-3-llm-agent-v7.ipynb"
    build_notebook(output)
