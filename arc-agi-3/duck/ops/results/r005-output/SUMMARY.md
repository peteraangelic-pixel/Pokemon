# r005 · output

UTC 2026-10-12 18:28:04

## petersharps/arc3-duck
## summary.txt
```
benchmark: duck-harness-kaggle
solver:    duck-harness
games:     2
passes:    1
runs:      2 (won: 0)
started:   2026-10-12 14:39:44
ended:     2026-10-12 14:47:44
duration:  8m 0s
mean score:    24.84
median score:  24.84
total actions: 115
total tokens:  97946
generated tokens/sec: 203.93 (job wallclock)
total wallclock: 960.2s

per-game (mean across passes):
  ft09-0d8bbf25: score=47.62, levels=4.0/6, actions=73, tokens=53893
  ls20-9607627b: score=2.06, levels=1.0/7, actions=42, tokens=44053
```
benchmark.json: 32271 bytes, table in out_petersharps__arc3-duck/table.txt
log lines: 235 SMOKE_MARKER_PRESENT=True
## ARC3 lines
```
[     6.6s]E Applied patch ARC3-Inference/inference/utils/retained_functions.py cleanly.
[     6.6s]E Applied patch ARC3-Inference/inference/utils/segmentation.py cleanly.
[     6.6s]E Checking patch ARC3-Inference/inference/agent/action_names.py...
[     6.6s]E Checking patch ARC3-Inference/inference/agent/noop_repeat_guard.py...
[     6.6s]E Checking patch ARC3-Inference/inference/agent/priority_pace_reference.json...
[     6.6s]E Checking patch ARC3-Inference/inference/agent/priority_scheduler.py...
[     6.6s]E Checking patch ARC3-Inference/inference/agent/prompts.py...
[     6.6s]E Checking patch ARC3-Inference/inference/agent/python_tool_sandbox.py...
[     6.6s]E Checking patch ARC3-Inference/inference/agent/runtime_state.py...
[     6.6s]E Checking patch ARC3-Inference/inference/agent/tool_agent.py...
[     6.6s]E Checking patch ARC3-Inference/inference/agent/vision_context.py...
[     6.6s]E Checking patch ARC3-Inference/inference/framework/run.py...
[     6.6s]E Checking patch ARC3-Inference/inference/framework/solver.py...
[     6.6s]E Checking patch ARC3-Inference/inference/utils/animation.py...
[     6.6s]E Checking patch ARC3-Inference/inference/utils/frame_diff.py...
[     6.6s]E Checking patch ARC3-Inference/inference/utils/openai_compat.py...
[     6.6s]E Checking patch ARC3-Inference/inference/utils/retained_functions.py...
[     6.6s]E Checking patch ARC3-Inference/inference/utils/segmentation.py...
[     6.6s]E Applied patch ARC3-Inference/inference/agent/action_names.py cleanly.
[     6.6s]E Applied patch ARC3-Inference/inference/agent/noop_repeat_guard.py cleanly.
[     6.6s]E Applied patch ARC3-Inference/inference/agent/priority_pace_reference.json cleanly.
[     6.6s]E Applied patch ARC3-Inference/inference/agent/priority_scheduler.py cleanly.
[     6.6s]E Applied patch ARC3-Inference/inference/agent/prompts.py cleanly.
[     6.6s]E Applied patch ARC3-Inference/inference/agent/python_tool_sandbox.py cleanly.
[     6.6s]E Applied patch ARC3-Inference/inference/agent/runtime_state.py cleanly.
[     6.6s]E Applied patch ARC3-Inference/inference/agent/tool_agent.py cleanly.
[     6.6s]E Applied patch ARC3-Inference/inference/agent/vision_context.py cleanly.
[     6.6s]E Applied patch ARC3-Inference/inference/framework/run.py cleanly.
[     6.6s]E Applied patch ARC3-Inference/inference/framework/solver.py cleanly.
[     6.6s]E Applied patch ARC3-Inference/inference/utils/animation.py cleanly.
[     6.6s]E Applied patch ARC3-Inference/inference/utils/frame_diff.py cleanly.
[     6.6s]E Applied patch ARC3-Inference/inference/utils/openai_compat.py cleanly.
[     6.6s]E Applied patch ARC3-Inference/inference/utils/retained_functions.py cleanly.
[     6.6s]E Applied patch ARC3-Inference/inference/utils/segmentation.py cleanly.
[   613.0s]  ARC3 smoke: games=['ft09', 'ls20'] minutes=8
[   613.0s]  benchmark.solver: HarnessSolver(label='duck-harness', runtime_environment=None, job_dir=None, soft_end_time=None, minimal_diagnostics=False, model='local', analyzer_timeout=900.0, max_actions_per_game=None, max_runtime_s_per_game=480, max_generated_tokens_per_game=None, concurrency=2, s
[   613.4s]  ARC3 offline games: ['ls20-9607627b', 'ft09-0d8bbf25']
[  1095.9s]  ARC3 smoke results:
[  1095.9s]  ARC3 smoke: games=2 gen_tokens=97946 non_reset_actions=114 crashed=[]
[  1095.9s]  ARC3_SMOKE_OK
```
## dfranzen/arc-agi-3-milestone-2-solution
## summary.txt
```
benchmark: duck-harness-kaggle
solver:    duck-harness
games:     25
passes:    4
runs:      100 (won: 33)
started:   2026-10-03 14:09:04
ended:     2026-10-03 22:20:01
duration:  8h 10m 56s
mean score:    46.49
median score:  39.02
total actions: 21245
total tokens:  17504777
generated tokens/sec: 594.25 (job wallclock)
total wallclock: 2540924.1s

per-game (mean across passes):
  ar25-0c556536: score=85.42, levels=7.2/8, actions=324, tokens=178129
  bp35-0a0ad940: score=1.18, levels=1.0/9, actions=71, tokens=143382
  cd82-fb555c5d: score=81.20, levels=6.0/6, actions=194, tokens=161404
  cn04-2fe56bfb: score=26.19, levels=2.5/6, actions=141, tokens=186463
  dc22-fdcac232: score=42.51, levels=3.8/6, actions=328, tokens=269557
  ft09-0d8bbf25: score=86.90, levels=5.5/6, actions=111, tokens=83347
  g50t-5849a774: score=9.25, levels=1.8/7, actions=243, tokens=162835
  ka59-38d34dbb: score=18.79, levels=2.8/7, actions=225, tokens=187305
  lf52-271a04aa: score=1.82, levels=1.0/10, actions=85, tokens=96480
  lp85-305b61c3: score=100.00, levels=8.0/8, actions=135, tokens=145002
  ls20-9607627b: score=26.88, levels=4.0/7, actions=426, tokens=270905
  m0r0-492f87ba: score=46.42, levels=3.2/6, actions=213, tokens=182632
  r11l-495a7899: score=82.14, levels=5.2/6, actions=102, tokens=167982
  re86-8af5384d: score=62.91, levels=6.2/8, actions=528, tokens=264362
  s5i5-18d95033: score=23.86, levels=3.2/8, actions=199, tokens=262539
  sb26-7fbdac44: score=93.23, levels=8.0/8, actions=168, tokens=70524
  sc25-635fd71a: score=19.60, levels=2.8/6, actions=283, tokens=144991
  sk48-d8078629: score=0.00, levels=0.0/8, actions=68, tokens=64415
  sp80-589a99af: score=13.10, levels=1.8/6, actions=89, tokens=170548
  su15-1944f8ab: score=27.78, levels=4.2/9, actions=173, tokens=206060
  tn36-ef4dde99: score=53.52, levels=4.2/7, actions=178, tokens=161684
  tr87-cd924810: score=92.31, levels=5.8/6, actions=279, tokens=132601
  tu93-0768757b: score=83.74, levels=8.8/9, actions=283, tokens=338314
  vc33-5430563c: score=80.36, levels=6.0/7, actions=242, tokens=183110
  wa30-ee6fef47: score=3.22, levels=1.2/9, actions=216, tokens=141615
```
benchmark.json: 5318144 bytes, table in out_dfranzen__arc-agi-3-milestone-2-solution/table.txt
log lines: 2625 SMOKE_MARKER_PRESENT=False
## ARC3 lines
```
[     6.9s]E Applied patch ARC3-Inference/inference/framework/run.py cleanly.
[     6.9s]E Applied patch ARC3-Inference/inference/framework/solver.py cleanly.
[     6.9s]E Applied patch ARC3-Inference/inference/utils/animation.py cleanly.
[     6.9s]E Applied patch ARC3-Inference/inference/utils/frame_diff.py cleanly.
[     6.9s]E Applied patch ARC3-Inference/inference/utils/openai_compat.py cleanly.
[     6.9s]E Applied patch ARC3-Inference/inference/utils/retained_functions.py cleanly.
[     6.9s]E Applied patch ARC3-Inference/inference/utils/segmentation.py cleanly.
[     6.9s]E Checking patch ARC3-Inference/inference/agent/action_names.py...
[     6.9s]E Checking patch ARC3-Inference/inference/agent/noop_repeat_guard.py...
[     6.9s]E Checking patch ARC3-Inference/inference/agent/priority_pace_reference.json...
[     6.9s]E Checking patch ARC3-Inference/inference/agent/priority_scheduler.py...
[     6.9s]E Checking patch ARC3-Inference/inference/agent/prompts.py...
[     6.9s]E Checking patch ARC3-Inference/inference/agent/python_tool_sandbox.py...
[     6.9s]E Checking patch ARC3-Inference/inference/agent/runtime_state.py...
[     6.9s]E Checking patch ARC3-Inference/inference/agent/tool_agent.py...
[     6.9s]E Checking patch ARC3-Inference/inference/agent/vision_context.py...
[     6.9s]E Checking patch ARC3-Inference/inference/framework/run.py...
[     6.9s]E Checking patch ARC3-Inference/inference/framework/solver.py...
[     6.9s]E Checking patch ARC3-Inference/inference/utils/animation.py...
[     6.9s]E Checking patch ARC3-Inference/inference/utils/frame_diff.py...
[     6.9s]E Checking patch ARC3-Inference/inference/utils/openai_compat.py...
[     6.9s]E Checking patch ARC3-Inference/inference/utils/retained_functions.py...
[     6.9s]E Checking patch ARC3-Inference/inference/utils/segmentation.py...
[     6.9s]E Applied patch ARC3-Inference/inference/agent/action_names.py cleanly.
[     6.9s]E Applied patch ARC3-Inference/inference/agent/noop_repeat_guard.py cleanly.
[     6.9s]E Applied patch ARC3-Inference/inference/agent/priority_pace_reference.json cleanly.
[     6.9s]E Applied patch ARC3-Inference/inference/agent/priority_scheduler.py cleanly.
[     6.9s]E Applied patch ARC3-Inference/inference/agent/prompts.py cleanly.
[     6.9s]E Applied patch ARC3-Inference/inference/agent/python_tool_sandbox.py cleanly.
[     6.9s]E Applied patch ARC3-Inference/inference/agent/runtime_state.py cleanly.
[     6.9s]E Applied patch ARC3-Inference/inference/agent/tool_agent.py cleanly.
[     6.9s]E Applied patch ARC3-Inference/inference/agent/vision_context.py cleanly.
[     6.9s]E Applied patch ARC3-Inference/inference/framework/run.py cleanly.
[     6.9s]E Applied patch ARC3-Inference/inference/framework/solver.py cleanly.
[     6.9s]E Applied patch ARC3-Inference/inference/utils/animation.py cleanly.
[     6.9s]E Applied patch ARC3-Inference/inference/utils/frame_diff.py cleanly.
[     6.9s]E Applied patch ARC3-Inference/inference/utils/openai_compat.py cleanly.
[     6.9s]E Applied patch ARC3-Inference/inference/utils/retained_functions.py cleanly.
[     6.9s]E Applied patch ARC3-Inference/inference/utils/segmentation.py cleanly.
[   622.1s]  benchmark.solver: HarnessSolver(label='duck-harness', runtime_environment=None, job_dir=None, soft_end_time=None, minimal_diagnostics=False, model='local', analyzer_timeout=900.0, max_actions_per_game=None, max_runtime_s_per_game=29018, max_generated_tokens_per_game=None, concurrency=10
```
## skarin/arc-agi-3-27-80-lb-100-trajectory-audit
no benchmark.json
log lines: 12 SMOKE_MARKER_PRESENT=False
## shiiin9/affectify-arc-31-54-in-a-single-sub
no benchmark.json
log lines: 6 SMOKE_MARKER_PRESENT=False

RESULT=OK
