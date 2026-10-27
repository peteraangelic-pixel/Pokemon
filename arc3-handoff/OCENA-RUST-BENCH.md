# OCENA: benchmark segmentacji `arc3.exe` (Rust + rayon) — 27.10.2026

> **Ten benchmark NIE jest mój.** Leży na **ich** gałęzi
> `peteraangelic-pixel/Smak-Domu-Konkurs` @ `arena/5ed750ef-smak-domu-konkurs`,
> ścieżka `arc-agi-3/rust/` (`BENCHMARK.md`, `Cargo.toml`, `src/bin/arc3.rs`, `src/grid.rs`,
> `src/lib.rs`, `src/replay.rs`, `src/score.rs`).
>
> Sprawdziłem to dwustronnie, nie na oko:
> * `git ls-tree -r HEAD` na **mojej** gałęzi → **zero** plików `.rs`, zero `Cargo.toml`, zero `.exe`;
> * `grep` po moich 10 dokumentach → **zero** trafień `arc3.exe`, `bench`, `--mode salt`, `frames/s`.
>
> Ścieżka kompilacji w wklejonym logu użytkownika potwierdza autorstwo:
> `...\Smak-Domu-Konkurs-arena-5ed750ef-smak-domu-konkurs\arc-agi-3\rust`.
>
> **Nie mylić z `benchmark_v2.9.1_FINAL_FIX_z_binarkami.zip`** — patrz §6, to inny konkurs.

Pomiary użytkownika na **AMD Ryzen 9 5950X (16 rdzeni / 32 wątki)**, Windows, `release`:

| tryb | klatki | siatka | wątki | wall | throughput | per frame | komponenty śr. |
|---|---|---|---|---|---|---|---|
| `blobs` | 5000 | 64×64 | 32 | 0.889 s | **5624.1 f/s** | **0.178 ms** | 17.6 |
| `salt` | 2000 | 64×64 | 32 | 5.509 s | **363.0 f/s** | **2.755 ms** | 2142.7 |

---

## 1. Arytmetyka: spójna w 6/6 punktów

Przeliczyłem każdą wartość pochodną niezależnie:

| wielkość | `blobs` podane / obliczone | `salt` podane / obliczone |
|---|---|---|
| throughput | 5624.1 / **5624.3** | 363.0 / **363.0** |
| per frame | 0.178 / **0.178** | 2.755 / **2.755** |
| avg components | 17.6 / **17.6** | 2142.7 / **2142.7** |
| `frames × per_frame` vs wall | 0.890 / **0.889** | 5.510 / **5.509** |

Metodologia w `src/bin/arc3.rs::cmd_bench` jest **czysta** i nie zawyża wyniku:
generowanie klatek odbywa się **przed** `Instant::now()`, jest **warmup**
(`let _ = segment_layer(&grids[0]);`), a ziarno jest deterministyczne
(`seed = i + 1`), więc pomiar jest powtarzalny. `par_iter()` równolegli **po klatkach**,
nie wewnątrz klatki — co jest właściwym wyborem przy tak małej siatce.

**Werdykt: liczby są wiarygodne jako pomiar tego, co mierzą.** Problem nie jest w pomiarze,
tylko w tym, **co** on mierzy (§3) i **czy to cokolwiek zmienia** (§5).

---

## 2. Znalazłem błąd w ich `BENCHMARK.md`: zawieranie to **O(n·h·w + n²)**, nie O(n²)

Ich dokument twierdzi: *„Algorytm zawierania jest O(n²) względem liczby komponentów."*
W `src/grid.rs` L304-345 pętla wygląda tak:

```rust
for b in 0..n {                                    // n iteracji
    for cell in reached.iter_mut() { *cell = false; }   // O(h·w)  czyszczenie
    /* obsianie brzegów */                               // O(h + w)
    while let Some((r, c)) = stack.pop() { ... }        // O(h·w)  flood-fill
    for a in 0..n { ... }                               // O(n)
}
```

Czyli **dla każdego komponentu od nowa czyszczona i przeszukiwana jest CAŁA siatka**:

> **Złożoność = O(n · h·w) + O(n²)**, a członem **wiodącym jest `n · h·w`**, nie `n²`.

