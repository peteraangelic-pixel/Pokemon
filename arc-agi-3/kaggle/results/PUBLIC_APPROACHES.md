# Czego używa czołówka — skan publicznych notebooków

> Celowo **nie kopiujemy ich kodu**. Wyciągamy tylko: jaki model,
> jaki silnik wnioskowania, jakie techniki. Resztę piszemy sami.

## `arc-prize-2026-sovereign-agent.ipynb`

- komórek: 23, rozmiar: 595,567 B
- **modele**: qwen, llama, nemotron
- **silniki**: vllm, transformers, torch, llama.cpp
- **techniki**: bfs, beam, replay, cache, precompute, precompute, offline, memory, summary, summarize, context, truncate, prune, cot, reflection, json, structured, retry, segmentation, connected, component, object, diff, delta

Opis autora (fragment):

> # About this notebook This notebook contains my solution for **ARC Prize 2026 — ARC-AGI-3, Milestone 2**, built on [Tufa Labs’ Duck harness](https://www.kaggle.com/code/jeroencottaar/tufa-labs-duck-harness-june-30-milestone-winner). Full credit goes to Jeroen Cottaar and Tufa Labs for the original Duck solver, harness, and notebook. The attached source bundle is an unchanged copy of Tufa Labs’ original bundle. **All my modifications to the harness are included in the patch at the beginning of this notebook**, which is applied automatically during setup. The patch is based on the original [Duck harness](https://github.com/Tufalabs/duck-harness) at commit `7652836`. I also switched to [Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next), using [Intel’s AutoRound quantization](https://huggingface.co/Intel/Qwen3.8-Flash-Next-W4A16-AutoRound) and a separate quantized [MTP draf

## `tufa-duck-baseline-arc3.ipynb`

- komórek: 21, rozmiar: 35,085 B
- **modele**: qwen
- **silniki**: vllm, torch
- **techniki**: cache, offline, context, cot, json, segmentation, object, delta
- importy: IPython, arc_agi, datetime, hashlib, html, inference, json, os, pandas, pathlib, pickle, subprocess, sys, sysconfig, taaf, tarfile, time, urllib

Opis autora (fragment):

> # Tufa Duck Baseline ARC3 Reproducible Kaggle notebook for Tufa Labs' The Duck ARC-AGI-3 harness. The solver implementation is mounted from the pinned, public TAAF source bundle; its framework and agent architecture are preserved. For ordinary notebook runs, the offline smoke path plays one bundled game and writes a non-scoring placeholder output. A real competition rerun uses Kaggle's live Arcade gateway and evaluates every game. ARC-AGI-3 is a code competition: Kaggle records the actions and produces the scored run output; there is no user-authored `submission.csv` schema. ## Source, model, and API settings - Upstream: [Tufalabs/duck-harness](https://github.com/Tufalabs/duck-harness), with TAAF source supplied by the attached source-share dataset because competition reruns have internet disabled. - Model: `vrfai/Qwen3.6-27B-FP8`, loaded from the attached model snapshot. - Inference end

## `arc-agi-3-v21-taaf-27b.ipynb`

- komórek: 17, rozmiar: 25,375 B
- **modele**: qwen
- **silniki**: vllm, torch
- **techniki**: cache, offline, cot, json, object, delta
- importy: IPython, arc_agi, datetime, html, json, os, pandas, pathlib, pickle, subprocess, sys, sysconfig, taaf, time, urllib

Opis autora (fragment):

> # Tufa Labs ARC3 submission ![Tufa Labs](attachment:tufa_labs.png) **Note**: this notebook is a more readable version of the notebook that scored our milestone-winning 1.21; unfortunately, we haven't had the same lucky result with this one. The original one is also shared here, but using it is not recommended: https://www.kaggle.com/code/jeroencottaar/taaf-duck-harness-kaggle **Note**: if you make a copy of this notebook, you will have to manually select the proper GPU (RTX Pro 6000). Link to writeup explaining what's going on here: https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/discussion/717133 Link to Machine Learning Street Talk interview by Tim Scarfe about this duck harness: https://x.com/MLStreetTalk/status/2072326433922297975?s=20 This notebook executes the ARC-AGI-3 solver written by the Tufa Labs team; in alphabetical order: Harold Bessis, Jeroen Cottaar, Isaiah P

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

## `arc3-m2-solution.ipynb`

