# Czego używa czołówka — skan publicznych notebooków

> Celowo **nie kopiujemy ich kodu**. Wyciągamy tylko: jaki model,
> jaki silnik wnioskowania, jakie techniki. Resztę piszemy sami.

## `arc-prize-2026-sovereign-agent.ipynb`

- komórek: 23, rozmiar: 584,128 B
- **modele**: qwen, llama, nemotron
- **silniki**: vllm, transformers, torch, llama.cpp
- **techniki**: bfs, beam, replay, cache, precompute, precompute, offline, memory, summary, summarize, context, truncate, prune, cot, reflection, json, structured, retry, segmentation, connected, component, object, diff, delta

Opis autora (fragment):

> # About this notebook This notebook contains my solution for **ARC Prize 2026 — ARC-AGI-3, Milestone 2**, built on [Tufa Labs’ Duck harness](https://www.kaggle.com/code/jeroencottaar/tufa-labs-duck-harness-june-30-milestone-winner). Full credit goes to Jeroen Cottaar and Tufa Labs for the original Duck solver, harness, and notebook. The attached source bundle is an unchanged copy of Tufa Labs’ original bundle. **All my modifications to the harness are included in the patch at the beginning of this notebook**, which is applied automatically during setup. The patch is based on the original [Duck harness](https://github.com/Tufalabs/duck-harness) at commit `7652836`. I also switched to [Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next), using [Intel’s AutoRound quantization](https://huggingface.co/Intel/Qwen3.8-Flash-Next-W4A16-AutoRound) and a separate quantized [MTP draf

## `arc-agi-3-v21-taaf-27b.ipynb`

- komórek: 17, rozmiar: 25,375 B
- **modele**: qwen
- **silniki**: vllm, torch
- **techniki**: cache, offline, cot, json, object, delta
- importy: IPython, arc_agi, datetime, html, json, os, pandas, pathlib, pickle, subprocess, sys, sysconfig, taaf, time, urllib

Opis autora (fragment):

> # Tufa Labs ARC3 submission ![Tufa Labs](attachment:tufa_labs.png) **Note**: this notebook is a more readable version of the notebook that scored our milestone-winning 1.21; unfortunately, we haven't had the same lucky result with this one. The original one is also shared here, but using it is not recommended: https://www.kaggle.com/code/jeroencottaar/taaf-duck-harness-kaggle **Note**: if you make a copy of this notebook, you will have to manually select the proper GPU (RTX Pro 6000). Link to writeup explaining what's going on here: https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/discussion/717133 Link to Machine Learning Street Talk interview by Tim Scarfe about this duck harness: https://x.com/MLStreetTalk/status/2072326433922297975?s=20 This notebook executes the ARC-AGI-3 solver written by the Tufa Labs team; in alphabetical order: Harold Bessis, Jeroen Cottaar, Isaiah P

## `arc3-arena-hero-v2-p37-int3.ipynb`

- komórek: 3, rozmiar: 3,816 B
- **techniki**: json, diff
- importy: hashlib, json, os, pandas, pathlib, subprocess, sys, tarfile, time

Opis autora (fragment):

> # Flash Duck-transfer arena competition candidate Public validation: 110 independent cyclic replicas of the 20 public games, 1800 s of gameplay. Competition rerun: discover the hidden gateway roster, nine hours total including setup and a ten-minute cleanup reserve. One RTX PRO 6000 Blackwell 96 GB; fixed winning model/agent/scheduler settings. Public replicas test scaling and stability, not hidden-game generalization. The gateway records actions and creates the real submission artifact.

## `arc3-arena-hero-v2-runb.ipynb`

- komórek: 3, rozmiar: 3,776 B
- **techniki**: json, diff
- importy: hashlib, json, os, pandas, pathlib, subprocess, sys, tarfile, time

Opis autora (fragment):

> # Flash Duck-transfer arena competition candidate Public validation: 110 independent cyclic replicas of the 20 public games, 1800 s of gameplay. Competition rerun: discover the hidden gateway roster, nine hours total including setup and a ten-minute cleanup reserve. One RTX PRO 6000 Blackwell 96 GB; fixed winning model/agent/scheduler settings. Public replicas test scaling and stability, not hidden-game generalization. The gateway records actions and creates the real submission artifact.

## `try-merging-it-you-might-get-lucky-and-win-gold.ipynb`

- komórek: 23, rozmiar: 568,776 B
- **modele**: qwen, llama, nemotron
- **silniki**: vllm, transformers, torch, llama.cpp
- **techniki**: bfs, beam, replay, cache, precompute, precompute, offline, memory, summary, summarize, context, truncate, prune, cot, reflection, json, structured, retry, segmentation, connected, component, object, diff, delta

Opis autora (fragment):

