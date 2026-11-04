# Kod przejety z innej sesji (vendored) — `a450b00f` @ `bb17ccdc`

**Proweniencja (dokladna):**
* repo: `peteraangelic-pixel/Pokemon`
* galaz: `arena/a450b00f-pokemon`
* commit: `bb17ccdc` — "Fix offline HAR triage tests: ID length and account-level asymmetry" (2026-11-04T10:14:08Z)
* sciezka zrodlowa: `nask/lab/har_triage.py`, `nask/lab/auth_matrix.py`, `nask/lab/tests/test_har_triage.py`, `nask/lab/tests/test_auth_matrix.py`
* pobrane przez GitHub API (`Accept: application/vnd.github.raw`) 2026-11-04, bez modyfikacji poza opisana nizej.

**Po co:** to jest narzedzie do analizy zrzutow HAR z **dwoch wlasnych kont** usera
(krok L1/L4 runbooka). Pracuje wylacznie offline: normalizuje segmenty ID do `{id}`,
grupuje endpointy, wykrywa tokeny w query (`token`, `access_token`, `api_key`, `session`,
`jwt`, ...) i oznacza asymetrie uprawnien miedzy kontami. Zero sieci, zero poswiadczen,
zero werdyktow — kazdy wynik to hipoteza do recznego potwierdzenia.

Zasada przyjeca od autorow (`auth_matrix.py`): **wspolny dostep do wspolnego zasobu
nie jest IDOR-em samym w sobie.**

## Znaleziony defekt (zgloszony w `PRZEGLAD-GALEZI-20261104-FALA2.md`)

Uruchomilem ich testy na ich wlasnym commicie (`python3 -m unittest discover -s tests`):
**1/11 FAIL**.

```
FAIL: test_normalize_ids
  normalize_template("/api/tasks/abc123deadbeef") -> "/api/tasks/abc123deadbeef"
  oczekiwane:                                        "/api/tasks/{id}"
```

Przyczyna: `HEX_LONG_RE = ^[0-9a-fA-F]{16,}$` nie lapie 14-znakowego identyfikatora
szesnastkowego, a ich wlasny test takiego oczekuje. Skutek praktyczny: przy HAR-ach
z ID-ami krotszymi niz 16 znakow kazde ID staje sie osobnym "endpointem", czyli tabela
porownawcza dwoch kont rozjezdza sie dokladnie tam, gdzie szukamy IDOR-a.

## Lokalna poprawka (jedna linia, udokumentowana)

```diff
-HEX_LONG_RE = re.compile(r"^[0-9a-fA-F]{16,}$")
+HEX_LONG_RE = re.compile(r"^[0-9a-fA-F]{12,}$")  # LOCAL FIX (c87): 16 -> 12, patrz PROWENIENCJA.md
```

Po poprawce: **11/11 OK**. Reszta plikow nietknieta. Ich sesja moze to przeniesc na swoja
galaz (albo zmienic test, jesli 16 bylo zamierzone — wtedy prosze o decyzje, bo to wplywa
na czulosc grupowania).

## Jak uruchomic

```bash
cd nask/tools/vendor/a450b00f
python3 -m unittest discover -s tests -p "test_*.py"   # 11/11
python3 har_triage.py --help 2>/dev/null || python3 -c "import har_triage; print(har_triage.__doc__)"
```
