# r018 · push

UTC 2026-10-13 11:04:33

## Push
```
Kernel version 6 successfully pushed.  Please check progress at https://www.kaggle.com/code/petersharps/arc3-duck
```
VERSION=6
STATUS=COMPLETE after 3516s
SMOKE_MARKER_PRESENT=True
## ARC3 / error lines
```
[     6.3s]E Applied patch ARC3-Inference/inference/utils/retained_functions.py cleanly.
[     6.3s]E Applied patch ARC3-Inference/inference/utils/segmentation.py cleanly.
[     6.3s]E Checking patch ARC3-Inference/inference/agent/tool_agent.py...
[     6.3s]E Applied patch ARC3-Inference/inference/agent/tool_agent.py cleanly.
[     6.3s]E Checking patch ARC3-Inference/inference/agent/prompts.py...
[     6.3s]E Checking patch ARC3-Inference/inference/agent/python_tool_sandbox.py...
[     6.3s]E Checking patch ARC3-Inference/inference/agent/tool_agent.py...
[     6.3s]E Checking patch ARC3-Inference/inference/utils/world_model.py...
[     6.3s]E Applied patch ARC3-Inference/inference/agent/prompts.py cleanly.
[     6.3s]E Applied patch ARC3-Inference/inference/agent/python_tool_sandbox.py cleanly.
[     6.3s]E Applied patch ARC3-Inference/inference/agent/tool_agent.py cleanly.
[     6.3s]E Applied patch ARC3-Inference/inference/utils/world_model.py cleanly.
[     6.3s]E Checking patch ARC3-Inference/inference/agent/action_names.py...
[     6.3s]E Checking patch ARC3-Inference/inference/agent/noop_repeat_guard.py...
[     6.3s]E Checking patch ARC3-Inference/inference/agent/priority_pace_reference.json...
[     6.3s]E Checking patch ARC3-Inference/inference/agent/priority_scheduler.py...
[     6.3s]E Checking patch ARC3-Inference/inference/agent/prompts.py...
[     6.3s]E Checking patch ARC3-Inference/inference/agent/python_tool_sandbox.py...
[     6.3s]E Checking patch ARC3-Inference/inference/agent/runtime_state.py...
[     6.3s]E Checking patch ARC3-Inference/inference/agent/tool_agent.py...
[     6.3s]E Checking patch ARC3-Inference/inference/agent/vision_context.py...
[     6.3s]E Checking patch ARC3-Inference/inference/framework/run.py...
[     6.3s]E Checking patch ARC3-Inference/inference/framework/solver.py...
[     6.3s]E Checking patch ARC3-Inference/inference/utils/animation.py...
[     6.3s]E Checking patch ARC3-Inference/inference/utils/frame_diff.py...
[     6.3s]E Checking patch ARC3-Inference/inference/utils/openai_compat.py...
[     6.3s]E Checking patch ARC3-Inference/inference/utils/retained_functions.py...
[     6.3s]E Checking patch ARC3-Inference/inference/utils/segmentation.py...
[     6.3s]E Applied patch ARC3-Inference/inference/agent/action_names.py cleanly.
[     6.3s]E Applied patch ARC3-Inference/inference/agent/noop_repeat_guard.py cleanly.
[     6.3s]E Applied patch ARC3-Inference/inference/agent/priority_pace_reference.json cleanly.
[     6.3s]E Applied patch ARC3-Inference/inference/agent/priority_scheduler.py cleanly.
[     6.3s]E Applied patch ARC3-Inference/inference/agent/prompts.py cleanly.
[     6.3s]E Applied patch ARC3-Inference/inference/agent/python_tool_sandbox.py cleanly.
[     6.3s]E Applied patch ARC3-Inference/inference/agent/runtime_state.py cleanly.
[     6.3s]E Applied patch ARC3-Inference/inference/agent/tool_agent.py cleanly.
[     6.3s]E Applied patch ARC3-Inference/inference/agent/vision_context.py cleanly.
[     6.3s]E Applied patch ARC3-Inference/inference/framework/run.py cleanly.
[     6.3s]E Applied patch ARC3-Inference/inference/framework/solver.py cleanly.
[     6.3s]E Applied patch ARC3-Inference/inference/utils/animation.py cleanly.
[     6.3s]E Applied patch ARC3-Inference/inference/utils/frame_diff.py cleanly.
[     6.3s]E Applied patch ARC3-Inference/inference/utils/openai_compat.py cleanly.
[     6.3s]E Applied patch ARC3-Inference/inference/utils/retained_functions.py cleanly.
[     6.3s]E Applied patch ARC3-Inference/inference/utils/segmentation.py cleanly.
[     6.3s]E Checking patch ARC3-Inference/inference/agent/tool_agent.py...
[     6.3s]E Applied patch ARC3-Inference/inference/agent/tool_agent.py cleanly.
[     6.3s]E Checking patch ARC3-Inference/inference/agent/prompts.py...
[     6.3s]E Checking patch ARC3-Inference/inference/agent/python_tool_sandbox.py...
[     6.3s]E Checking patch ARC3-Inference/inference/agent/tool_agent.py...
[     6.3s]E Checking patch ARC3-Inference/inference/utils/world_model.py...
[     6.3s]E Applied patch ARC3-Inference/inference/agent/prompts.py cleanly.
[     6.3s]E Applied patch ARC3-Inference/inference/agent/python_tool_sandbox.py cleanly.
[     6.3s]E Applied patch ARC3-Inference/inference/agent/tool_agent.py cleanly.
[     6.3s]E Applied patch ARC3-Inference/inference/utils/world_model.py cleanly.
[   536.4s]  ARC3 smoke: games=['cn04', 'dc22', 'g50t', 'ka59', 'ls20', 'm0r0', 's5i5', 'sc25', 'su15', 'tn36'] minutes=48
[   536.4s]  benchmark.solver: HarnessSolver(label='duck-harness', runtime_environment=None, job_dir=None, soft_end_time=None, minimal_diagnostics=False, model='local', analyzer_timeout=900.0, max_actions_per_game=None, max_runtime_s_per_game=2880, max_generated_tokens_per_game=None, concurrency=10,
[   536.7s]  ARC3 offline games: ['tn36-ef4dde99', 'm0r0-492f87ba', 'cn04-2fe56bfb', 'dc22-fdcac232', 'ka59-38d34dbb', 'sc25-635fd71a', 's5i5-18d95033', 'ls20-9607627b', 'su15-1944f8ab', 'g50t-5849a774']
[  3441.8s]  ARC3 smoke results:
[  3441.8s]  ARC3 smoke: games=10 gen_tokens=1737255 non_reset_actions=2058 crashed=[]
[  3441.8s]  ARC3_SMOKE_OK
```
## Log (filtered, last 80 lines)
```
[  3417.2s]E analyzer request timed out at action 286; yielding with 0 tool call(s) preserved: HTTPConnectionPool(host='127.0.0.1', port=8001): Read timed out. (read timeout=1.9460966569999982)
[  3417.2s]E analyzer request timed out at action 216; yielding with 0 tool call(s) preserved: HTTPConnectionPool(host='127.0.0.1', port=8001): Read timed out. (read timeout=34.74164691599981)
[  3417.2s]E 
[  3417.2s]E analyzer request timed out at action 216; yielding with 0 tool call(s) preserved: HTTPConnectionPool(host='127.0.0.1', port=8001): Read timed out. (read timeout=34.74164691599981)
[  3417.2s]E analyzer request timed out at action 146; yielding with 0 tool call(s) preserved: HTTPConnectionPool(host='127.0.0.1', port=8001): Read timed out. (read timeout=68.94003278400032)
[  3417.2s]E 
[  3417.2s]E analyzer request timed out at action 146; yielding with 0 tool call(s) preserved: HTTPConnectionPool(host='127.0.0.1', port=8001): Read timed out. (read timeout=68.94003278400032)
[  3417.3s]E analyzer request timed out at action 167; yielding with 0 tool call(s) preserved: HTTPConnectionPool(host='127.0.0.1', port=8001): Read timed out. (read timeout=4.805636367000261)
[  3417.3s]E 
[  3417.3s]E analyzer request timed out at action 167; yielding with 0 tool call(s) preserved: HTTPConnectionPool(host='127.0.0.1', port=8001): Read timed out. (read timeout=4.805636367000261)
[  3417.3s]  [finished] g50t-5849a774 state=gave_up level=2/7 score=10.71 actions=168 tokens=168970 per-level=41/78,44/175,83/179,0/230,0/96,0/54,0/67 note="tokens=179111"
[  3417.3s]  [finished] sc25-635fd71a state=gave_up level=4/6 score=42.62 actions=285 tokens=166390 per-level=85/36,10/6,29/32,69/83,92/143,0/50 note="tokens=166390"
[  3417.3s]  [finished] m0r0-492f87ba state=gave_up level=3/6 score=28.57 actions=215 tokens=170262 per-level=32/30,56/111,107/203,20/26,0/500,0/237 note="tokens=170262"
[  3417.3s]  [finished] tn36-ef4dde99 state=gave_up level=1/7 score=3.57 actions=145 tokens=173865 per-level=21/32,124/72,0/26,0/40,0/30,0/55,0/62 note="tokens=173865"
[  3417.3s]  [finished] cn04-2fe56bfb state=gave_up level=4/6 score=47.62 actions=166 tokens=182616 per-level=16/29,62/54,25/85,42/300,21/208,0/113 note="tokens=182616"
[  3417.4s]E analyzer request timed out at action 305; yielding with 0 tool call(s) preserved: HTTPConnectionPool(host='127.0.0.1', port=8001): Read timed out. (read timeout=9.27426248500069)
[  3417.4s]E 
[  3417.4s]E analyzer request timed out at action 305; yielding with 0 tool call(s) preserved: HTTPConnectionPool(host='127.0.0.1', port=8001): Read timed out. (read timeout=9.27426248500069)
[  3417.4s]E analyzer request timed out at action 158; yielding with 0 tool call(s) preserved: HTTPConnectionPool(host='127.0.0.1', port=8001): Read timed out. (read timeout=6.3159157769996455)
[  3417.4s]E 
[  3417.4s]E analyzer request timed out at action 158; yielding with 0 tool call(s) preserved: HTTPConnectionPool(host='127.0.0.1', port=8001): Read timed out. (read timeout=6.3159157769996455)
[  3417.6s]  [finished] dc22-fdcac232 state=gave_up level=4/6 score=44.77 actions=304 tokens=171666 per-level=58/59,61/102,91/67,93/98,1/324,0/578 note="tokens=174725"
[  3417.6s]  [finished] su15-1944f8ab state=gave_up level=7/9 score=56.42 actions=157 tokens=184664 per-level=13/22,19/42,16/26,39/115,21/36,12/31,19/8,18/40,0/41 note="tokens=184664"
[  3418.0s]  [sys] RAM 114.9/176.9 | swap none | proc 1.2 GB, 70 threads, 75 fds | GPU0 93.8/95.6 | disk / 7102.4/8156.9, /kaggle/working 0.7/19.5
[  3421.1s]  [finished] ls20-9607627b state=gave_up level=1/7 score=3.27 actions=250 tokens=165362 per-level=23/22,227/123,0/73,0/84,0/96,0/192,0/186 note="tokens=172194"
[  3423.5s]E analyzer request timed out at action 260; yielding with 1 tool call(s) preserved: HTTPConnectionPool(host='127.0.0.1', port=8001): Read timed out. (read timeout=55.16186547499956)
[  3423.5s]E 
[  3423.5s]E analyzer request timed out at action 260; yielding with 1 tool call(s) preserved: HTTPConnectionPool(host='127.0.0.1', port=8001): Read timed out. (read timeout=55.16186547499956)
[  3423.7s]  [finished] ka59-38d34dbb state=gave_up level=3/7 score=17.85 actions=259 tokens=168852 per-level=19/28,51/109,71/51,118/51,0/33,0/132,0/326 note="tokens=172800"
[  3438.1s]E analyzer request timed out at action 117; yielding with 1 tool call(s) preserved: HTTPConnectionPool(host='127.0.0.1', port=8001): Read timed out. (read timeout=55.10920717800036)
[  3438.1s]E 
[  3438.1s]E analyzer request timed out at action 117; yielding with 1 tool call(s) preserved: HTTPConnectionPool(host='127.0.0.1', port=8001): Read timed out. (read timeout=55.10920717800036)
[  3438.3s]  [finished] s5i5-18d95033 state=gave_up level=3/8 score=16.67 actions=116 tokens=184608 per-level=25/20,32/89,41/106,18/54,0/162,0/38,0/86,0/83 note="tokens=188291"
[  3440.9s]  benchmark: regenerated diagnostics in /kaggle/working in 2.48s
[  3440.9s]  benchmark: duck-harness-kaggle
[  3440.9s]  solver:    duck-harness
[  3440.9s]  games:     10
[  3440.9s]  passes:    1
[  3440.9s]  runs:      10 (won: 0)
[  3440.9s]  started:   2026-10-13 11:13:36
[  3440.9s]  ended:     2026-10-13 12:01:57
[  3440.9s]  duration:  48m 21s
[  3440.9s]  mean score:    27.21
[  3440.9s]  median score:  23.21
[  3440.9s]  total actions: 2065
[  3440.9s]  total tokens:  1737255
[  3440.9s]  generated tokens/sec: 598.76 (job wallclock)
[  3440.9s]  total wallclock: 28834.1s
[  3440.9s]  
[  3440.9s]  per-game (mean across passes):
[  3440.9s]    cn04-2fe56bfb: score=47.62, levels=4.0/6, actions=166, tokens=182616
[  3440.9s]    dc22-fdcac232: score=44.77, levels=4.0/6, actions=304, tokens=171666
[  3440.9s]    g50t-5849a774: score=10.71, levels=2.0/7, actions=168, tokens=168970
[  3440.9s]    ka59-38d34dbb: score=17.85, levels=3.0/7, actions=259, tokens=168852
[  3440.9s]    ls20-9607627b: score=3.27, levels=1.0/7, actions=250, tokens=165362
[  3440.9s]    m0r0-492f87ba: score=28.57, levels=3.0/6, actions=215, tokens=170262
[  3440.9s]    s5i5-18d95033: score=16.67, levels=3.0/8, actions=116, tokens=184608
[  3440.9s]    sc25-635fd71a: score=42.62, levels=4.0/6, actions=285, tokens=166390
[  3440.9s]    su15-1944f8ab: score=56.42, levels=7.0/9, actions=157, tokens=184664
[  3440.9s]    tn36-ef4dde99: score=3.57, levels=1.0/7, actions=145, tokens=173865
[  3440.9s]  
[  3440.9s]  diagnostics: /kaggle/working/diagnostics.html
[  3441.7s]E /usr/local/lib/python3.12/dist-packages/IPython/core/display.py:724: UserWarning: Consider using IPython.display.IFrame instead
[  3441.7s]E   warnings.warn("Consider using IPython.display.IFrame instead")
[  3441.7s]E 
[  3441.7s]E /usr/local/lib/python3.12/dist-packages/IPython/core/display.py:724: UserWarning: Consider using IPython.display.IFrame instead
[  3441.7s]E   warnings.warn("Consider using IPython.display.IFrame instead")
[  3441.8s]  ARC3 smoke results:
[  3441.8s]    tn36-ef4dde99            state=gave_up    levels=1/7 actions=145 non_reset=143 gen_tokens=173865 score=3.57
[  3441.8s]    m0r0-492f87ba            state=gave_up    levels=3/6 actions=215 non_reset=214 gen_tokens=170262 score=28.57
[  3441.8s]    cn04-2fe56bfb            state=gave_up    levels=4/6 actions=166 non_reset=166 gen_tokens=182616 score=47.62
[  3441.8s]    dc22-fdcac232            state=gave_up    levels=4/6 actions=304 non_reset=304 gen_tokens=171666 score=44.77
[  3441.8s]    ka59-38d34dbb            state=gave_up    levels=3/7 actions=259 non_reset=259 gen_tokens=168852 score=17.85
[  3441.8s]    sc25-635fd71a            state=gave_up    levels=4/6 actions=285 non_reset=282 gen_tokens=166390 score=42.62
[  3441.8s]    s5i5-18d95033            state=gave_up    levels=3/8 actions=116 non_reset=116 gen_tokens=184608 score=16.67
[  3441.8s]    ls20-9607627b            state=gave_up    levels=1/7 actions=250 non_reset=249 gen_tokens=165362 score=3.27
[  3441.8s]    su15-1944f8ab            state=gave_up    levels=7/9 actions=157 non_reset=157 gen_tokens=184664 score=56.42
[  3441.8s]    g50t-5849a774            state=gave_up    levels=2/7 actions=168 non_reset=168 gen_tokens=168970 score=10.71
[  3441.8s]  ARC3 smoke: games=10 gen_tokens=1737255 non_reset_actions=2058 crashed=[]
[  3441.8s]  ARC3_SMOKE_OK
```
## summary.txt
```
benchmark: duck-harness-kaggle
solver:    duck-harness
games:     10
passes:    1
runs:      10 (won: 0)
started:   2026-10-13 11:13:36
ended:     2026-10-13 12:01:57
duration:  48m 21s
mean score:    27.21
median score:  23.21
total actions: 2065
total tokens:  1737255
generated tokens/sec: 598.76 (job wallclock)
total wallclock: 28834.1s

per-game (mean across passes):
  cn04-2fe56bfb: score=47.62, levels=4.0/6, actions=166, tokens=182616
  dc22-fdcac232: score=44.77, levels=4.0/6, actions=304, tokens=171666
  g50t-5849a774: score=10.71, levels=2.0/7, actions=168, tokens=168970
  ka59-38d34dbb: score=17.85, levels=3.0/7, actions=259, tokens=168852
  ls20-9607627b: score=3.27, levels=1.0/7, actions=250, tokens=165362
  m0r0-492f87ba: score=28.57, levels=3.0/6, actions=215, tokens=170262
  s5i5-18d95033: score=16.67, levels=3.0/8, actions=116, tokens=184608
  sc25-635fd71a: score=42.62, levels=4.0/6, actions=285, tokens=166390
  su15-1944f8ab: score=56.42, levels=7.0/9, actions=157, tokens=184664
  tn36-ef4dde99: score=3.57, levels=1.0/7, actions=145, tokens=173865
```

RESULT=OK