> # About this notebook This notebook contains my solution for **ARC Prize 2026 — ARC-AGI-3, Milestone 2**, built on [Tufa Labs’ Duck harness](https://www.kaggle.com/code/jeroencottaar/tufa-labs-duck-harness-june-30-milestone-winner). Full credit goes to Jeroen Cottaar and Tufa Labs for the original Duck solver, harness, and notebook. The attached source bundle is an unchanged copy of Tufa Labs’ original bundle. **All my modifications to the harness are included in the patch at the beginning of this notebook**, which is applied automatically during setup. The patch is based on the original [Duck harness](https://github.com/Tufalabs/duck-harness) at commit `7652836`. I also switched to [Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next), using [Intel’s AutoRound quantization](https://huggingface.co/Intel/Qwen3.8-Flash-Next-W4A16-AutoRound) and a separate quantized [MTP draf

## `cage-ael-a1.ipynb`

- komórek: 25, rozmiar: 578,044 B
- **modele**: qwen, llama, nemotron
- **silniki**: vllm, transformers, torch, llama.cpp
- **techniki**: bfs, beam, replay, cache, precompute, precompute, offline, memory, summary, summarize, context, truncate, prune, cot, reflection, json, structured, retry, segmentation, connected, component, object, diff, delta

Opis autora (fragment):

> ### About this notebook **Update (v3):** This version reruns the open-sourced submission (v1) with **4 passes on all 25 demo games**, using a runtime budget scaled to match the time available per game in the competition. I couldn’t complete this run before publishing, as I had run out of Kaggle compute. The notebook is otherwise identical. **For details on the solution, see my [write-up](https://www.kaggle.com/writeups/dfranzen/arc-agi-3-milestone-2).** This notebook contains my solution for **ARC Prize 2026 — ARC-AGI-3, Milestone 2**, built on [Tufa Labs’ Duck harness](https://www.kaggle.com/code/jeroencottaar/tufa-labs-duck-harness-june-30-milestone-winner). Full credit goes to Jeroen Cottaar and Tufa Labs for the original Duck solver, harness, and notebook. The attached source bundle is an unchanged copy of Tufa Labs’ original bundle. **All my modifications to the harness are included

## `arcmx.ipynb`

- komórek: 3, rozmiar: 82,463 B
- **modele**: qwen, llama
- **silniki**: transformers, torch
- **techniki**: offline, memory, context, json
- importy: agents, arcengine, ast, builtins, collections, concurrent, datetime, gc, hashlib, importlib, json, logging, numpy, os, pathlib, pydantic, random, re, resource, site, subprocess, sys, time, torch, traceback, transformers, typing, zipfile

## `b3-4de-hmm.ipynb`

- komórek: 62, rozmiar: 445,341 B
- **silniki**: transformers, torch
- **techniki**: cache, offline, memory, summary, summarize, context, json, backtrack, connected, component, object, diff, delta
- importy: IPython, PIL, atexit, dataclasses, datetime, dinov2, faulthandler, gc, hashlib, importlib, io, json, math, matplotlib, numpy, os, pandas, pathlib, random, re, signal, subprocess, sys, tempfile, threading, time, torch, traceback, typing, warnings

Opis autora (fragment):

> # HMM-Navi / DIVE-HMM — B3.4e Diagnostic: Strong Sequence Baseline Audit B3.4d closed topology/place-node modeling as a main contribution: after fair decoding, no single graph transition control produced robust functional gain over static SALAD. The remaining question is whether the project has been comparing against an overly weak temporal baseline. B3.4e therefore audits **stronger established-style sequence alignment controls** on the exact same frozen 4Seasons pairs and SALAD similarity matrices. This notebook does **not** claim to reproduce an official SeqSLAM or AdaptSeqVPR implementation. Instead it implements transparent, fixed, classical-style controls: - static SALAD; - fixed frame-index HMM controls; - causal SeqSLAM-style multi-slope trajectory scoring; - causal dual-direction flexible-step Viterbi alignment; - offline dual-direction flexible-step Viterbi as a non-causal diag

## `cprs-arc-agi-3-super-agent-v22.ipynb`

- komórek: 23, rozmiar: 582,361 B
- **modele**: qwen, llama, nemotron
- **silniki**: vllm, transformers, torch, llama.cpp
- **techniki**: bfs, beam, replay, cache, precompute, precompute, offline, memory, summary, summarize, context, truncate, prune, reflection, json, structured, retry, segmentation, connected, component, object, diff, delta

Opis autora (fragment):

