#!/usr/bin/env python3
"""
Build Kaggle notebook for ARC-AGI-3 LLM Agent v7.0

v7.0 improvements:
- Goal classifier (COVER/COPY/REACH/REDUCE/PLACE/FLOW/ALIGN/LOCAL_CONSTRAINTS)
- Counter-picking: strategy hints injected per goal class
- Heuristic ValueGate (no ML weights needed)
- Escalation ladder (audit #2+ = STRATEGY RESET)
- Robust LEVEL NOTES extraction
"""

import json
import sys
from pathlib import Path


def build_notebook(output_path: str):
    """Build Kaggle notebook for LLM agent v7.0"""
    
    # Read source files
    source_dir = Path(__file__).parent
    goal_classifier = (source_dir / "goal_classifier.py").read_text()
    llm_policy_v7 = (source_dir / "llm_policy_v7_0.py").read_text()
    llm_agent_v7 = (source_dir / "llm_agent_v7.py").read_text()
    grid_utils = (source_dir / "grid_utils.py").read_text()
    
    notebook = {
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "# ARC-AGI-3 LLM Agent v7.0\n",
                    "\n",
                    "**New in v7.0:**\n",
                    "- Goal classifier (8 classes) - detects game type in runtime\n",
                    "- Counter-picking: strategy hints per goal class\n",
                    "- Heuristic ValueGate (no ML, no weights)\n",
                    "- Escalation ladder (audit #2+ = STRATEGY RESET)\n",
                    "- Robust LEVEL NOTES extraction\n",
                    "\n",
                    "**Expected: ~42-50 score** (threshold: 40.97)"
                ]
            },
            {
                "cell_type": "code",
                "metadata": {},
                "source": [
                    "# Install dependencies\n",
                    "!pip install -q openai numpy pillow arcengine\n",
                    "\n",
                    "import os\n",
                    "os.environ['KAGGLE_IS_COMPETITION_RERUN'] = '1'\n",
                    "\n",
                    "# LLM configuration - adjust to available model\n",
                    "os.environ.setdefault('LLM_BASE_URL', 'http://127.0.0.1:1234/v1')\n",
                    "os.environ.setdefault('LLM_MODEL_ID', 'qwen2.5-7b')\n",
                    "os.environ.setdefault('LLM_API_KEY', 'EMPTY')"
                ],
                "execution_count": None,
                "outputs": []
            },
            {
                "cell_type": "code",
                "metadata": {},
                "source": [
                    "# Grid utilities\n",
                    grid_utils
                ],
                "execution_count": None,
                "outputs": []
            },
            {
                "cell_type": "code",
                "metadata": {},
                "source": [
                    "# Goal classifier (8 classes + counter-picking)\n",
                    goal_classifier
                ],
                "execution_count": None,
                "outputs": []
            },
            {
                "cell_type": "code",
                "metadata": {},
                "source": [
                    "# LLM policy v7.0\n",
                    llm_policy_v7
                ],
                "execution_count": None,
                "outputs": []
            },
            {
                "cell_type": "code",
                "metadata": {},
                "source": [
                    "# LLM agent adapter for v7.0\n",
                    llm_agent_v7
                ],
                "execution_count": None,
                "outputs": []
            },
            {
                "cell_type": "code",
                "metadata": {},
                "source": [
                    "# Verify setup\n",
                    "from llm_agent_v7 import LLMAgent\n",
                    "print(f'v7.0 agent loaded: {LLMAgent.name}')"
                ],
                "execution_count": None,
                "outputs": []
            }
        ],
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "name": "python",
                "version": "3.10.0"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 5
    }
    
    with open(output_path, "w") as f:
        json.dump(notebook, f, indent=2)
    
    print(f"Built notebook: {output_path}")
    print(f"  goal_classifier.py: {len(goal_classifier)} chars")
    print(f"  llm_policy_v7_0.py: {len(llm_policy_v7)} chars")
    print(f"  llm_agent_v7.py: {len(llm_agent_v7)} chars")
    print(f"  grid_utils.py: {len(grid_utils)} chars")


if __name__ == "__main__":
    output = sys.argv[1] if len(sys.argv) > 1 else "arc-agi-3-llm-agent-v7.ipynb"
    build_notebook(output)
