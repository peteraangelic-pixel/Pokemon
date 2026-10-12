# r007 · push

UTC 2026-10-12 19:28:51

## Push
```
Kernel version 2 successfully pushed.  Please check progress at https://www.kaggle.com/code/petersharps/arc3-duck
```
VERSION=2
STATUS=COMPLETE after 3514s
SMOKE_MARKER_PRESENT=True
## ARC3 / error lines
```
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
[     6.6s]E Checking patch ARC3-Inference/inference/agent/tool_agent.py...
[     6.6s]E Applied patch ARC3-Inference/inference/agent/tool_agent.py cleanly.
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
[     6.6s]E Checking patch ARC3-Inference/inference/agent/tool_agent.py...
[     6.6s]E Applied patch ARC3-Inference/inference/agent/tool_agent.py cleanly.
[   556.1s]  ARC3 smoke: games=['cn04', 'dc22', 'g50t', 'ka59', 'ls20', 'm0r0', 's5i5', 'sc25', 'su15', 'tn36'] minutes=48
[   556.1s]  benchmark.solver: HarnessSolver(label='duck-harness', runtime_environment=None, job_dir=None, soft_end_time=None, minimal_diagnostics=False, model='local', analyzer_timeout=900.0, max_actions_per_game=None, max_runtime_s_per_game=2880, max_generated_tokens_per_game=None, concurrency=10,
[   556.5s]  ARC3 offline games: ['tn36-ef4dde99', 'm0r0-492f87ba', 'cn04-2fe56bfb', 'dc22-fdcac232', 'ka59-38d34dbb', 'sc25-635fd71a', 's5i5-18d95033', 'ls20-9607627b', 'su15-1944f8ab', 'g50t-5849a774']
[  3448.3s]  ARC3 smoke results:
[  3448.3s]  ARC3 smoke: games=10 gen_tokens=1737833 non_reset_actions=2396 crashed=[]
[  3448.3s]  ARC3_SMOKE_OK
```
## Log (filtered, last 80 lines)
```
[  3437.1s]E analyzer request timed out at action 122; yielding with 0 tool call(s) preserved: HTTPConnectionPool(host='127.0.0.1', port=8001): Read timed out. (read timeout=0.9242628239999249)
[  3437.1s]E analyzer request timed out at action 259; yielding with 0 tool call(s) preserved: HTTPConnectionPool(host='127.0.0.1', port=8001): Read timed out. (read timeout=11.818624000000455)
[  3437.1s]E 
[  3437.1s]E analyzer request timed out at action 259; yielding with 0 tool call(s) preserved: HTTPConnectionPool(host='127.0.0.1', port=8001): Read timed out. (read timeout=11.818624000000455)
[  3437.1s]E analyzer request timed out at action 274; yielding with 0 tool call(s) preserved: HTTPConnectionPool(host='127.0.0.1', port=8001): Read timed out. (read timeout=7.067510880000555)
[  3437.1s]E 
[  3437.1s]E analyzer request timed out at action 274; yielding with 0 tool call(s) preserved: HTTPConnectionPool(host='127.0.0.1', port=8001): Read timed out. (read timeout=7.067510880000555)
[  3437.3s]  [finished] cn04-2fe56bfb state=gave_up level=1/6 score=4.76 actions=121 tokens=178300 per-level=14/29,107/54,0/85,0/300,0/208,0/113 note="tokens=178300"
[  3437.3s]  [finished] m0r0-492f87ba state=gave_up level=5/6 score=71.43 actions=258 tokens=170549 per-level=29/30,51/111,78/203,28/26,55/500,17/237 note="tokens=170549"
[  3437.3s]  [finished] sc25-635fd71a state=gave_up level=5/6 score=66.70 actions=273 tokens=170911 per-level=29/36,5/6,122/32,71/83,46/143,0/50 note="tokens=170911"
[  3437.4s]E analyzer request timed out at action 275; yielding with 0 tool call(s) preserved: HTTPConnectionPool(host='127.0.0.1', port=8001): Read timed out. (read timeout=36.04018865099988)
[  3437.4s]E 
[  3437.4s]E analyzer request timed out at action 275; yielding with 0 tool call(s) preserved: HTTPConnectionPool(host='127.0.0.1', port=8001): Read timed out. (read timeout=36.04018865099988)
[  3437.6s]  [finished] g50t-5849a774 state=gave_up level=3/7 score=21.43 actions=274 tokens=163884 per-level=43/78,32/175,74/179,125/230,0/96,0/54,0/67 note="tokens=173470"
[  3437.8s]E analyzer request timed out at action 268; yielding with 0 tool call(s) preserved: HTTPConnectionPool(host='127.0.0.1', port=8001): Read timed out. (read timeout=41.65754668799946)
[  3437.8s]E 
[  3437.8s]E analyzer request timed out at action 268; yielding with 0 tool call(s) preserved: HTTPConnectionPool(host='127.0.0.1', port=8001): Read timed out. (read timeout=41.65754668799946)
[  3437.9s]E analyzer request timed out at action 431; yielding with 0 tool call(s) preserved: HTTPConnectionPool(host='127.0.0.1', port=8001): Read timed out. (read timeout=19.286426151999876)
[  3437.9s]E 
[  3437.9s]E analyzer request timed out at action 431; yielding with 0 tool call(s) preserved: HTTPConnectionPool(host='127.0.0.1', port=8001): Read timed out. (read timeout=19.286426151999876)
[  3438.0s]E analyzer request timed out at action 122; yielding with 0 tool call(s) preserved: HTTPConnectionPool(host='127.0.0.1', port=8001): Read timed out. (read timeout=56.98209901300015)
[  3438.0s]E 
[  3438.0s]E analyzer request timed out at action 122; yielding with 0 tool call(s) preserved: HTTPConnectionPool(host='127.0.0.1', port=8001): Read timed out. (read timeout=56.98209901300015)
[  3438.0s]  [finished] ka59-38d34dbb state=gave_up level=2/7 score=10.71 actions=267 tokens=180501 per-level=20/28,66/109,181/51,0/51,0/33,0/132,0/326 note="tokens=180501"
[  3438.0s]  [finished] ls20-9607627b state=gave_up level=3/7 score=8.52 actions=430 tokens=167183 per-level=27/22,165/123,162/73,76/84,0/96,0/192,0/186 note="tokens=167183"
[  3438.2s]  [finished] s5i5-18d95033 state=gave_up level=2/8 score=8.33 actions=121 tokens=179038 per-level=22/20,82/89,17/106,0/54,0/162,0/38,0/86,0/83 note="tokens=191326"
[  3438.2s]E analyzer request timed out at action 169; yielding with 0 tool call(s) preserved: HTTPConnectionPool(host='127.0.0.1', port=8001): Read timed out. (read timeout=26.168718190999243)
[  3438.2s]E 
[  3438.2s]E analyzer request timed out at action 169; yielding with 0 tool call(s) preserved: HTTPConnectionPool(host='127.0.0.1', port=8001): Read timed out. (read timeout=26.168718190999243)
[  3438.5s]  [finished] su15-1944f8ab state=gave_up level=3/9 score=12.36 actions=168 tokens=186549 per-level=19/22,29/42,31/26,89/115,0/36,0/31,0/8,0/40,0/41 note="tokens=186549"
[  3438.7s]  [sys] RAM 113.8/176.9 | swap none | proc 1.3 GB, 70 threads, 77 fds | GPU0 93.8/95.6 | disk / 7102.4/8156.9, /kaggle/working 0.7/19.5
[  3444.5s]  [finished] tn36-ef4dde99 state=gave_up level=5/7 score=53.57 actions=200 tokens=170771 per-level=30/32,57/72,14/26,25/40,27/30,47/55,0/62 note="tokens=176029"
[  3444.5s]  [finished] dc22-fdcac232 state=gave_up level=4/6 score=47.62 actions=294 tokens=170147 per-level=44/59,55/102,68/67,87/98,40/324,0/578 note="tokens=174808"
[  3447.5s]  benchmark: regenerated diagnostics in /kaggle/working in 2.64s
[  3447.5s]  benchmark: duck-harness-kaggle
[  3447.5s]  solver:    duck-harness
[  3447.5s]  games:     10
[  3447.5s]  passes:    1
[  3447.5s]  runs:      10 (won: 0)
[  3447.5s]  started:   2026-10-12 19:38:15
[  3447.5s]  ended:     2026-10-12 20:26:22
[  3447.5s]  duration:  48m 7s
[  3447.5s]  mean score:    30.54
[  3447.5s]  median score:  16.89
[  3447.5s]  total actions: 2406
[  3447.5s]  total tokens:  1737833
[  3447.5s]  generated tokens/sec: 601.76 (job wallclock)
[  3447.5s]  total wallclock: 28820.9s
[  3447.5s]  
[  3447.5s]  per-game (mean across passes):
[  3447.5s]    cn04-2fe56bfb: score=4.76, levels=1.0/6, actions=121, tokens=178300
[  3447.5s]    dc22-fdcac232: score=47.62, levels=4.0/6, actions=294, tokens=170147
[  3447.5s]    g50t-5849a774: score=21.43, levels=3.0/7, actions=274, tokens=163884
[  3447.5s]    ka59-38d34dbb: score=10.71, levels=2.0/7, actions=267, tokens=180501
[  3447.5s]    ls20-9607627b: score=8.52, levels=3.0/7, actions=430, tokens=167183
[  3447.5s]    m0r0-492f87ba: score=71.43, levels=5.0/6, actions=258, tokens=170549
[  3447.5s]    s5i5-18d95033: score=8.33, levels=2.0/8, actions=121, tokens=179038
[  3447.5s]    sc25-635fd71a: score=66.70, levels=5.0/6, actions=273, tokens=170911
[  3447.5s]    su15-1944f8ab: score=12.36, levels=3.0/9, actions=168, tokens=186549
[  3447.5s]    tn36-ef4dde99: score=53.57, levels=5.0/7, actions=200, tokens=170771
[  3447.5s]  
[  3447.5s]  diagnostics: /kaggle/working/diagnostics.html
[  3448.2s]E /usr/local/lib/python3.12/dist-packages/IPython/core/display.py:724: UserWarning: Consider using IPython.display.IFrame instead
[  3448.2s]E   warnings.warn("Consider using IPython.display.IFrame instead")
[  3448.2s]E 
[  3448.2s]E /usr/local/lib/python3.12/dist-packages/IPython/core/display.py:724: UserWarning: Consider using IPython.display.IFrame instead
[  3448.2s]E   warnings.warn("Consider using IPython.display.IFrame instead")
[  3448.3s]  ARC3 smoke results:
[  3448.3s]    tn36-ef4dde99            state=gave_up    levels=5/7 actions=200 non_reset=200 gen_tokens=170771 score=53.57
[  3448.3s]    m0r0-492f87ba            state=gave_up    levels=5/6 actions=258 non_reset=258 gen_tokens=170549 score=71.43
[  3448.3s]    cn04-2fe56bfb            state=gave_up    levels=1/6 actions=121 non_reset=120 gen_tokens=178300 score=4.76
[  3448.3s]    dc22-fdcac232            state=gave_up    levels=4/6 actions=294 non_reset=293 gen_tokens=170147 score=47.62
[  3448.3s]    ka59-38d34dbb            state=gave_up    levels=2/7 actions=267 non_reset=266 gen_tokens=180501 score=10.71
[  3448.3s]    sc25-635fd71a            state=gave_up    levels=5/6 actions=273 non_reset=270 gen_tokens=170911 score=66.70
[  3448.3s]    s5i5-18d95033            state=gave_up    levels=2/8 actions=121 non_reset=121 gen_tokens=179038 score=8.33
[  3448.3s]    ls20-9607627b            state=gave_up    levels=3/7 actions=430 non_reset=428 gen_tokens=167183 score=8.52
[  3448.3s]    su15-1944f8ab            state=gave_up    levels=3/9 actions=168 non_reset=166 gen_tokens=186549 score=12.36
[  3448.3s]    g50t-5849a774            state=gave_up    levels=3/7 actions=274 non_reset=274 gen_tokens=163884 score=21.43
[  3448.3s]  ARC3 smoke: games=10 gen_tokens=1737833 non_reset_actions=2396 crashed=[]
[  3448.3s]  ARC3_SMOKE_OK
```
## summary.txt
```
benchmark: duck-harness-kaggle
solver:    duck-harness
games:     10
passes:    1
runs:      10 (won: 0)
started:   2026-10-12 19:38:15
ended:     2026-10-12 20:26:22
duration:  48m 7s
mean score:    30.54
median score:  16.89
total actions: 2406
total tokens:  1737833
generated tokens/sec: 601.76 (job wallclock)
total wallclock: 28820.9s

per-game (mean across passes):
  cn04-2fe56bfb: score=4.76, levels=1.0/6, actions=121, tokens=178300
  dc22-fdcac232: score=47.62, levels=4.0/6, actions=294, tokens=170147
  g50t-5849a774: score=21.43, levels=3.0/7, actions=274, tokens=163884
  ka59-38d34dbb: score=10.71, levels=2.0/7, actions=267, tokens=180501
  ls20-9607627b: score=8.52, levels=3.0/7, actions=430, tokens=167183
  m0r0-492f87ba: score=71.43, levels=5.0/6, actions=258, tokens=170549
  s5i5-18d95033: score=8.33, levels=2.0/8, actions=121, tokens=179038
  sc25-635fd71a: score=66.70, levels=5.0/6, actions=273, tokens=170911
  su15-1944f8ab: score=12.36, levels=3.0/9, actions=168, tokens=186549
  tn36-ef4dde99: score=53.57, levels=5.0/7, actions=200, tokens=170771
```

RESULT=OK
