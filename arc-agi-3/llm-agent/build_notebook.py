"""Build the Kaggle notebook for the LLM-based ARC-AGI-3 agent.

This generates a .ipynb file that:
1. Installs the ARC runtime from competition wheels
2. Installs vLLM from the wheelhouse dataset  
3. Starts a vLLM server with Qwen3.6-27B-FP8
4. Deploys the LLM agent code
5. Runs the agent on all competition games
6. Generates submission.parquet
"""
import base64
import json
import os
from pathlib import Path


def make_cell(source: str, cell_type: str = "code") -> dict:
    """Create a notebook cell."""
    lines = source.split("\n")
    # Each line except the last should end with \n
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
    grid_utils_b64 = encode_file(str(agent_dir / "grid_utils.py"))
    llm_policy_b64 = encode_file(str(agent_dir / "llm_policy.py"))
    llm_agent_b64 = encode_file(str(agent_dir / "llm_agent.py"))
    
    cells = []
    
    # Cell 1: Markdown intro
    cells.append({
        "cell_type": "markdown",
        "metadata": {"trusted": True},
        "source": [
            "# ARC-AGI-3 LLM Agent\n",
            "\n",
            "LLM-based agent using Qwen3.6-27B-FP8 via vLLM. ",
            "Architecture: tool-calling REPL with Python sandbox, anti-loop detection, ",
            "context management. Based on the Duck harness (MIT, Tufa Labs).\n",
            "\n",
            "**Datasets required:**\n",
            "- `driessmit1/arc3-vllm-h100-wheelhouse-v3` (vLLM + torch wheels)\n",
            "- `driessmit1/vrfai-qwen3-6-27b-fp8-hf-snapshot` (Qwen3.6-27B-FP8 model)\n",
        ],
    })
    
    # Cell 2: Setup and configuration
    cells.append(make_cell('''\
import base64
import json
import os
import shutil
import subprocess
import sys
import sysconfig
import time
from pathlib import Path

# Competition rerun detection
TRUE_SUBMISSION = os.environ.get("KAGGLE_IS_COMPETITION_RERUN", "").strip().lower() in {"1", "true", "yes"}
NOTEBOOK_START = time.time()

os.environ["MPLBACKEND"] = "Agg"

# CUDA library path
cuda_path = "/usr/local/nvidia/lib64"
os.environ["LIBRARY_PATH"] = os.pathsep.join(
    e for e in [cuda_path, *os.environ.get("LIBRARY_PATH", "").split(os.pathsep)] if e
)

WORKING = Path("/kaggle/working")
WORKING.mkdir(parents=True, exist_ok=True)

print(f"TRUE_SUBMISSION={TRUE_SUBMISSION}")
print(f"GPU check:")
subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"], check=False)
'''))
    
    # Cell 3: Install ARC runtime
    cells.append(make_cell('''\
# Install ARC runtime from competition wheels
subprocess.check_call([
    sys.executable, "-m", "pip", "install", "--quiet",
    "--no-index", "--no-warn-conflicts", "--disable-pip-version-check",
    "--find-links", "/kaggle/input/competitions/arc-prize-2026-arc-agi-3/arc_agi_3_wheels",
    "arc-agi", "python-dotenv",
], stdout=subprocess.DEVNULL)
print("ARC runtime installed")
'''))
    
    # Cell 4: Install vLLM from wheelhouse
    cells.append(make_cell('''\
# Install vLLM from the wheelhouse dataset
WHEELHOUSE_DATASET = "driessmit1/arc3-vllm-h100-wheelhouse-v3"
MODEL_DATASET = "driessmit1/vrfai-qwen3-6-27b-fp8-hf-snapshot"

# Find the wheelhouse and model paths
def find_dataset_path(slug):
    for candidate in [
        Path(f"/kaggle/input/{slug}"),
        Path(f"/kaggle/input/datasets") / slug.split("/")[0] / slug.split("/")[1],
    ]:
        if candidate.exists():
            return candidate
    # Fallback: search for the slug directory
    for p in Path("/kaggle/input").iterdir():
        if slug.split("/")[-1] in p.name or p.name == slug.split("/")[-1]:
            return p
    return Path(f"/kaggle/input/{slug.split('/')[-1]}")

WHEELHOUSE = find_dataset_path(WHEELHOUSE_DATASET)
MODEL_PATH = find_dataset_path(MODEL_DATASET)

print(f"Wheelhouse: {WHEELHOUSE} (exists: {WHEELHOUSE.exists()})")
print(f"Model: {MODEL_PATH} (exists: {MODEL_PATH.exists()})")

# Install vLLM into a separate site-packages to avoid conflicts
SITE_PACKAGES = WORKING / "vllm_site"
SITE_PACKAGES.mkdir(exist_ok=True)

requirements = WHEELHOUSE / "requirements.lock"
if not requirements.exists():
    # Try alternative names
    for name in ["requirements.txt", "requirements.lock"]:
        alt = WHEELHOUSE / name
        if alt.exists():
            requirements = alt
            break

if requirements.exists():
    print(f"Installing vLLM from {requirements}")
    subprocess.check_call([
        sys.executable, "-m", "pip", "install",
        "--no-index", "--find-links", str(WHEELHOUSE),
        "--requirement", str(requirements),
        "--target", str(SITE_PACKAGES),
        "--upgrade", "--ignore-installed",
        "--only-binary", ":all:", "--no-compile",
        "--disable-pip-version-check", "--no-warn-conflicts",
    ])
    print("vLLM installed")
else:
    print(f"WARNING: No requirements file found in {WHEELHOUSE}")
    print(f"Contents: {list(WHEELHOUSE.iterdir())[:10]}")
    # Try direct install of vllm wheel
    wheels = list(WHEELHOUSE.glob("vllm-*.whl"))
    if wheels:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install",
            "--no-index", "--find-links", str(WHEELHOUSE),
            "--target", str(SITE_PACKAGES),
            str(wheels[0]),
        ])
        print(f"Installed vLLM wheel: {wheels[0].name}")

# Add to Python path
os.environ["PYTHONPATH"] = str(SITE_PACKAGES) + os.pathsep + os.environ.get("PYTHONPATH", "")
sys.path.insert(0, str(SITE_PACKAGES))
'''))
    
    # Cell 5: Start vLLM server
    cells.append(make_cell('''\
import urllib.request

VLLM_HOST = "127.0.0.1"
VLLM_PORT = 1234
VLLM_BASE_URL = f"http://{VLLM_HOST}:{VLLM_PORT}/v1"
SERVED_MODEL = "vrfai/Qwen3.6-27B-FP8"
VLLM_LOG = WORKING / "vllm_server.log"
VLLM_PID_FILE = WORKING / "vllm_server.pid"

# Kill any existing server
if VLLM_PID_FILE.exists():
    try:
        os.kill(int(VLLM_PID_FILE.read_text().strip()), 9)
    except Exception:
        pass
    VLLM_PID_FILE.unlink(missing_ok=True)

# Start vLLM OpenAI-compatible server
vllm_env = os.environ.copy()
vllm_env.update({
    "USE_TF": "0",
    "TRANSFORMERS_NO_TF": "1",
    "TRANSFORMERS_NO_TORCHVISION": "1",
    "VLLM_NO_USAGE_STATS": "1",
    "PYTHONPATH": str(SITE_PACKAGES),
})

cmd = [
    sys.executable, "-m", "vllm.entrypoints.openai.api_server",
    "--model", str(MODEL_PATH),
    "--served-model-name", SERVED_MODEL,
    "--host", VLLM_HOST,
    "--port", str(VLLM_PORT),
    "--tensor-parallel-size", "1",
    "--enable-auto-tool-choice",
    "--tool-call-parser", "qwen3_coder",
    "--generation-config", "vllm",
    "--enable-prefix-caching",
    "--default-chat-template-kwargs", '{"preserve_thinking": true}',
    "--reasoning-parser", "qwen3",
    "--max-model-len", "65536",
]

print(f"Starting vLLM: {' '.join(cmd[:8])}...")
log_fh = open(VLLM_LOG, "w")
proc = subprocess.Popen(cmd, env=vllm_env, stdout=log_fh, stderr=subprocess.STDOUT, text=True)
VLLM_PID_FILE.write_text(str(proc.pid))

# Wait for server to be ready
print("Waiting for vLLM server...", flush=True)
deadline = time.time() + 600
ready = False
while time.time() < deadline:
    try:
        req = urllib.request.Request(f"{VLLM_BASE_URL}/models")
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status < 500:
                ready = True
                break
    except Exception:
        pass
    time.sleep(5)
    # Check if process is still alive
    if proc.poll() is not None:
        print(f"vLLM server exited with code {proc.returncode}")
        print(f"Log tail: {VLLM_LOG.read_text()[-2000:]}")
        break

if ready:
    print("vLLM server ready!")
    # Smoke test
    payload = json.dumps({
        "model": SERVED_MODEL,
        "messages": [{"role": "user", "content": "Say hello in one word."}],
        "max_tokens": 16,
        "temperature": 0.0,
    }).encode()
    req = urllib.request.Request(
        f"{VLLM_BASE_URL}/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read())
    reply = result["choices"][0]["message"].get("content", "").strip()
    print(f"Smoke test reply: {reply!r}")
    VLLM_OK = True
else:
    print("ERROR: vLLM server did not start. Log:")
    print(VLLM_LOG.read_text()[-3000:])
    VLLM_OK = False
'''))
    
    # Cell 6: Deploy agent code
    cells.append(make_cell(f'''
# Deploy agent source files
agent_dir = Path("/tmp/arc_llm_agent")
agent_dir.mkdir(parents=True, exist_ok=True)

(agent_dir / "__init__.py").write_text("""# LLM agent package""")
(agent_dir / "grid_utils.py").write_bytes(base64.b64decode({json.dumps(grid_utils_b64)}))
(agent_dir / "llm_policy.py").write_bytes(base64.b64decode({json.dumps(llm_policy_b64)}))
(agent_dir / "llm_agent.py").write_bytes(base64.b64decode({json.dumps(llm_agent_b64)}))

# Set environment for the agent
os.environ["LLM_BASE_URL"] = VLLM_BASE_URL
os.environ["LLM_MODEL_ID"] = SERVED_MODEL
os.environ["LLM_API_KEY"] = "EMPTY"
os.environ["LLM_CONTEXT_WINDOW"] = "32768"
os.environ["LLM_MAX_OUTPUT"] = "2048"
os.environ["LLM_TEMPERATURE"] = "0.6"
os.environ["LLM_TIMEOUT"] = "120"
os.environ["LLM_MULTIMODAL"] = "0"  # start without images to save tokens

print(f"Agent deployed in {{agent_dir}}")
print(f"LLM config: {{SERVED_MODEL}} @ {{VLLM_BASE_URL}}")
'''))
    
    # Cell 7: Run competition
    cells.append(make_cell('''\
import shutil
from pathlib import Path

if TRUE_SUBMISSION:
    # === COMPETITION RUN ===
    # Copy the ARC-AGI-3-Agents framework
    framework_src = Path("/kaggle/input/competitions/arc-prize-2026-arc-agi-3/ARC-AGI-3-Agents")
    framework = WORKING / "ARC-AGI-3-Agents"
    if framework.exists():
        shutil.rmtree(framework)
    shutil.copytree(framework_src, framework)
    
    # Copy our agent into the templates directory
    target = framework / "agents" / "templates"
    target.mkdir(parents=True, exist_ok=True)
    for f in ("__init__.py", "grid_utils.py", "llm_policy.py", "llm_agent.py"):
        shutil.copy2(Path("/tmp/arc_llm_agent") / f, target / f)
    
    # Register our agent
    init_content = """
\\"\\\"\\\"Agent registry for ARC-AGI-3 LLM agent.\\"\\\"\\\"
from typing import Type
from dotenv import load_dotenv
from .agent import Agent, Playback
from .recorder import Recorder
from .swarm import Swarm
from .templates.random_agent import Random
from .templates.my_agent import MyAgent
from .templates.llm_agent import LLMAgent

load_dotenv()
AVAILABLE_AGENTS: dict[str, Type[Agent]] = {
    "random": Random,
    "myagent": MyAgent,
    "llmagent": LLMAgent,
}
for recording in Recorder.list():
    AVAILABLE_AGENTS[recording] = Playback
"""
    (framework / "agents" / "__init__.py").write_text(init_content)
    
    # Write .env
    (framework / ".env").write_text("\\n".join([
        "SCHEME=http",
        "HOST=gateway",
        "PORT=8001",
        "ARC_API_KEY=competition-gateway",
        "ARC_BASE_URL=http://gateway:8001/",
        "OPERATION_MODE=online",
        "ENVIRONMENTS_DIR=",
        f"RECORDINGS_DIR={WORKING}/recordings",
        f"LLM_BASE_URL={VLLM_BASE_URL}",
        f"LLM_MODEL_ID={SERVED_MODEL}",
        "LLM_API_KEY=EMPTY",
        "LLM_CONTEXT_WINDOW=32768",
        "LLM_MAX_OUTPUT=2048",
        "LLM_TEMPERATURE=0.6",
        "LLM_TIMEOUT=120",
        "LLM_MULTIMODAL=0",
    ]) + "\\n")
    
    # Wait for gateway
    import urllib.request
    print("Waiting for competition gateway...")
    deadline = time.time() + 600
    while time.time() < deadline:
        try:
            with urllib.request.urlopen("http://gateway:8001/api/games", timeout=10) as r:
                if r.status < 500:
                    break
        except Exception:
            pass
        time.sleep(5)
    
    # Run the agent
    run_env = os.environ.copy()
    run_env["MPLBACKEND"] = "Agg"
    run_env["LLM_BASE_URL"] = VLLM_BASE_URL
    run_env["LLM_MODEL_ID"] = SERVED_MODEL
    run_env["PYTHONPATH"] = str(SITE_PACKAGES) + os.pathsep + run_env.get("PYTHONPATH", "")
    
    # Choose agent: LLM if vLLM started successfully, otherwise fallback to heuristic
    if VLLM_OK:
        agent_name = "llmagent"
        print(f"Starting LLM agent run ({agent_name})...")
    else:
        agent_name = "myagent"
        print("WARNING: vLLM not available, falling back to heuristic agent (myagent)")
    
    result = subprocess.run(
        [sys.executable, "main.py", "--agent", agent_name],
        cwd=framework,
        env=run_env,
        capture_output=True,
        text=True,
        timeout=32000,  # ~9 hours
    )
    print("STDOUT:", result.stdout[-3000:] if result.stdout else "(empty)")
    print("STDERR:", result.stderr[-3000:] if result.stderr else "(empty)")
    print(f"Return code: {result.returncode}")
    
else:
    # === SAVE PHASE (non-competition) ===
    import pandas as pd
    placeholder = pd.DataFrame(
        [["placeholder_0", "placeholder", True, 0.0]],
        columns=["row_id", "game_id", "end_of_game", "score"],
    )
    placeholder.to_parquet(WORKING / "submission.parquet", index=False)
    print("Wrote save-phase placeholder submission.parquet")
'''))
    
    # Cell 8: Diagnostics
    cells.append(make_cell('''\
# Print diagnostics
elapsed = time.time() - NOTEBOOK_START
print(f"Notebook elapsed: {elapsed:.0f}s ({elapsed/60:.1f} min)")

# Show vLLM server log tail
if VLLM_LOG.exists():
    log = VLLM_LOG.read_text()
    print(f"\\nvLLM log ({len(log)} chars), last 500:")
    print(log[-500:])

# Show any recordings
recordings = WORKING / "recordings"
if recordings.exists():
    files = list(recordings.iterdir())
    print(f"\\nRecordings: {len(files)} files")
    for f in files[:5]:
        print(f"  {f.name} ({f.stat().st_size} bytes)")
'''))
    
    # Assemble notebook
    notebook = {
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.12.0",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 4,
        "cells": cells,
    }
    
    # Fix source format: ensure proper line endings
    for cell in notebook["cells"]:
        lines = cell["source"]
        if isinstance(lines, str):
            cell["source"] = [line + "\n" for line in lines.split("\n")]
            if cell["source"]:
                cell["source"][-1] = cell["source"][-1].rstrip("\n")
        elif isinstance(lines, list):
            fixed = []
            for i, line in enumerate(lines):
                if i < len(lines) - 1 and not line.endswith("\n"):
                    fixed.append(line + "\n")
                else:
                    fixed.append(line)
            cell["source"] = fixed
    
    Path(output_path).write_text(json.dumps(notebook, indent=1))
    print(f"Notebook written to {output_path} ({len(notebook['cells'])} cells)")


if __name__ == "__main__":
    import sys
    output = sys.argv[1] if len(sys.argv) > 1 else "arc-agi-3-llm-agent.ipynb"
    build_notebook(output)
