# Przegląd repo `peteraangelic-pixel/NASK` (gałąź `arena/a29ca234-nask`)

Data: 2026-11-03. Sprawdzone wykonawczo, nie po opisie.

## Co jest w repo

- `main` — **1 plik** (`README.md`), commit `e0a562e` „Initial commit".
- `arena/a29ca234-nask` — **25 plików**, 11 commitów, tip `ed96a2f` z 11:44.
  Zawartość: `rust/{subenum,ffuzz,probe,takeover,native}`, `python/{jsminer,gen_report,ffi_native}`,
  `templates/{report,poc-example,scope}`, `STRATEGIA.md`, 2 workflow.

---

## 1. Wynik kompilacji — zmierzony, nie oceniany

```
cargo build --release w rust/<crate>:

subenum    OK          (kompiluje się, działa)
probe      BŁĄD        error[E0599]: no method named `timeout_connect` found for struct `ureq::Request`
takeover   BŁĄD        E0599 ×5 (timeout_connect, status, header, header, into_string)
ffuzz      BŁĄD        E0599 ×5 (jw.)
native     BŁĄD        current package believes it's in a workspace when it's not
```

**3 z 4 crate'ów w workspace nie kompilują się.** Przyczyna jest jedna i banalna:
`timeout_connect` istnieje na `AgentBuilder`, nie na `Request`. Poprawka to 1 linia na plik.

### Skąd się to wzięło — historia commitów to pokazuje

```
15:24  fix: cargo fmt --check (ręczne poprawki formatowania Rust)
15:25  fix: ci.yml - cargo fmt nieblocking
15:27  fix: clippy nieblocking
15:29  fix: clippy nieblocking (|| true)
15:30  fix: subenum używa ToSocketAddrs
15:32  fix: cargo check zamiast cargo build
15:33  fix: usunięto features=[tls] z ureq
15:35  fix: cargo check bez --all-targets
15:36  fix: usunięto cargo check/test z CI
```

Dziewięć commitów „fix", zakończonych **usunięciem kompilacji i testów z CI**. Efekt:
`ci.yml` uruchamia dziś tylko `cargo fmt` (continue-on-error) i `cargo clippy || true`.
**Zielony CI w tym repo nie znaczy nic** — nie sprawdza, czy kod się buduje.

## 2. Najpoważniejszy defekt: brak limitera

```
grep -rniE "rate|limit|req/s|sleep|throttle" rust/ --include=*.rs
→ 1 trafienie, przypadkowe (pętla w lib.rs)
```

W całym repo **nie ma żadnego ograniczenia szybkości**. `ffuzz` i `probe` puszczają Rayonem
tyle żądań, ile rdzeni — na Ryzenie 16/32 to setki req/s.

**Regulamin NASK §6 pkt 2:** „Dopuszczalne jest użycie automatycznych narzędzi z maksymalną
szybkością skanowania na poziomie **5 req/s**." §6 pkt 3: naruszenie **może skutkować
odrzuceniem Zgłoszenia**.

To nie jest „drobiazg wydajnościowy" — to jedyny defekt w tym repo, który może kosztować
wszystkie nagrody naraz, nawet jeśli znajdziesz krytyczną podatność. Moje `naskrecon` ma
sufit 4,5 req/s wspólny dla wątków i **odmawia startu** przy `--rps > 5`.

## 3. Błędy faktograficzne do poprawienia

| gdzie | jest | powinno być |
|---|---|---|
| `README.md` | „300–20 000 PLN za błąd, **pula 1 mln PLN**" | pula **edycji NASK = 100 000 zł** (regulamin §7 pkt 7). Milion to pula całego programu bug bounty NASK, nie tej edycji |
| `templates/scope.md` | „W scope: NASK, CERT Polska, Gov.pl, mSzyfr, Gmina Władysławowo" w jednym arkuszu | 5 **osobnych** programów, każdy z własną listą domen i własnym regulaminem. Jeden arkusz = ryzyko testowania domeny z niewłaściwej edycji |
| `templates/poc-example.md` | przykład IDOR w `mszyfr.gov.pl` | to inny program (mSzyfr). Sam plik uczciwie oznacza „ilustracja, nie rzeczywista luka" — to na plus |
| `.github/workflows/scan.yml` | domyślna ścieżka `rust/wordlists/small.txt` | **taki plik nie istnieje w repo** → workflow wywali się na starcie |
| `STRATEGIA.md` | „Subdomain Takeover — najlepszy stosunek wysiłku do nagrody" | §8 poz. 11.2: takeover **bez działającego PoC przejęcia** jest wykluczony. To nie jest „łatwa" klasa |

## 4. Co jest naprawdę cenne — i przeniosłem to do naszego repo

1. **`templates/report.md`** — dobrze zbudowany szablon zgłoszenia, z checkboxami klas
   z §8 (01–20). Oszczędza pisanie od zera przy każdym raporcie. **Wartościowe.**
2. **`templates/poc-example.md`** — wzorzec PoC z krokami odtworzenia, dwoma własnymi kontami
   i sekcją „ wpływ po ludzku". Dokładnie to, czego wymaga §8 poz. 14 (PoC obowiązkowe). **Wartościowe.**
3. **`python/gen_report.py`** — generuje raport z CLI (program, tytuł, klasa, PoC, wpływ),
   wczytuje plik PoC. 116 linii, bez zależności. **Wartościowe, przeniesione.**
4. **`rust/subenum`** — jedyny działający crate. Pomysł dobry (Rayon + DNS), ale wymagał
   dwóch rzeczy: limitera i guardu zakresu. **Przeniesione z poprawkami.**
5. **`python/jsminer.py`** — pobiera JS z URL i wyciąga endpointy/sekretny. Nasze `naskrecon scan`
   robi to samo offline na plikach; ich wersja ma fetch. Uzupełniające, nie konkurencyjne.

## 5. Czego nie przeniosłem i dlaczego

- **`ffuzz`** — fuzzer bez limitera. Sama idea jest w porządku, ale przy 5 req/s fuzzing
  słownikiem jest bezużyteczny (1000 słów = 3,5 minuty i szum). Wysiłek lepiej włożyć
  w jedno ręcznie sprawdzone żądanie.
- **`takeover`** — klasa wprost wykluczona bez PoC przejęcia (§8 poz. 11.2), a enumeracja
  subdomen `nask.pl` prowadzi do 106 hostów **poza zakresem** (patrz `REKONESANS`).
- **`native`/`ffi_native`** — 92 + ~90 linii po to, żeby licznik wzorców działał w Rust.
  Nasz `naskrecon scan` robi to samo natywnie bez FFI i bez warstwy ctypes.

---

## Podsumowanie jednym akapitem

Repo ma **trafną intuicję** (jedna klasa podatności, PoC, własne konta) i **jedną naprawdę
przydatną rzecz do natychmiastowego użycia** — szablon raportu z generatorem. Ale kod jest
w stanie nieukończonym: 3 z 4 crate'ów się nie budują, CI przestało cokolwiek sprawdzać,
a fuzzer bez limitera 5 req/s może unieważnić nawet udane zgłoszenie. Najlepsze, co można
z tym zrobić, to **zostawić szablony, a narzędzia wziąć z `naskrecon`** — które ma limiter,
guard zakresu i odejmowanie catch-all, i przechodzi 16 testów.