| tryb | `n` | `n·h·w` | `n²` | co dominuje |
|---|---|---|---|---|
| `blobs` | 17.6 | 72 247 | 311 | **`n·h·w` — 232×** |
| `salt` | 2142.7 | 8 776 524 | 4 591 189 | **`n·h·w` — 2×** |

Dlaczego to ma znaczenie, a nie jest czepianiem się notacji: **`n²` rośnie tylko z liczbą
obiektów, `n·h·w` rośnie też z POWIERZCHNIĄ planszy.** Ich sformułowanie przewiduje, że
powiększenie planszy przy tej samej liczbie obiektów nic nie kosztuje; kod mówi co innego.
Przy ocenie ryzyka ogona (§4) to jest różnica w przewidywaniu, nie w opisie.

Uczciwe zastrzeżenie do mojej własnej analizy: **mam dwa punkty pomiarowe i trzy niewiadome**
(koszt stały, współczynnik przy `n·h·w`, przy `n²`), więc **nie potrafię rozdzielić** tych
dwóch członów samymi tymi danymi. Oba modele przechodzą dokładnie przez oba punkty.
Rozdzieli je dopiero generator, który zmienia `n` **niezależnie od powierzchni** —
`synthetic_blobs` zawsze rysuje dokładnie 18 blobów, więc `--size` zmienia powierzchnię
przy stałym `n`; to wystarczy, ale potrzeba flagi w rodzaju `--count`.

---

## 3. `salt` to test torturowy, nie klatka z gry

Generator `synthetic()` robi `row.push(((state >> 33) % 4) as u8)` — **niezależny, jednostajny
losowy kolor z 4 na każdą komórkę**. Efekt: **2142.7 komponentu na 4096 komórek**, czyli średni
komponent ma **1.9 komórki**. To jest szum solniczka-pieprz, a nie plansza.

