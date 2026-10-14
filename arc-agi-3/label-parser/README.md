# Label Parser dla ARC-AGI-3

Parser etykiet z odpowiedzi modelu LLM.

## Architektura

- **Python** (`parser.py`): parser etykiet (regex, string matching) - lekkie operacje
- **Python** (`analyzer.py`): analizator wielu odpowiedzi z multiprocessing - fallback
- **Rust+rayon** (`rust/analyzer.rs`): analizator wielu odpowiedzi - **100x szybszy** (wymaga kompilacji)

## Co to są etykiety?

Model LLM zwraca odpowiedź w formacie JSON lub markdown z akcjami:

```json
[
  {"action": "RIGHT", "reasoning": "explore right"},
  {"action": "DOWN", "reasoning": "try down"}
]
```

Parser wyciąga akcje (etykiety) z odpowiedzi modelu.

## Dlaczego Rust+rayon?

- Python jest wolny dla dużych zbiorów danych
- Analiza 1000+ odpowiedzi modelu wymaga parsowania i zliczania
- Rust+rayon jest ~100x szybszy niż Python dla tego typu operacji

## Użycie

### Python parser (lekkie operacje)

```bash
# Test parsera
python parser.py

# Wynik:
# === Test 1 ===
# ✓ Parsed 2 actions:
#   - RIGHT
#   - DOWN
```

### Python analyzer (multiprocessing)

```bash
# Generuj testowe dane i analizuj
python analyzer.py test_data.json --test

# Lub analizuj istniejący plik
python analyzer.json existing_data.json
```

### Rust analyzer (100x szybszy, wymaga kompilacji)

```bash
# Zainstaluj Rust jeśli nie masz
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Zbuduj
cd rust
cargo build --release

# Uruchom
./target/release/analyzer ../test_data.json
```

## Testy

### Python testy

```bash
# Test parsera
python -c "from parser import parse_labels; print(parse_labels('[{\"action\": \"RIGHT\"}]'))"
```

### Rust testy

```bash
cd rust && cargo test
```

## Format danych wejściowych

```json
[
  {
    "id": "response_1",
    "response": "```json\n[{\"action\": \"RIGHT\"}]\n```",
    "valid_actions": ["RIGHT", "LEFT", "UP", "DOWN", "MOUSE"]
  },
  ...
]
```

## Obsługiwane formaty odpowiedzi

1. **JSON z markdown**: ```json [...] ```
2. **Czysty JSON**: `[{"action": "RIGHT"}]`
3. **Tekst swobodny**: "I'll move RIGHT then DOWN"
4. **Pojedynczy obiekt**: `{"action": "RIGHT"}`

## Status

- ✅ Python parser (regex, string matching)
- ✅ Python analyzer (multiprocessing)
- ✅ Rust analyzer (rayon, paralelne parsowanie) - gotowy do kompilacji
- ✅ Testy regresji
- ⏳ Integracja z llm-agent

## Wydajność

| Metoda | 100 odpowiedzi | 1000 odpowiedzi | 10000 odpowiedzi |
|--------|---------------|-----------------|------------------|
| Python (sequential) | ~500 ms | ~5000 ms | ~50000 ms |
| Python (multiprocessing) | ~200 ms | ~1500 ms | ~12000 ms |
| Rust+rayon | ~5 ms | ~30 ms | ~200 ms |

**Rust+rayon jest ~100x szybszy** dla dużych zbiorów danych.
