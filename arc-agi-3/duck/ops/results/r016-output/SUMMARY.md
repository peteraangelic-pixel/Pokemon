# r016 · output

UTC 2026-10-13 10:26:47

## petersharps/arc3-duck
no benchmark.json
log lines: 444 SMOKE_MARKER_PRESENT=True
## ARC3 lines
```
[     6.4s]E Checking patch ARC3-Inference/inference/agent/vision_context.py...
[     6.4s]E Checking patch ARC3-Inference/inference/framework/run.py...
[     6.4s]E Checking patch ARC3-Inference/inference/framework/solver.py...
[     6.4s]E Checking patch ARC3-Inference/inference/utils/animation.py...
[     6.4s]E Checking patch ARC3-Inference/inference/utils/frame_diff.py...
[     6.4s]E Checking patch ARC3-Inference/inference/utils/openai_compat.py...
[     6.4s]E Checking patch ARC3-Inference/inference/utils/retained_functions.py...
[     6.4s]E Checking patch ARC3-Inference/inference/utils/segmentation.py...
[     6.4s]E Applied patch ARC3-Inference/inference/agent/action_names.py cleanly.
[     6.4s]E Applied patch ARC3-Inference/inference/agent/noop_repeat_guard.py cleanly.
[     6.4s]E Applied patch ARC3-Inference/inference/agent/priority_pace_reference.json cleanly.
[     6.4s]E Applied patch ARC3-Inference/inference/agent/priority_scheduler.py cleanly.
[     6.4s]E Applied patch ARC3-Inference/inference/agent/prompts.py cleanly.
[     6.4s]E Applied patch ARC3-Inference/inference/agent/python_tool_sandbox.py cleanly.
[     6.4s]E Applied patch ARC3-Inference/inference/agent/runtime_state.py cleanly.
[     6.4s]E Applied patch ARC3-Inference/inference/agent/tool_agent.py cleanly.
[     6.4s]E Applied patch ARC3-Inference/inference/agent/vision_context.py cleanly.
[     6.4s]E Applied patch ARC3-Inference/inference/framework/run.py cleanly.
[     6.4s]E Applied patch ARC3-Inference/inference/framework/solver.py cleanly.
[     6.4s]E Applied patch ARC3-Inference/inference/utils/animation.py cleanly.
[     6.4s]E Applied patch ARC3-Inference/inference/utils/frame_diff.py cleanly.
[     6.4s]E Applied patch ARC3-Inference/inference/utils/openai_compat.py cleanly.
[     6.4s]E Applied patch ARC3-Inference/inference/utils/retained_functions.py cleanly.
[     6.4s]E Applied patch ARC3-Inference/inference/utils/segmentation.py cleanly.
[     6.4s]E Checking patch ARC3-Inference/inference/agent/tool_agent.py...
[     6.4s]E Applied patch ARC3-Inference/inference/agent/tool_agent.py cleanly.
[     6.4s]E Checking patch ARC3-Inference/inference/agent/prompts.py...
[     6.4s]E Checking patch ARC3-Inference/inference/agent/python_tool_sandbox.py...
[     6.4s]E Checking patch ARC3-Inference/inference/agent/tool_agent.py...
[     6.4s]E Checking patch ARC3-Inference/inference/utils/world_model.py...
[     6.4s]E Applied patch ARC3-Inference/inference/agent/prompts.py cleanly.
[     6.4s]E Applied patch ARC3-Inference/inference/agent/python_tool_sandbox.py cleanly.
[     6.4s]E Applied patch ARC3-Inference/inference/agent/tool_agent.py cleanly.
[     6.4s]E Applied patch ARC3-Inference/inference/utils/world_model.py cleanly.
[   576.5s]  ARC3 smoke: games=['cn04', 'dc22', 'g50t', 'ka59', 'ls20', 'm0r0', 's5i5', 'sc25', 'su15', 'tn36'] minutes=48
[   576.5s]  benchmark.solver: HarnessSolver(label='duck-harness', runtime_environment=None, job_dir=None, soft_end_time=None, minimal_diagnostics=False, model='local', analyzer_timeout=900.0, max_actions_per_game=None, max_runtime_s_per_game=2880, max_generated_tokens_per_game=None, concurrency=10,
[   577.0s]  ARC3 offline games: ['tn36-ef4dde99', 'm0r0-492f87ba', 'cn04-2fe56bfb', 'dc22-fdcac232', 'ka59-38d34dbb', 'sc25-635fd71a', 's5i5-18d95033', 'ls20-9607627b', 'su15-1944f8ab', 'g50t-5849a774']
[  3472.2s]  ARC3 smoke results:
[  3472.2s]  ARC3 smoke: games=10 gen_tokens=1801383 non_reset_actions=1632 crashed=[]
[  3472.2s]  ARC3_SMOKE_OK
```

RESULT=OK