Dlatego **363 frames/s nie jest liczbą, którą cokolwiek się planuje.** Liczbą bliską realnej
grze jest `blobs` (17.6 komponentu = „kilka dużych obiektów na tle"), czyli **5624 frames/s**.

⚠️ Niezweryfikowane w ich dokumencie: twierdzenie *„Plansze z dużą liczbą drobnych obiektów
istnieją"* nie ma przy sobie pomiaru. **Nie mam ani dowodu za, ani przeciw** — `arcengine`
nie jest zainstalowany w moim sandboxie (po resecie #8), więc nie zmierzyłem rozkładu
liczby komponentów na **prawdziwych** klatkach 25 gier. To jest jedyna luka empiryczna
w tej ocenie i da się ją zamknąć w kilka minut (§7).

---

## 4. Porównanie z ich własnym `BENCHMARK.md` — jedno trafione, jedno nie

Ich `BENCHMARK.md` podaje pomiary z runnera GitHub Actions (**4 wątki**):

| tryb | GHA (4 w.) | 5950X (32 w.) | lepiej o | efektywność 8× wątków |
|---|---|---|---|---|
| `salt` | 15.9 ms | **2.755 ms** | 5.77× | 72 % |
| `blobs` | 0.326 ms | **0.178 ms** | 1.83× | **23 %** |

⚠️ Te dwie kolumny to **różne procesory**, więc to nie jest czysty pomiar skalowania —
nie wolno z tego wyciągać wniosku o efektywności rayon jako takiej.

**Konkretna rozbieżność z ich własną prognozą:** `BENCHMARK.md` przewiduje dla 5950X
*„realistyczna klatka powinna zejść do **~0.08 ms**"*. Zmierzone **0.178 ms**, czyli
**2.22× gorzej niż obiecano** w tym samym dokumencie. Prognoza była ekstrapolacją
„per-rdzeń × równoległość", nie pomiarem — i to jest dokładnie ten błąd, przed którym
sam ostrzegam w `FAKTY-I-POMIARY.md`: **nie planować na niezmierzonych krzywych.**

Przyczyna jest widoczna w kodzie: przy 17.6 komponentu na klatkę koszt stały (~157 µs,
patrz niżej) dominuje, a równoleglenie **po klatkach** 32 wątkami przy 0.178 ms pracy
oznacza, że narzut dispatchu rayon jest tego samego rzędu co sama praca. Stąd 23 %.

Dekompozycja kosztu z dwóch punktów (model `T = A + B·n`):
**A ≈ 157 µs na klatkę** (stałe: etykietowanie + sąsiedztwo + hashe) i **B ≈ 1.21 µs na
komponent**. Te 157 µs na 4096 komórek = **38 ns/komórkę**, co jest dużo jak na release —
prawdopodobna przyczyna: `comp_cells: Vec<HashSet<(usize, usize)>>` i `cells.contains(&(r,c))`,
czyli hashowanie krotek zamiast płaskiej tablicy `Vec<u8>`/bitmapy. To jest **realny trop
do optymalizacji**, gdyby kiedykolwiek była potrzebna (§5 mówi, że nie jest).

---

## 5. Werdykt: wynik jest OK, ale **nie może zmienić wyniku konkursu**

To jest najważniejszy akapit tego dokumentu.

Jedno wywołanie modelu na **linii szybkiej** kosztuje
`3664.6 tok / 603 tok/s = **6077 ms**` (`FAKTY-I-POMIARY.md`, `EKONOMIA-TOKENOW.md` §1bis).

| | czas | udział w koszcie wywołania modelu | stosunek |
|---|---|---|---|
| segmentacja `blobs` | 0.178 ms | **0.0029 %** | **1 : 34 142** |
| segmentacja `salt` | 2.755 ms | **0.045 %** | 1 : 2 206 |
| **wywołanie modelu** | **6077 ms** | 100 % | — |

Dodatkowo, z oficjalnej metodologii (`docs.arcprize.org/methodology`, potwierdzone w
`OCENA-DEEPSEEK-V9.md` §5): *„Internal operations that do not change the environment
(tool calls, reasoning steps, retries) are NOT counted as actions"* — więc szybkość
segmentacji **nie wpływa na punktację w ogóle**, a na budżet 9 h wpływa w czwartym
rzędzie wielkości.

**Ich własny `BENCHMARK.md` mówi to samo i ma rację** (*„to nie jest wąskie gardło 9 godzin"*).
Zgadzam się z tym wnioskiem i potwierdzam go niezależnym rachunkiem. Ich trzy wskazane
miejsca, gdzie Rust realnie pomaga, oceniam tak:

| ich argument | moja ocena |
|---|---|
| 1. ogon rozkładu (Python 4400 ms → 37 min/grę) | ⚠️ **warunkowo prawdziwe** — prawdziwe TYLKO jeśli realna gra wygeneruje klatkę rzędu 2142 komponentów. To jest **niezmierzone** (§3). Na `blobs`-podobnych klatkach Python kosztuje 39 ms, czyli ~20 s na grę — nie problem |
| 2. analiza offline nagrań (1e6 klatek: 11 h → 1.3 min) | ✅ **trafione i wartościowe** — to jest prawdziwy zysk, bo odblokowuje analizę, której inaczej nie da się wykonać |
| 3. precompute / BFS offline | ✅ **kierunek trafiony**, ale patrz §7: moim blokerem była **pamięć RAM**, nie szybkość segmentacji |

---

## 6. Rozróżnienie, o które pytał użytkownik: to są DWA różne narzędzia

W pytaniu padło „nowsze wersje 2.7, 2.8, 2.9 (`benchmark_v2.9.1_FINAL_FIX_z_binarkami.zip`)".
**To nie jest ten benchmark.** W repo są dwie niezależne rzeczy:

| | **PTCG benchmark** | **ARC segmentacja** |
|---|---|---|
| konkurs | Pokemon TCG Kaggle (zakończony) | **ARC-AGI-3 (bieżący)** |
| plik | `pokemon-agent/tools/benchmark_v2.py` | `arc-agi-3/rust/src/bin/arc3.rs` |
| wersje | **v2.7 → v2.8 → v2.9 → v2.9.1** | brak numeracji wersji |
| zip | `benchmark_v2.9.1_FINAL_FIX_z_binarkami.zip` i 5 innych | **nie istnieje** |
| binarki | `pokemon-agent/rust/bin-win/*.exe` (10 szt.: `gauntlet_rust.exe`, `search_deck_rust.exe`, `policy_rollout.exe`, …) | użytkownik zbudował sam przez `cargo build --release` |
| autorstwo | **moje** (commits `9055b08`, `f579a7f`, `6fdc3a`, `1ffa3f9`, `05f30c6`, `5f7c759`) | **ich gałęzi**, nie moje |
| nagłówek w kodzie | `benchmark_v2.py:3`: „v2.9.1 FINAL FIX — merge a450 v2.7 + c87 v2.8 + fix 582774b + bin-win" | — |

Numery **2.7/2.8/2.9/2.9.1 należą wyłącznie do PTCG**. Binarki z tego zipa to
`gauntlet`/`search_deck`/`policy_rollout` — one **nie mają żadnego zastosowania w ARC**,
bo ARC to inny silnik (`arcengine`), inna metryka (RHAE) i inne gry.

---

## 7. Gdzie moc tego PC **realnie** daje przewagę w ARC — i to nie jest segmentacja

Pytanie użytkownika brzmiało: benchmark na PC, „bo ma większą moc obliczeniową niż Actions
i twój sandbox, żebyśmy mieli większe szanse w ARC". **Teza jest słuszna, ale adres jest zły.**

Mój sandbox: **2 CPU, 3939 MB RAM** (`nproc`, `free -m` — zmierzone).
Mój zmierzony bloker w przeszukiwaniu offline **nie był** szybkością, tylko **pamięcią**:

| gra | RAM na stan | stany | zapotrzebowanie | mój sandbox |
|---|---|---|---|---|
| `re86` | 0.190 MB | 94 405 | **17.9 GB** | 3.9 GB ❌ |
| `sc25` | — | — | 602 MB | 3.9 GB ✅ |

Rozrzut pamięci między grami to **~40×** (`results/sweep4_*.jsonl`). Dlatego `sweep5`
(`sk48`, `tr87`, `tn36`) nie dowiózł nic przez 90 minut i został zabity na żądanie
użytkownika, a ja **przesadziłem z korektą** do `--workers 1` po jednym OOM — zamiast
zaplanować pamięciowo (`EKONOMIA-TOKENOW.md`, ustalenie z 25.10).

> **Wniosek: na tym PC przewagę daje 16 rdzeni i — przede wszystkim — RAM na frontier,
> nie Rust na segmentacji.** Te same `arc3_search.py` / `sweep2.py`, które tu umierały
> na pamięć, na maszynie z 32–64 GB i harmonogramie pamięciowym powinny dojść znacznie
> głębiej. To jest **0 GPU i 0 tokenów LLM**, czyli nie zjada slota ani kwoty GPU (30 h/tydz.).

Co **nie** jest przewagą: szybkość segmentacji (§5, 1 : 34 142) i jakakolwiek optymalizacja
`grid.rs`. Nie warto na to wydawać czasu przed 2 XI.

---

## 8. Trzy rzeczy do zrobienia, w kolejności wartości

1. **Zmierzyć rozkład liczby komponentów na PRAWDZIWYCH klatkach 25 gier** (§3). To rozstrzyga,
   czy ogon z ich argumentu 1 w ogóle istnieje. Kilka minut, `pip install arcengine`, bez GPU.
   Bez tego zarówno ich „37 min na grę", jak i moje „to nierealne" są zgadywaniem.
2. **Uruchomić `sweep2.py` na tym PC z harmonogramem pamięciowym** (§7) — `--workers` zależne
   od `sum_baseline` i zmierzonego MB/stan, a nie sztywne 1. To jest jedyna rzecz z tej listy,
   która może **podnieść wynik**, bo dokłada poziomy.
3. **Poprawić ich `BENCHMARK.md`**: O(n·h·w + n²) zamiast O(n²) (§2) oraz wycofać prognozę
   „~0.08 ms na 5950X", bo pomiar mówi 0.178 ms (§4). To nie zmienia decyzji o slocie,
   ale zostawianie błędnej złożoności w dokumencie, na podstawie którego ktoś będzie
   szacował ogon, to dokładnie ta sama pułapka co `concurrency=120`.

**Nie proponuję** dalszych pomiarów `arc3 bench`. Metodologia jest czysta, liczby spójne,
a mierzona wielkość jest cztery rzędy poniżej wiążącego ograniczenia.
