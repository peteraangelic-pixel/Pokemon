# ARC-AGI-3 — stan i przekazanie (handoff)

> Ten plik istnieje po to, żeby **nowa sesja Arena.ai mogła podjąć pracę w 2 minuty**.
> Nowa sesja nie pamięta tej rozmowy — wszystko, co ma wiedzieć, musi być tutaj.

**Ostatnia aktualizacja:** 10 X 2026, ~20:30 CEST

---

## Stan: ETAP 0 — analiza zrobiona, kod nietknięty

| Pozycja | Wartość |
|---|---|
| Konkurs zaakceptowany na Kaggle | ✅ (użytkownik potwierdził) |
| Sklonowany baseline | ✅ `Tufalabs/duck-harness` (MIT) — **tylko w `.cache/duck`, NIE w repo** |
| Analiza architektury | ✅ `README.md` w tym katalogu |
| Uruchomiony baseline na Kaggle | ❌ **następny krok** |
| Jakakolwiek zmiana w kodzie | ❌ |
| Wynik własny na leaderboardzie | ❌ |

⚠️ **`.cache/` jest wyłączone ze snapshotów.** Po nowym uruchomieniu trzeba zrobić
`git clone --depth 1 https://github.com/Tufalabs/duck-harness.git` od nowa.

---

## Co już wiemy (nie odkrywaj tego od zera)

Kontekst rynkowy — patrz `../konkursy-ai-2026.md` (główny brief):
- 28 aktywnych teamów (nie 4 494 — to liczba kont), top to Tufa Labs 55,89 RHAE
- Leaderboard skoczył z 27,9% (30 IX) na 55,89% (4 X), bo Duck poszedł open-source
- Zostało **$75 000 dla top-5**; milestone'y (30 VI, 30 IX) przepadły; $700k bonusu poza zasięgiem
- **Zero wymogu angielskiego** — czysty wynik na leaderboardzie, bez writeupu (w przeciwieństwie do ARC-AGI-2, gdzie $275k jest *za opis*)

Technika — patrz `README.md` w tym katalogu:
- 7 słabych punktów zidentyfikowanych w kodzie, z numerami linii
- Największa luka: **brak pamięci między 20 passami** (`_ensure_session` zeruje wszystko)
- Druga: **wiedza kasowana przy przejściu poziomu** (6 z 7 slotów)
- Trzecia: parser etykiet gubi markdown (`**World model:**` nie zadziała) — najłatwiejszy pewny zysk
- **Binding constraint: 9 h na notebooku Kaggle.** Config z repo (25 gier × 20 passów × 45 min) się nie mieści

---

## Następny krok (dokładnie)

1. Wejść na https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/code
2. Wrzucić `taaf-duck-harness-kaggle-share.ipynb` ze sklonowanego repo **bez żadnych zmian**
3. Odpalić na **podzbiorze gier** (nie 25×20 — nie zmieści się w 9 h), np. 5 gier × 1 pass
4. Zapisać do `baseline.md`: wynik RHAE + **realny czas jednego passu na GPU Kaggle**
5. Dopiero potem ruszać punkty E → B → A z `README.md`

Bez kroku 4 nie da się zaplanować reszty, bo nie wiemy, ile passów mieści się w 9 godzinach.

---

## Deadline'y

| Data | Co |
|---|---|
| 26 X 2026 | entry deadline — **już zaakceptowane** |
| **2 XI 2026** | **finałowa submision** |
| 4 XII 2026 | ogłoszenie wyników |

Dni do submision: **22** (od 10 X)

---

## Podział na sesje (ustalony z użytkownikiem)

| Sesja | Branch | Cel |
|---|---|---|
| `arena/7cc8a7e0-pokemon` | **ta sesja** | Pokémon TCG AI Battle Challenge (Kaggle) |
| osobna (do założenia) | przydzieli Arena | **ARC-AGI-3** ← to |
| osobna | — | Gemma 4 Developer Agent (już działa) |
| osobna | — | hackathony Devpost |

⚠️ **Zasada:** jeden konkurs = jedna sesja. Nie puszczać tego samego konkursu w dwóch sesjach — Kaggle to jedno konto = jedna osoba, dwa teamy grożą dyskwalifikacją.

---

## Jak zacząć nową sesję

Wklej na początku:

```
Przeczytaj arc-agi-3/README.md i arc-agi-3/STATUS.md w tym repo.
Pracujemy nad ARC-AGI-3 na Kaggle (deadline 2 XI 2026).
Kontynuuj od kroku „Następny krok" w STATUS.md.
Nie rób zmian w kodzie poza katalogiem arc-agi-3/.
```
