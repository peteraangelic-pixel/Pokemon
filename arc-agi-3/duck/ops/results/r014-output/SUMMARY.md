# r014 · output

UTC 2026-10-13 09:01:18

## petersharps/arc3-duck
no benchmark.json
log lines: 482 SMOKE_MARKER_PRESENT=True
## ARC3 lines
```
[     7.3s]E Checking patch ARC3-Inference/inference/agent/vision_context.py...
[     7.3s]E Checking patch ARC3-Inference/inference/framework/run.py...
[     7.3s]E Checking patch ARC3-Inference/inference/framework/solver.py...
[     7.3s]E Checking patch ARC3-Inference/inference/utils/animation.py...
[     7.3s]E Checking patch ARC3-Inference/inference/utils/frame_diff.py...
[     7.3s]E Checking patch ARC3-Inference/inference/utils/openai_compat.py...
[     7.3s]E Checking patch ARC3-Inference/inference/utils/retained_functions.py...
[     7.3s]E Checking patch ARC3-Inference/inference/utils/segmentation.py...
[     7.3s]E Applied patch ARC3-Inference/inference/agent/action_names.py cleanly.
[     7.3s]E Applied patch ARC3-Inference/inference/agent/noop_repeat_guard.py cleanly.
[     7.3s]E Applied patch ARC3-Inference/inference/agent/priority_pace_reference.json cleanly.
[     7.3s]E Applied patch ARC3-Inference/inference/agent/priority_scheduler.py cleanly.
[     7.3s]E Applied patch ARC3-Inference/inference/agent/prompts.py cleanly.
[     7.3s]E Applied patch ARC3-Inference/inference/agent/python_tool_sandbox.py cleanly.
[     7.3s]E Applied patch ARC3-Inference/inference/agent/runtime_state.py cleanly.
[     7.3s]E Applied patch ARC3-Inference/inference/agent/tool_agent.py cleanly.
[     7.3s]E Applied patch ARC3-Inference/inference/agent/vision_context.py cleanly.
[     7.3s]E Applied patch ARC3-Inference/inference/framework/run.py cleanly.
[     7.3s]E Applied patch ARC3-Inference/inference/framework/solver.py cleanly.
[     7.3s]E Applied patch ARC3-Inference/inference/utils/animation.py cleanly.
[     7.3s]E Applied patch ARC3-Inference/inference/utils/frame_diff.py cleanly.
[     7.3s]E Applied patch ARC3-Inference/inference/utils/openai_compat.py cleanly.
[     7.3s]E Applied patch ARC3-Inference/inference/utils/retained_functions.py cleanly.
[     7.3s]E Applied patch ARC3-Inference/inference/utils/segmentation.py cleanly.
[     7.3s]E Checking patch ARC3-Inference/inference/agent/tool_agent.py...
[     7.3s]E Applied patch ARC3-Inference/inference/agent/tool_agent.py cleanly.
[     7.3s]E Checking patch ARC3-Inference/inference/agent/prompts.py...
[     7.3s]E Checking patch ARC3-Inference/inference/agent/python_tool_sandbox.py...
[     7.3s]E Checking patch ARC3-Inference/inference/agent/tool_agent.py...
[     7.3s]E Checking patch ARC3-Inference/inference/utils/world_model.py...
[     7.3s]E Applied patch ARC3-Inference/inference/agent/prompts.py cleanly.
[     7.3s]E Applied patch ARC3-Inference/inference/agent/python_tool_sandbox.py cleanly.
[     7.3s]E Applied patch ARC3-Inference/inference/agent/tool_agent.py cleanly.
[     7.3s]E Applied patch ARC3-Inference/inference/utils/world_model.py cleanly.
[   730.8s]  ARC3 smoke: games=['cn04', 'dc22', 'g50t', 'ka59', 'ls20', 'm0r0', 's5i5', 'sc25', 'su15', 'tn36'] minutes=48
[   730.8s]  benchmark.solver: HarnessSolver(label='duck-harness', runtime_environment=None, job_dir=None, soft_end_time=None, minimal_diagnostics=False, model='local', analyzer_timeout=900.0, max_actions_per_game=None, max_runtime_s_per_game=2880, max_generated_tokens_per_game=None, concurrency=10,
[   731.4s]  ARC3 offline games: ['tn36-ef4dde99', 'm0r0-492f87ba', 'cn04-2fe56bfb', 'dc22-fdcac232', 'ka59-38d34dbb', 'sc25-635fd71a', 's5i5-18d95033', 'ls20-9607627b', 'su15-1944f8ab', 'g50t-5849a774']
[  3624.9s]  ARC3 smoke results:
[  3624.9s]  ARC3 smoke: games=10 gen_tokens=1606296 non_reset_actions=2318 crashed=[]
[  3624.9s]  ARC3_SMOKE_OK
```

RESULT=OK
