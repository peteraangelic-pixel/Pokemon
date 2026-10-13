# ARC-AGI-3 Strategy — rewizja 5 (11 X 2026)

## Co zrobiliśmy: agent z LLM

Poprzednia sesja zbudowała agenta heurystycznego (bez modelu) — wynik ~1-5.
Próg nagród to 40.97. Heurystyka ma sufit — dalsze iteracje nie dadzą przełomu.

**Nowe podejście:** agent z prawdziwym LLM (Qwen3.6-27B-FP8 via vLLM).
Architektura bazuje na Duck harness (MIT, Tufa Labs) — tym samym, którego
używa czołówka (Tufa Labs, Daniel Franzen, NVARC3).

### Co zostało zbudowane

```
arc-agi-3/llm-agent/
├── grid_utils.py     # ASCII, segmentacja, kolory
├── llm_policy.py     # LLM client, prompt, anti-loop, parsowanie akcji
├── llm_agent.py      # adapter do ARC-AGI-3-Agents framework
├── build_notebook.py # generator notebooka Kaggle
└── notebook/         # katalog push na Kaggle
    ├── kernel-metadata.json
    ├── submission.ipynb
    └── .submit.trigger
```

### Jak to działa

1. Notebook startuje vLLM z modelem Qwen3.6-27B-FP8 (27GB FP8)
2. Agent dostaje stan gry jako ASCII + segmentację (obiekty, kolory, kształty)
3. LLM odpowiada JSON-em: `{"action": "UP", "reasoning": "..."}`
4. Action batching: LLM może zaplanować do 15 akcji naraz
5. Anti-loop: detekcja oscylacji, wymuszona eksploracja po 6 powtórzeniach
6. Fallback: jeśli vLLM padnie, wraca do heurystycznego `myagent`

### Parametry

| Parametr | Wartość | Uzasadnienie |
|---|---|---|
| GPU | RTX Pro 6000 (48GB) | 27GB FP8 mieści się z zapasem na kontekst |
| Model | Qwen3.6-27B-FP8 | Ten sam co czołówka, 27B parametrów |
| Kontekst | 32768 tokenów | ~20 tur konwersacji |
| Akcje/game | 400 | Duck baseline używa podobnego |
| Czas/game | 240s | 110 × 4min = 7.3h w ramach 9h |
| Temp | 0.6 | Zbalansowane eksploracja/eksploatacja |

### Jak uruchomić

```bash
# Trigger w GitHub Actions:
touch arc-agi-3/llm-agent/notebook/.submit.trigger
git add arc-agi-3/llm-agent/notebook/.submit.trigger
git commit -m "trigger: LLM agent submission"
git push origin arena/7911f950-pokemon
```

### Ryzyka

1. **GPU**: Jeśli Kaggle da P100 (16GB) zamiast RTX Pro 6000 (48GB), model się nie zmieści.
   Fallback: agent heurystyczny (wynik ~1-5).
2. **Czas**: 2s na wywołanie LLM × 400 akcji = 800s na grę bez batchowania.
   Z batchowaniem ~10x mniej wywołań, ale to wciąż ryzykowne.
3. **Jakość**: LLM bez fine-tuningu na ARC może nie rozumieć specyfiki gier.
   Ale to i tak o rzędy wielkości lepsze niż heurystyka.

### Następne kroki

Jeśli pierwsze zgłoszenie zadziała (notebook się uruchomi, agent gra):
1. Analizować transcripty — gdzie LLM popełnia błędy
2. Dodać episodic memory między poziomami
3. Testować z obrazami (multimodal mode)
4. Optymalizować prompt na podstawie realnych gier
5. Rozważyć mniejsze modele (W4A16) jeśli GPU nie wystarczy

### Uczciwa ocena szans

- **Pesymistyczny**: notebook się nie uruchomi (vLLM problem), wynik = fallback ~1-5
- **Realistyczny**: agent gra, rozumie proste gry, wynik 5-15
- **Optymistyczny**: LLM dobrze radzi sobie z większością gier, wynik 15-30
- **Próg nagród**: 40.97 — mało prawdopodobny w pierwszym podejściu, ale
  to jest punkt startu do iteracji, nie wynik końcowy

Kluczowe: **dostajemy twardy punkt odniesienia** z prawdziwym modelem.
Bez tego nie wiemy, ile brakuje.