- komórek: 23, rozmiar: 569,175 B
- **modele**: qwen, llama, nemotron
- **silniki**: vllm, transformers, torch, llama.cpp
- **techniki**: bfs, beam, replay, cache, precompute, precompute, offline, memory, summary, summarize, context, truncate, prune, cot, reflection, json, structured, retry, segmentation, connected, component, object, diff, delta

Opis autora (fragment):

> ### About this notebook **Update (v3):** This version reruns the open-sourced submission (v1) with **4 passes on all 25 demo games**, using a runtime budget scaled to match the time available per game in the competition. I couldn’t complete this run before publishing, as I had run out of Kaggle compute. The notebook is otherwise identical. **For details on the solution, see my [write-up](https://www.kaggle.com/writeups/dfranzen/arc-agi-3-milestone-2).** This notebook contains my solution for **ARC Prize 2026 — ARC-AGI-3, Milestone 2**, built on [Tufa Labs’ Duck harness](https://www.kaggle.com/code/jeroencottaar/tufa-labs-duck-harness-june-30-milestone-winner). Full credit goes to Jeroen Cottaar and Tufa Labs for the original Duck solver, harness, and notebook. The attached source bundle is an unchanged copy of Tufa Labs’ original bundle. **All my modifications to the harness are included

## `continual-training-seed102-reverse.ipynb`

- komórek: 4, rozmiar: 2,509 B
- **modele**: qwen
- **techniki**: offline, memory

## `arcmx.ipynb`

- komórek: 4, rozmiar: 97,238 B
- **modele**: qwen
- **silniki**: transformers, torch
- **techniki**: cache, offline, memory, summary, json, diff
- importy: agents, arcengine, collections, gc, json, logging, math, numpy, os, pandas, pathlib, pydantic, re, shutil, signal, site, subprocess, sys, time, torch, transformers, typing, zipfile

## `arc-agi-3-how-noisy-is-one-run.ipynb`

- komórek: 10, rozmiar: 3,400 B
- **modele**: qwen
- **techniki**: diff
- importy: glob, math, numpy, pandas

Opis autora (fragment):

> # ARC-AGI-3: how noisy is one run? This notebook uses the per-run results of the public **Duck** harness baseline (Tufa Labs, [github.com/Tufalabs/duck-harness](https://github.com/Tufalabs/duck-harness); Qwen3.6-27B FP8, 20 runs on each of the 25 public games) to answer three practical questions: 1. How much does the score of the *same* agent vary from run to run? 2. Which public games actually carry signal? 3. How many runs do you need before a score change can be told apart from noise? All credit for the runs goes to Tufa Labs. Data: the attached dataset. ## 1. Run-to-run variation per game The same code on the same game can score anywhere from 0 to several points. Averages over one run per game hide this. ## 2. Which games carry signal? A game where every run scores 0 tells you nothing about a change to your agent. Below: games where at least half the runs score above zero. ## 3. How 

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

- komórek: 23, rozmiar: 594,610 B
- **modele**: qwen, llama, nemotron
- **silniki**: vllm, transformers, torch, llama.cpp
- **techniki**: bfs, beam, replay, cache, precompute, precompute, offline, memory, summary, summarize, context, truncate, prune, cot, reflection, json, structured, retry, segmentation, connected, component, object, diff, delta

Opis autora (fragment):

> # ARC-AGI-3 Milestone 2: Apex Sovereign Agent (D-Prime SOTA Architecture) ### Targeting 1st Rank on ARC Prize 2026 Leaderboard - **Engine**: Qwen3.8-Flash-Next W4A16 AutoRound + Albucino MTP Draft Model (Pennyroyal SGLang v2.5.3) - **Hardware**: Nvidia RTX Pro 6000 (Blackwell SM120, 96GB VRAM) - **Scheduler**: Champion D-Prime Form Priority ($A \cdot M \cdot C + B \cdot \phi$) with dynamic pace tracking - **Resilience**: Hyper-Resilient retry session (180s read timeout, zero timeout yield) - **Action Guards**: Board dump suppression, noop repeat guard, death loop lookahead, auto frame diff - **Submission Contract**: Pre-materialized submission contract preventing zero-byte evaluation errors ## 0. Harness patch Patch to add our modifications to the original tufa harness. ## 1. Environment and submission mode Detect whether this is a real competition rerun (which minimises diagnostics), se

