# ARC-AGI-3 LLM Agent

LLM-based agent for the ARC-AGI-3 Kaggle competition. Uses Qwen3.6-27B-FP8
via vLLM for game reasoning with action batching and anti-loop detection.

## Architecture

Based on the [Duck harness](https://github.com/Tufalabs/duck-harness) (MIT, Tufa Labs):

1. **vLLM server** serves Qwen3.6-27B-FP8 locally on Kaggle GPU
2. **LLM policy** sends game state (ASCII grid + segmentation) to the model
3. **Model** outputs structured JSON actions with reasoning
4. **Action batching** — model can output multiple actions; only re-plans when:
   - batch exhausted
   - level changes
   - loop detected
5. **Anti-loop detection** — oscillation, repeated actions, stale states

## Files

| File | Purpose |
|---|---|
| `grid_utils.py` | ASCII formatting, segmentation, color mapping |
| `llm_policy.py` | LLM client, prompt, anti-loop, action parsing |
| `llm_agent.py` | ARC-AGI-3-Agents framework adapter |
| `build_notebook.py` | Generates the Kaggle notebook |
| `notebook/` | Kaggle push directory |

## Budget

- 400 actions per game
- 240 seconds per game (soft limit)
- 110 games × 4 min = 440 min ≈ 7.3 hours (fits in 9h with margin)
- ~2 seconds per LLM call, action batching up to 15 actions per call

## Datasets

Required Kaggle datasets (attached to notebook):
- `driessmit1/arc3-vllm-h100-wheelhouse-v3` — vLLM + torch wheels
- `driessmit1/vrfai-qwen3-6-27b-fp8-hf-snapshot` — model weights

## Submission

```bash
# Trigger: commit to arc-agi-3/llm-agent/notebook/.submit.trigger
# Or: Run workflow "ARC-AGI-3 LLM agent submit" in GitHub Actions
```

## Fallback

If vLLM fails to start (wrong GPU, OOM, etc.), the notebook falls back to
the heuristic `myagent` from the baseline.
