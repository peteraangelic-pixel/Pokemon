# Benchmark v2.x z `arena/c87f7a48-pokemon` — co przenosić, co nie

**Data:** 21.10.2026
**Źródło:** gałąź `arena/c87f7a48-pokemon`, `pokemon-agent/tools/benchmark_v2.py` (v2 → v2.4)
**Pytanie:** czy nasz benchmark (ARC-AGI-3, `local/`) potrzebuje tych ulepszeń?

## Krótka odpowiedź

**Faz pomiarowych — nie.** Wszystkie sześć mierzy rzeczy, których w ARC-AGI-3 nie ma
(przeciwnik, talie, liga, silnik C++).
**Dyscypliny pomiarowej — tak, i to pilnie.** Trzy z jej reguł uderzają dokładnie
w słabość naszego benchmarku, a pomiar pokazał, że stary benchmark nie umiał
odpowiedzieć na pytanie, do którego go używaliśmy.

## Co jest na tej gałęzi

| Faza | Co mierzy | Dlaczego u nas nie zadziała |
|---|---|---|
| 1 / 1b | FFI vs Rust gauntlet (gier/s) | nie mamy silnika C++ do zbindowania |
| 2 | liga round-robin 4 pilotów × 100 gier | brak przeciwników i talii |
| 3 | belief / Judge (modelowanie talii wroga) | brak przeciwnika |
| 4 | inference transformera (L4/L8, pointer) | mamy szkic, ale brak danych treningowych |
| 5 | PPO: throughput generowania gier | brak pętli self-play |
| 6 | ablacja „lethal" (seat swap, n≥600) | brak dwóch miejsc/przeciwnika |

Wniosek: **żadnej z tych faz nie przenosimy.** To benchmark domenowy.

## Co przenosimy — i czego nam brakowało

Historia tej gałęzi to seria audytów (v2 → v2.1 → v2.2 → v2.3 → v2.4), w których
kolejno wypadały: hardcodowane liczby, fałszywe warstwy transformera, źle
oznaczone etykiety („71.3 gier/s" liczone bez kroku uczenia), ablacja, która
porównywała dwóch różnych agentów zamiast jednego z flagą on/off.

Pięć reguł, które z tego wynikają:

1. **Kontrola = ten sam agent, dwa pomiary.** U nich v67 vs v67 dawało ±10–15 pp
   szumu. To nie była strata czasu — to była jedyna liczba, która pozwalała
   odróżnić efekt od szumu.
2. **Wymiana miejsc (seat swap).** W grze dwuosobowej niweluje przewagę pierwszego
   gracza. W grze jednoosobowej odpowiednikiem są **wspólne seedy** (common random
   numbers).
3. **n≥600.** Mała próba + binarny wynik = szum większy niż efekt.
4. **Prawdziwa ablacja.** Ta sama ścieżka kodu, jedna flaga on/off — nie „nowy
   agent vs stary agent".
5. **Etykietuj to, co zmierzyłeś.** „Generowanie gier" ≠ „trening". Ekstrapolacja
   ≠ pomiar.

## Co z tego zrobiliśmy: `local/abtest.py`

Zmierzyłem najpierw, czy w ogóle mamy problem — i mieliśmy.

### Pomiar 1: czy silnik jest deterministyczny?

```
sp80  deterministic     m0r0  deterministic     cd82  deterministic
ls20  deterministic     vc33  deterministic     bp35  deterministic
```

Tak, przy tym samym seedzie. To znaczy, że **wspólne seedy są u nas dostępne**
i dają coś mocniejszego niż seat swap: przy deterministycznym silniku różnica
między dwoma wariantami to wyłącznie efekt zmiany, którą testujemy.

### Pomiar 2: szum własny benchmarku (ten sam agent, rozłączne seedy)

| próba | wynik A | wynik B | szum | gry, które się różniły |
|---|---|---|---|---|
| n=60/gra, 25 gier | 0.63 | 0.58 | **0.05** | **8/25** |
| n=20/gra, 6 gier | 0.55 | 0.25 | **0.30** | **5/6** |

Ten sam agent, zero zmian w kodzie. Przy n=20 na 6 grach benchmark ma szum
**większy niż każda zmiana, jaką realnie wprowadzaliśmy**.

### Pomiar 3: prawdziwe A/B (parowane seedy)

Test: `epsilon 0.15 → 0.45`, `temp → 0.5`, 4 gry × 20 seedów = 80 epizodów.

```
total_levels_A  0.5      total_levels_B  0.4      total_delta  -0.1
per_episode_delta_mean  -0.025    sd 0.355
CI95 per episode        [-0.10, +0.05]      significant: false
sign test               4 lepsze / 6 gorsze / 70 remisów,  p=0.53
n potrzebne do wykrycia 0.10  ->  1582 epizody
```

Czyli: zmiana, która „wyglądała" na −0.1 poziomu, jest **nieodróżnialna od zera**,
i żeby rzetelnie zmierzyć efekt rzędu 0.10, potrzebujemy ~1600 epizodów — nie 6.

Na 16 rdzeniach to nadal minuty, nie godziny (`~250–350 ep/s`). Lokalnie po prostu
nas na to stać; wcześniej tego nie robiliśmy nie z braku czasu, a z braku metody.

### Trzy tryby narzędzia

```bash
# 1) jaki jest szum przy mojej próbce? (odpowiednik v67 vs v67)
python local/abtest.py noise --seeds 60 --workers 14

# 2) czy zmiana pomaga? (odpowiednik seat swap = wspólne seedy)
python local/abtest.py ab --seeds 120 --workers 14 \
    --params-a '{}' --params-b '{"epsilon": 0.4}'

# 3) ile próbek potrzebuję? (odpowiednik n>=600)
python local/abtest.py power --delta 0.10 --sd 0.35
```

## Czego nadal nie mamy, a moglibyśmy wziąć

- **Ablacja przez flagę, nie przez osobny plik.** U nich „lethal on/off" na tym
  samym agencie. U nas `llm_policy_v7.py` ma już przełączniki przez `ARC3_*`
  env — brakuje tylko narzędzia, które odpali ten sam kod dwa razy z różnym env
  i porówna parowanie. To naturalne rozszerzenie `abtest.py`.
- **Zachowywanie wersji obok siebie** (`benchmark_v2_v2.py`, `..._v2.1.py` …).
  U nas zastępuje to git, więc nie kopiujemy — ale w wynikach warto zapisywać
  hash commita, żeby raport był odtwarzalny. `abtest.py` tego jeszcze nie robi.

## Rekomendacja

1. **Benchmarku nie przepisywać** — fazy v2.x są domenowe.
2. **Używać `abtest.py` przed każdą decyzją o submisie.** Konkretnie: najpierw
   `noise`, potem `ab`. Jeśli `significant: false` — nie ma czego submitująć.
3. **Nie wierzyć pojedynczemu przebiegowi `gauntlet.py`.** On nadal jest dobry do
   „czy w ogóle coś działa" i do zbierania kandydatów (tak znalazł lp85/vc33),
   ale nie do orzekania „lepiej/gorzej".

To jest realna wartość z tej gałęzi: nie kod, tylko to, że pokazała cenę
benchmarku, który mierzy szum i nazywa go wynikiem.
