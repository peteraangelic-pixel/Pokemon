# Integracja z sesją arena/98ddb59f-pokemon (Duck harness)

**Data:** 2026-10-14 02:55 UTC

## Kluczowe ustalenia (z DIAGNOSIS.md i FAILURES.md)

### Główny problem
- **50.9 pkt traci na nierozwiązanych poziomach**, tylko 2.6 pkt na nadmiarze ruchów
- **Wniosek**: "action efficiency is not the problem. Points are lost because levels are not solved"
- Agent jest ograniczony myśleniem (81k tokenów), nie akcjami (0.58 akcji/ruch)

### Klasyfikacja porażek (10 transkryptów)
- **(a) nowa mechanika niezrozumiana: 6/10 przypadków** - agent dedukuje z pikseli zamiast eksperymentować
- **(b) zły cel: 3/10 przypadków** - hipoteza z poziomu 1 nie działa na poziomie 2
- **(c) dobry model ale brak rozwiązania: 1/10 przypadków**
- **(d) pętla: 0/10 przypadków**

### GOAL_CATALOG.md (15 gier treningowych)
6 klas celów: POKRYJ, DOTRZYJ, KOPIUJ, OGRANICZENIA LOKALNE, ZREDUKUJ, UMIEŚĆ, PRZEPŁYW, WYRÓWNAJ

Kluczowe zasady:
1. **Warunek wygranej to zawsze "wszystkie"** - wszystkie cele pokryte, wszystkie awatary na wyjściach
2. **6/15 gier to KOPIUJ** - wzorzec do skopiowania lub przetłumaczenia
3. **Licznik malejący to limit kroków** - wyzerowanie = przegrana, nie wygrana
4. **86% straty powstaje po rozwiązaniu poziomu 1** - agent zna cel, ale utknął

### Propozycje zmian (z FAILURES.md)
1. **Automatyczny raport o nowych elementach** - po wejściu na nowy poziom harness wskazuje co jest nowe
2. **Wymuszona sonda** - dla każdego nowego elementu harness wykonuje 1-3 tanie akcje
3. **Limit tokenów rozmyślania** - po przekroczeniu harness wymusza eksperyment

**Problem**: "Phase 3 feasibility check" pokazał, że automatyczna sonda ma niski yield (15% widocznych efektów).

## Moje zmiany (w tej sesji)

1. ✅ **Skrócony prompt** - mniej tokenów na myślenie (z ~81k do ~10k)
2. ✅ **Batch actions** - LLM planuje 5-10 akcji naraz (zmniejsza liczbę wywołań modelu)
3. ⏳ **GOAL_CATALOG w prompt** - dodać warunki wygrane dla gier treningowych
4. ⏳ **Instrukcja eksperymentowania** - "jeśli widzisz nowy element, kliknij/go dotknij zamiast myśleć"

## Strategia

1. Zgłosić moje zmiany (prompt + batch + GOAL_CATALOG)
2. Jeśli wynik lepszy niż obecny (~1-5 pkt), sukces
3. Jeśli nie, potrzebna głębsza zmiana strukturalna (ale to wymaga dostępu do Duck harness)

## Status

- ✅ GOAL_CATALOG.md pobrany
- ✅ FAILURES.md pobrany
- ✅ DIAGNOSIS.md przeczytany
- ⏳ Zgłoszenie na Kaggle (wymaga rezerwacji w issue #1)
- ⏳ Integracja GOAL_CATALOG z LLM agentem
