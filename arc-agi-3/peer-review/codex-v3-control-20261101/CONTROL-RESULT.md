# Świeża kontrola v3 na Kaggle: wynik publicznego testu

Prywatny notebook petersharps/arc3-duck-codex-v3-control-1031,wersja1,zakończony COMPLETE. Kolektor Actions41240651612 zakończył się sukcesem i pobrał benchmark,10 logów promptów,serve.log oraz log notebooka. **To publiczny save-run,nie punktowana submisja ani prognoza59+.**

Kod dokładnie odzyskanej v3,SHA8d0195f92c5518a41d14edbfca596b72c27690f269f681bbaa9af0bc3d257bcc; zmienione wyłącznie metadane nowego prywatnego notebooka. Flash-Next W4A16+drafter,10 publicznych gier,48min/gra,concurrency10,1pass. Notebook loguje ARC3_SMOKE_OK i crashed=[].

## Wynik

| Metryka | Świeża v3 | Historyczny smoke v13.7 r121 |
|---|---:|---:|
| Średni wynik publiczny |27.49667|22.58848|
| Ukończone poziomy |33|25|
| Akcje ogółem |1877|2275|
| Akcje ukończonych poziomów |1577|1260|
| Akcje na nieukończonych |300|1015|
| Udział nieukończonych |15.98%|44.62%|

To porównanie historycznych przebiegów,nie losowane sparowane A/B jednej zmiany. Nie przypisujemy różnicy4.90819 punktu pojedynczemu patchowi. Historyczna v3 z wynikiem konkursowym26.25 pozostaje oddzielnym pomiarem.

| Gra | Ukończenia v3 | Ukończenia r121 |
|---|---:|---:|
| tn36 |3|0|
| m0r0 |2|5|
| cn04 |4|1|
| dc22 |3|2|
| ka59 |3|3|
| sc25 |5|5|
| s5i5 |5|4|
| ls20 |3|2|
| su15 |3|3|
| g50t |2|0|

Nie ma przewagi na każdej grze: m0r0 wyraźnie słabsze. Kontrola jest jednak użyteczna: prawdziwa pętla docelowego modelu kończy poziomy. Wcześniejszy lokalny Qwen z zerowymi ukończeniami nie stanowił równoważnego testu jakości.

Log notebooka:1,703,530 wygenerowanych tokenów,1872 non_reset_actions,589.25 tokens/s w końcowym pomiarze całego jobu.1877 akcji w benchmarku obejmuje także RESET-y. final_generated_tokens=0 w eksporcie nadal nie oznacza zerowego inference. Timeouty występują przy końcowym wyczerpaniu czasu; sam napis Read timed out nie dowodzi awarii całego przebiegu. Wszystkie10 gier mają stan gave_up po około2880–2891s,bez crashy.

## Dane i odtworzenie

Raw: analysis/v3-target-result-20261031/v3-output/benchmark.json,prompts/*.log,serve.log,arc3-duck-codex-v3-control-1031.log. summary.json przeliczone narzędziem analyze_v137_smoke.summarize. W tym katalogu jest również odczytany status COMPLETE,historia stanów kolektora i log pobierania.

Źródła: https://www.kaggle.com/code/petersharps/arc3-duck-codex-v3-control-1031 oraz https://github.com/peteraangelic-pixel/Smak-Domu-Konkurs/actions/runs/41240651612 .

Wniosek operacyjny: zachować tę kontrolę do eksperymentów z pamięcią i eliminowaniem utknięcia; porównywać ukończenia per gra przy tych samych ustawieniach. Nie przedstawiać tej próby jako ulepszonej v3 ani wyniku nowego guarded-gated. Żadnej nowej submisji konkursowej nie wykonano w tym teście.