> ### ARC-AGI-3 Milestone 2: Version 22 Apex SOTA Architecture (Proven 31.93 Base + Stability & Action Efficiency) **Daniel Franzen Baseline + Multi-Tier Cognitive Enhancements** - **Model & Drafter**: Qwen3.8-Flash-Next W4A16 AutoRound + Albucino MTP Draft Model (Pennyroyal SGLang v2.5.3) - **Serving Architecture**: BF16 host offload, 128k context window, hysteresis trimming (58k drain) - **Native Priority Scheduling**: 10 active slots, concurrency 10 (matched to MAXREQ), remaining-level tail lookup, score normalization - **Upgrade 1**: Solved-Level Episodic Memory (Cross-Level Physical Invariant Transfer & Retained Helpers) - **Upgrade 2**: Multi-Tier Anti-Loop Strategy Audit (Turn-12 intervention with explicit UNDO / RESET guidance) - **Upgrade 3**: Death-Loop Avoidance Warning (Multi-reset warning preventing repeated fatal action loops) - **Commit Optimization**: Fast Commit Bypass (<4

## `cprs-arc-agi-3-super-agent-v23-apex.ipynb`

- komórek: 23, rozmiar: 582,400 B
- **modele**: qwen, llama, nemotron
- **silniki**: vllm, transformers, torch, llama.cpp
- **techniki**: bfs, beam, replay, cache, precompute, precompute, offline, memory, summary, summarize, context, truncate, prune, reflection, json, structured, retry, segmentation, connected, component, object, diff, delta

Opis autora (fragment):

> ### ARC-AGI-3 Milestone 2: Version 22 Apex SOTA Architecture (Proven 31.93 Base + Stability & Action Efficiency) **Daniel Franzen Baseline + Multi-Tier Cognitive Enhancements** - **Model & Drafter**: Qwen3.8-Flash-Next W4A16 AutoRound + Albucino MTP Draft Model (Pennyroyal SGLang v2.5.3) - **Serving Architecture**: BF16 host offload, 128k context window, hysteresis trimming (58k drain) - **Native Priority Scheduling**: 10 active slots, concurrency 10 (matched to MAXREQ), remaining-level tail lookup, score normalization - **Upgrade 1**: Solved-Level Episodic Memory (Cross-Level Physical Invariant Transfer & Retained Helpers) - **Upgrade 2**: Multi-Tier Anti-Loop Strategy Audit (Turn-12 intervention with explicit UNDO / RESET guidance) - **Upgrade 3**: Death-Loop Avoidance Warning (Multi-reset warning preventing repeated fatal action loops) - **Commit Optimization**: Fast Commit Bypass (<4

## `arc-agi-3-m2-top-submission.ipynb`

- komórek: 23, rozmiar: 570,520 B
- **modele**: qwen, llama, nemotron
- **silniki**: vllm, transformers, torch, llama.cpp
- **techniki**: bfs, beam, replay, cache, precompute, precompute, offline, memory, summary, summarize, context, truncate, prune, cot, reflection, json, structured, retry, segmentation, connected, component, object, diff, delta

Opis autora (fragment):

> ### About this notebook **Update (v3):** This version reruns the open-sourced submission (v1) with **4 passes on all 25 demo games**, using a runtime budget scaled to match the time available per game in the competition. I couldn’t complete this run before publishing, as I had run out of Kaggle compute. The notebook is otherwise identical. **For details on the solution, see my [write-up](https://www.kaggle.com/writeups/dfranzen/arc-agi-3-milestone-2).** This notebook contains my solution for **ARC Prize 2026 — ARC-AGI-3, Milestone 2**, built on [Tufa Labs’ Duck harness](https://www.kaggle.com/code/jeroencottaar/tufa-labs-duck-harness-june-30-milestone-winner). Full credit goes to Jeroen Cottaar and Tufa Labs for the original Duck solver, harness, and notebook. The attached source bundle is an unchanged copy of Tufa Labs’ original bundle. **All my modifications to the harness are included

## `arc-agi-3-m2-franzen-fork.ipynb`

- komórek: 23, rozmiar: 569,171 B
- **modele**: qwen, llama, nemotron
- **silniki**: vllm, transformers, torch, llama.cpp
- **techniki**: bfs, beam, replay, cache, precompute, precompute, offline, memory, summary, summarize, context, truncate, prune, cot, reflection, json, structured, retry, segmentation, connected, component, object, diff, delta

Opis autora (fragment):

> ### About this notebook **Update (v3):** This version reruns the open-sourced submission (v1) with **4 passes on all 25 demo games**, using a runtime budget scaled to match the time available per game in the competition. I couldn’t complete this run before publishing, as I had run out of Kaggle compute. The notebook is otherwise identical. **For details on the solution, see my [write-up](https://www.kaggle.com/writeups/dfranzen/arc-agi-3-milestone-2).** This notebook contains my solution for **ARC Prize 2026 — ARC-AGI-3, Milestone 2**, built on [Tufa Labs’ Duck harness](https://www.kaggle.com/code/jeroencottaar/tufa-labs-duck-harness-june-30-milestone-winner). Full credit goes to Jeroen Cottaar and Tufa Labs for the original Duck solver, harness, and notebook. The attached source bundle is an unchanged copy of Tufa Labs’ original bundle. **All my modifications to the harness are included

