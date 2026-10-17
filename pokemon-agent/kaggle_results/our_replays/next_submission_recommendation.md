# Next submission recommendation - DO NOT AUTO-SUBMIT per user 2026-10-17

User: "dopiero jak przetestujesz na nowych przegranych meczach za 3h i okaze sie ze twoja nowa wersja super radzi sobie z tymi przegranymi.. szkoda slotu"

This workflow tests v70 (current best, 0.637 top30 20g, 0.55 pool, 600 rating) vs v74 (board<=3 prize<=4, 0.693 top30 10g / 0.63 20g, 0.6 vs Mengfei wall) vs v75 (final resistant).

It does NOT submit automatically. User must manually trigger submit_best_2am.yml with distinct bundle name after reviewing compare.txt and detailed_analysis.md.

## Current active submissions (as of fetch)
- 57290311 v63_super_fix_a450 (second branch, Kyogre) 773.7 - 2W-0L public
- 57290256 v70g_alakazam 600.0 - only validation, 0 public games yet

## How to decide next submit after 3h:
1. Wait for v70g to have 10+ public games (check episodes_57290256.csv)
2. Check loss_reasons.json for new wipe losses - if still 50%+ wipe, v74 should be better (it has +100 guard vs +500 in v63 Kyogre)
3. Compare compare_v70_v74_v75.txt - if v74 or v75 beats v70 by >0.03 on top30 20g AND beats Mengfei wall, then recommend v74/v75 with distinct name
4. Otherwise keep v70 or switch to Kyogre v63 (which has 773.7) - second branch is currently better because Kyogre meta > Alakazam

## Slots
Only last 2 submissions active. Currently active: v63 (773.7) and v70g (600.0). 4 submissions remaining today per last log. Do not waste slot without thorough test.
