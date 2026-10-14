#!/usr/bin/env python3
"""
Build notebook for ARC-AGI-3 LLM Agent v4

v4 improvements:
- Ultra-short prompt (max 500 tokens)
- Aggressive exploration (more actions, less thinking)
- Automatic new object testing
- Stuck detection and strategy change
"""

import json
import sys
from pathlib import Path

def build_notebook(output_path: str):
    """Build Kaggle notebook for LLM agent v4"""
    
    # Read source files
    source_dir = Path(__file__).parent
    llm_policy = (source_dir / "llm_policy_v4.py").read_text()
    llm_agent = (source_dir / "llm_agent.py").read_text()
    grid_utils = (source_dir / "grid_utils.py").read_text()
    
    notebook = {
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "# ARC-AGI-3 LLM Agent v4\n",
                    "\n",
                    "Ultra-fast agent with aggressive exploration.\n",
                    "\n",
                    "**Key improvements:**\n",
                    "- Ultra-short prompt (max 500 tokens)\n",
                    "- Aggressive exploration (more actions, less thinking)\n",
                    "- Automatic new object testing\n",
                    "- Stuck detection and strategy change"
                ]
            },
            {
                "cell_type": "code",
                "metadata": {},
                "source": [
                    "# Install dependencies\n",
                    "!pip install -q openai numpy pillow\n",
                    "\n",
                    "import os\n",
                    "os.environ['KAGGLE_IS_COMPETITION_RERUN'] = '1'"
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
                    "# LLM policy v4\n",
                    llm_policy
                ],
                "execution_count": None,
                "outputs": []
            },
            {
                "cell_type": "code",
                "metadata": {},
                "source": [
                    "# LLM agent\n",
                    llm_agent
                ],
                "execution_count": None,
                "outputs": []
            },
            {
                "cell_type": "code",
                "metadata": {},
                "source": [
                    "# Run benchmark\n",
                    "import arc_agi\n",
                    "from arc_agi.benchmark import Benchmark\n",
                    "\n",
                    "benchmark = Benchmark()\n",
                    "benchmark.run()"
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
                "codemirror_mode": {
                    "name": "ipython",
                    "version": 3
                },
                "file_extension": ".py",
                "mimetype": "text/x-python",
                "name": "python",
                "nbconvert_exporter": "python",
                "pygments_lexer": "ipython3",
                "version": "3.10.0"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 4
    }
    
    with open(output_path, 'w') as f:
        json.dump(notebook, f, indent=2)
    
    print(f"Notebook v4 written to {output_path}")

if __name__ == "__main__":
    output = sys.argv[1] if len(sys.argv) > 1 else "arc-agi-3-llm-agent-v4.ipynb"
    build_notebook(output)
