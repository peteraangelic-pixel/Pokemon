# Przegląd repo `peteraangelic-pixel/NASK` (05.11.2026) + co z tego użyłem

Zakres: wszystkie gałęzie repo, stan na 05.11.2026 ~11:20 UTC. Metoda: `gh api` (drzewo,
commity, surowe pliki), zero zgadywania — każdy fakt ma źródło w SHA lub w pliku.

## 1. Gałęzie i jedyny nowy commit

| gałąź | HEAD | data | co to jest |
|---|---|---|---|
| `main` | `e0a562e1` | 03.11 11:08 | „Initial commit" — pusta, niczego nie wnosi |
| `arena/a29ca234-nask` | **`b2cf80a4`** | **04.11 10:57** | **jedyna nowa rzecz od mojego przeglądu z 04.11 (`eb234af8`)** |
| `codex/multi-program-lab-20261103` | `a4fb58df` | 03.11 22:56 | bez zmian od fali 1 (regulaminy + lab) |

`b2cf80a4` = **„dodaj 6 nowych plików z Dysku Google (13-18) + podsumowanie gałęzi"**, czyli
kopie plików Drive do `drive_materials/`: 13-STRATEGIA-5-PROGRAMOW, 14-coordinator-findings,
15-PRZEGLAD-GALEZI, 16-MAPA-ENDPOINTOW, 17-IDEE-ZAROBEK, 18-PLAN-NOCNY. Pliki 14/15/16/17
przeczytałem z Drive w fali 2 — **nowe dla mnie były tylko 13 i 18**.

Wniosek operacyjny: **ta gałąź nie produkuje nowych pomiarów od 04.11 10:57.** Nie ma tu nic,
co zmienia kolejność pracy; są za to dwie rzeczy warte przejęcia i jeden defekt do zgłoszenia.

## 2. Defekt w ich kopii MOJEGO narzędzia (dowód odtwarzalny)

`nask-lab/tools/bundle_scan.py` (5 767 B) na `b2cf80a4` to **kopia mojego `bundle_scan.py`
sprzed korekty #33** — z tą samą sygnaturą docstring („Offline analyzer of public JS bundles
for the NASK bug-bounty morning run (P0-lite)"). Różnica krytyczna:

```python
# ICH wersja (b2cf80a4:nask-lab/tools/bundle_scan.py)
secrets.append({"kind": kind, "entropy": round(shannon(val), 2),
                "preview": val[:4] + "…" + val[-2:] if len(val) > 8 else val})
```

czyli **fragment wartości sekretu (4 pierwsze + 2 ostatnie znaki) jest zapisywany do raportu**,
a raporty są commitowane do publicznego repo. Dla krótszych wartości zapisywana jest **cała
wartość** (`else val`).

Dowód odtworzony przeze mnie 05.11 (syntetyczny, zmyślony klucz — nie prawdziwy):

```
plik: /tmp/demo/fake.js  →  const cfg={api_key:"aK91zQ7mT4vX2pL8nR3w"};
ICH bundle_scan : [{"kind":"generic_assignment","entropy":4.32,"preview":"aK91…3w"}]
MÓJ bundle_scan : [{"kind":"generic_assignment","entropy":4.32,"length":20,"fingerprint":"6e2ae262d780"}]
```

Do tego ich kopia nie ma moich korekt #39 (filtr `is_real_param` → 662 śmieciowe „parametry"
z minifikatora), #44 (`paths`/`hosts`/sekrety w query-stringu) ani #45/#48 (filtr kształtu
wartości i progi entropii).

**Co z tym zrobiłem:** niczego nie „pożyczyłem" z powrotem (ich wersja jest starsza), a fakt
zapisuję tu, żeby (a) nie uruchamiać ich kopii na prawdziwych bundlach i (b) powiedzieć im,
że mają w repo narzędzie publikujące fragmenty znalezionych poświadczeń. To jest to samo
zagadnienie, które u siebie zamknąłem jako **#33** — tylko że u nich nadal jest otwarte.

## 3. `nask-lab/naskhunt/checks.json` — plan, który JUŻ został wykonany

60 pozycji, wszystkie `science.nask.pl GET /api/downloadFile?fileId=<ID>`, ID co 2 w czterech
okolicach (18800–18868, 40330–40358, 12510–12520, 13225–13240), zasady: „GET-only, 2 req/s,
odstęp ID = 2 (brak brute-force sekwencyjnego)". Pole `class: "8.9"`.

