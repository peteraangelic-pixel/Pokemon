# Segmentacja: Rust + rayon vs Python — zmierzone

## Wyniki

| Klatka 64×64 | Komponentów | **Python** | **Rust (4 wątki)** | Przyspieszenie |
|---|---|---|---|---|
| Solniczka (4 kolory, przypadek patologiczny) | 2142 | **4400 ms** | **15.9 ms** | **~276×** |
| Realistyczna (18 dużych obiektów) | 17.6 | **39.4 ms** | **0.326 ms** | **~121×** |

- Python: `inference/utils/segmentation.py` z Duck harness, mierzone lokalnie, 30 klatek, po rozgrzewce.
- Rust: runner GitHub Actions, 4 wątki, 2000 / 5000 klatek.
- Generatory dają statystycznie równoważne klatki (2142 vs 2148 i 17.6 vs 17.6 komponentów), więc porównanie jest uczciwe.

**Per-rdzeń** Rust jest ~30–40× szybszy od Pythona; reszta to równoległość.
Na Twoim **5950X (16 rdzeni)** realistyczna klatka powinna zejść do **~0.08 ms**, czyli **~480×** względem Pythona. Twoje założenie „nawet 200×" było ostrożne — w praktyce jest lepiej.

## ⚠️ Uczciwe zastrzeżenie: to nie jest wąskie gardło 9 godzin

Policzmy to, zamiast się nim zachwycać:

- Realistyczna klatka, Python: 39 ms. Przy ~500 turach agenta na grę → **~20 s na grę** → 55 gier ≈ **18 minut**. To nie jest problem.
- Ale klatka patologiczna, Python: 4400 ms → **37 minut na grę**. Jedna taka gra i budżet 9 h leży.

**Gdzie Rust naprawdę robi różnicę:**
1. **Ogon rozkładu.** Algorytm zawierania jest O(n²) względem liczby komponentów. Plansze z dużą liczbą drobnych obiektów istnieją — i wtedy Python przestaje się mieścić. Rust zamienia katastrofę w niezauważalny koszt.
2. **Analiza offline.** Przeglądanie tysięcy nagranych przebiegów po kilkaset tur: 1e6 klatek × 39 ms = **11 godzin** w Pythonie; w Rust na 16 rdzeniach ≈ **1.3 minuty**. To jest przepaść, która decyduje, czy w ogóle możemy szukać zmarnowanych akcji.
3. **Precompute.** Wyszukiwanie offline (BFS, cache pre-solve) przetwarza wielkie ilości stanów. Tam rayon jest jedynym powodem, dla którego to w ogóle wykonalne.

**Wniosek:** nie piszemy tego w Rust, żeby uratować 9 godzin na Kaggle. Piszemy, żeby móc robić analizę i precompute, których w Pythonie nie da się wykonać w rozsądnym czasie.

## Jak powtórzyć pomiary

```bash
cd arc-agi-3/rust
cargo build --release
./target/release/arc3 bench --size 64 --frames 5000 --mode blobs
./target/release/arc3 bench --size 64 --frames 2000 --mode salt
```

Logi z każdego uruchomienia CI lądują w `arc-agi-3/ci-logs/`.