**Nie powtarzamy.** Ten sweep został wykonany i zamknięty: `PRZEGLAD-GALEZI-20261104.md`
wiersz „`science.nask.pl/api/downloadFile` = enum ID" → *MARTWE jako enum* — twarda walidacja
(`-1`, `18864abc`, `fileId[]` → 400 `Invalid file id`), 60 ID w 4 przedziałach → same publiczne
zdjęcia z aktualności; potwierdzone moim kanałem w run1 i ponownie w run9 (`sci-J20` = 400,
27 B, `{"error":"Invalid file id"}`).

**Pułapka nazewnicza warta odnotowania:** `class: "8.9"` to **oczekiwane CVSS** (widełki
„Wysoka 7.0–8.9" z §7 regulaminu), a NIE „§8 pkt 9" ani „klasa 9 z §8". Ktoś, kto czyta ten
plik pobieżnie, może uznać 60 pozycji za „60 znalezisk klasy 8.9". Nie są.

## 4. `nask-codex/programs/2026-11.json` — fakty, których nie miałem w rejestrze

Maszynowy zapis 5 programów (zweryfikowany 03.11, `terms_sha256` dla PDF-ów). Użyteczne:

| pole | wartość | dlaczego to zmienia pracę |
|---|---|---|
| `initial_edition_pool_pln` (NASK) | **100 000 zł** | potwierdzenie §7; `remaining_pool_pln: null` = stan puli nie jest publikowany |
| `rolling_awards_explicitly_allowed` | **true** | nagrody przyznawane w trakcie edycji ⇒ **nie czekamy z raportem do 30.11** (to samo co §7 pkt 5) |
| `results_deadline_days_after_edition_end` | 30 | wyniki do ~30.12 |
| `winner_acceptance_deadline_days` | **7** | od ogłoszenia jest 7 dni na potwierdzenie na platformie — termin nieodnawialny |
| `payout_deadline_days_after_results` | 60 | wypłata do ~60 dni od wyników |
| `own_or_test_accounts_only` | true | §6 pkt 1: tylko własne/testowe konta |
| `no_dedicated_test_accounts_notice` (NASK) | **false** + `false_notice_means`: „No statement observed on the program page; test-account availability is unverified" | **NASK NIE napisał, że kont testowych nie ma** ⇒ pytanie L0 pkt 2 (konto HIVE) jest uzasadnione, a nie „wymuszanie wyjątku" |
| `no_dedicated_test_accounts_notice` (CERT Polska) | **true** | w programie CERT jest wprost: brak kont testowych |
| `scope_conflicts` | `ctf.hack.cert.pl` wymienione w Tier 2, ale PDF wyklucza `*.hack.cert.pl`; „Do not test this host until resolved" | potwierdza moją odmowę mieszania programów i decyzję B (wstrzymaną) |

## 5. `drive_materials/07-recon-out-20261103.jsonl` — bazowy stan 12 hostów (03.11)

| host | status | bajty | tech | uwaga |
|---|---|---:|---|---|
| `116sos.pl` | 200 | 103 227 | nextjs, wordpress | 1 formularz |
| `bezpiecznewybory.pl` | **403** | 365 | waf_block | zamknięte (nie testujemy) |
| `bezpiecznymiesiac.pl` | 200 | 96 753 | azure | 3 ciastka |
| `dataannotation.pllum.org.pl` | 200 | **713** | azure, envoy | shell SPA (HIVE) |
| `dns.pl` | **0** | 0 | — | w tamtej chwili brak odpowiedzi transportu |
| `dyzurnet.pl` | 200 | 106 937 | cloudflare | 1 ciastko |
| `nask.pl` | **302** | 0 | — | apex → `www.nask.pl` (= L10, blokada formalna) |
| `oad.nask.pl` | 200 | 75 666 | azure, envoy | — |
| `pllum.org.pl` | 200 | 133 988 | azure | 2 ciastka |
| `science.nask.pl` | 200 | 161 472 | nextjs, wordpress | 1 ciastko |
| `secure.edu.pl` | **0** | 0 | — | brak odpowiedzi (niezmienne od 03.11) |
| `zglos-dezinformacje.nask.pl` | 200 | 43 912 | azure | **1 formularz** |

Użyłem tego jako potwierdzenia, że `secure.edu.pl` i `bezpiecznewybory.pl` są martwe/zablokowane
**od początku edycji**, a nie „zepsuły się dziś" — więc nie wracam do nich i nie marnuję żądań.

## 6. `drive_materials/08-nask-bugbounty-komplet.zip` — duplikat, bez surowca

53 842 B, 25 pozycji: same dokumenty i kod (`recon/src/*.rs`, `REGULAMIN-wyciag.md`,
`PRZEGLAD-REPO-NASK`, szablony zgłoszeń, `recon.yml`). **Nie ma w środku żadnych bundli ani
dowodów pomiarowych** (`recon/evidence-20261103/` 3,9 MB, o którym pisze 18-PLAN-NOCNY, jest
w workspace innej sesji, nie w tym zip-ie). Rozpakowałem listę, nie wgrywałem nic do repo.

## 7. `drive_materials/13-STRATEGIA-5-PROGRAMOW.md` i `18-PLAN-NOCNY` — co przejąłem

* **Kalibracja (potwierdzenie, nie nowość):** koordynator na 26 hostach 5 programów, 208 żądań,
  156 s ⇒ **0 do zgłoszenia, 19 odrzuconych przez §8** (X-Frame-Options/CSP frame-ancestors,
  security.txt). „To nie jest problem z narzędziem, to jest własność konkursu."
* **Stawki 5 programów:** NASK/CERT/Gov.pl/mSzyfr = 600/4 000/9 000/**20 000**; Władysławowo
  = 100/1 000/2 500/4 000 (5× mniej). 26 hostów dokładnych + 2 strefy wildcard
  (`*.cert.pl`, `*.komunikator.narodowy.gov.pl`). Wszystkie programy: ten sam limit 5 req/s.
* **Guard, który przejmuję jako własny (zgadza się z moją korektą #43):** „dane osobowe →
  przerwać natychmiast". U mnie to teraz instrument, nie deklaracja: liczniki PII + wyciszony
  podgląd + `no_preview` na sondach wrażliwych.
* **Guard, który już miałem:** „panel.dns.pl/partner.dns.pl poza zakresem (niepotwierdzone) —
  nie dotykać". Run 9 ujawnił w bundlu dns.pl dodatkowo **`tracker.dns.pl`** — traktuję tak samo:
  §5 wymienia literal `dns.pl` bez `*`, więc żadnego z tych hostów nie odpytuję.
* **Ich kolejność priorytetów:** #1 `hack.cert.pl` (mapa `/api/v1` + payout), #2 HIVE, #3 mSzyfr;
  `mwdb` zamknięty (2.20.0). Rola agenta: „nie zakładam kont, nie eksploatuję, nie wysyłam
  zgłoszeń" — zgodne z moim podziałem ról i z korektą #41.

## 8. Co z tego realnie zmieniło moją pracę dziś

1. **Nie powtórzyłem** sweepu `downloadFile` (checks.json) — zamknięty dwoma kanałami.
2. **Przejąłem fakty o terminach** (7 dni na potwierdzenie, rolling awards) do rejestru —
   to wpływa na moment wysyłki, nie na technikę.
3. **Zgłosiłem defekt ich kopii mojego narzędzia** (§2) z odtwarzalnym dowodem.
4. **Utwierdziłem wykluczenia**: `secure.edu.pl`, `bezpiecznewybory.pl`, `panel.dns.pl`,
   `tracker.dns.pl`, `www.nask.pl`, `info-trace.116sos.pl`.
5. **Surowiec do nowych tropów wziąłem skądinąd**: z mojego własnego `mine-rawpath-004-run7.json`
   (parametr `statisticsUrl`, `domainName`) i z `analysis-run003.json` (buildId science,
   `previewToken` pllum, literały `graph.facebook.com` w bundlu share) — patrz
   `WYNIKI-RUN9-RUN10-20261105.md`.

## 9. Czego w tym repo NIE ma (żeby nikt nie szukał)

Żadnych ciał odpowiedzi, żadnych bundli, żadnych HAR-ów, żadnych nowych pomiarów po
04.11 10:57, żadnego kodu Rust uruchomionego na celach (`nask-lab/nasktriage` i `naskhunt`
mają `checks.json`/testy, ale brak wyników przebiegów). Jedyny wartościowy surowiec pomiarowy
w całym ekosystemie gałęzi to `analysis-run003.json` (1,95 MB, 479 dokumentów) na
`Pokemon@arena/7911f950-pokemon` — i moje raporty `nask/reports/*`.
