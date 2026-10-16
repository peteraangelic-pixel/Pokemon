# ⚠️ POPRAWIONA INSTRUKCJA - Duck Harness Submission

**OSTATNIA AKTUALIZACJA:** 16.10 2026, 14:30 PL  
**STATUS:** Łańcuch nocny przejmie submit automatycznie

---

## ❌ NIE ROB TEGO RĘCZNIE

**Dlaczego:**
1. **GPU quota crash** - P100/T4 nie obsługuje FP8 (wymaga RTX PRO 6000, CC 8.9+)
2. **Daily limit** - tylko **1 submisja dziennie** (nie 2!), zajmiemy slot przed auto-submitem
3. **Brak zabezpieczenia budżetu** - notebook spali 9h z 30h/tydzień bez kontroli
4. **Łańcuch nocny zrobi to lepiej** - auto-submit z retry, atrybucją, monitoringiem

---

## ✅ PLAN: ŁAŃCUCH NOCNY (AUTOMATYCZNY)

**Harmonogram:**
- **16:25 UTC** (18:25 PL) - segment 2
- **21:50 UTC** (23:50 PL) - segment 3
- **00:00 UTC** (01:00 PL, sobota) - **push GPU z zabezpieczeniem budżetu**
- **~01:30-04:30 UTC** - auto-submit z poprawną receptą
- **~14:00 PL** (sobota) - wyniki na LB (rerun ~9h)

**Oczekiwany wynik:** 40-56 punktów (bazując na historycznym 56.52 + kalibracji)

**Co robi łańcuch:**
1. ✅ Zabezpieczenie kwoty (guard z Cell 14)
2. ✅ Retry na reset kwoty (00:00 UTC)
3. ✅ Poll statusu + auto-submit (`-v N -f submission.parquet`)
4. ✅ Atrybucja Tufy Labs
5. ✅ Wyniki do repo (bez ręcznej interwencji)

---

## 📊 KOREKTY DO POPRZEDNIEJ INSTRUKCJI

### ❌ BŁĄD: "Ten notebook da 68.91"
**PRAWDA:** 68.91 to **aktualny LB Tufy** z nowszej pracy. Ten kernel (June-30 milestone) → realny rerun: **~52-56** (historyczny 56.52, nasza kalibracja smoke→LB)

### ❌ BŁĄD: "Max 2 submisje dziennie"
**PRAWDA:** **1 dziennie** - dowód: nasz submit o 00:02 → "0 submissions remaining today"

### ❌ BŁĄD: "GPU P100 lub T4 x2 (minimum)"
**PRAWDA:** Model FP8 wymaga **RTX PRO 6000** (CC 8.9+). P100 (CC 6.0) i T4 (7.5) → **CRASH** po spaleniu kwoty

### ❌ BŁĄD: "~3-4h GPU na run"
**PRAWDA:** Pełny run ma **9h budżetu**. Notebook bez guard z Cell 14 → ręczne "Save & Run All" zjada ~9h z 30h/tydzień

### ❌ BŁĄD: Brak kroku "Submit"
**PRAWDA:** Instrukcja nie zawierała kroku submit! Po "Save & Run" notebook tylko działa, ale nie zgłasza wyniku do LB.

---

## 🎯 CO ROBIMY TERAZ

### Opcja 1: NIC (zalecane)
**Poczekaj na łańcuch nocny** - zrobi wszystko automatycznie, bezpieczniej, z retry.

**Kiedy sprawdzisz wyniki:**
- Sobota ~14:00 PL (po LB rerun)
- Powinieneś mieć **40-56 punktów** na tablicy

### Opcja 2: Ręczny submit (ODRADZAM)
**TYLKO jeśli:**
1. Masz dostęp do **H100/A100 GPU** (nie P100/T4!)
2. Jesteś pewien że masz **daily slot wolny** (sprawdź w Kaggle)
3. Zrozumiesz że zajmujesz slot przed auto-submitem
4. Dodasz guard z Cell 14 do notebooka (zabezpieczenie budżetu)

**Jak wtedy:**
1. Otwórz Kaggle Competition
2. Załaduj `duck-harness-original.ipynb`
3. Dodaj 3 datasety (te same co w łańcuchu)
4. **WAŻNE:** Wybierz GPU H100 lub A100 (NIE P100/T4!)
5. Dodaj guard z Cell 14 (zabezpieczenie budżetu)
6. Kliknij "Save & Run All"
7. **POCZEKAJ** aż notebook się zakończy (~9h)
8. Sprawdź "Submissions" → kliknij "Submit to Competition"

---

## 🔧 WARTOŚCIOWE Z PAKIETU (wykorzystane)

✅ Lista 3 datasetów = identyczna jak w naszych metadanych  
✅ Link do opisu Tufy + GitHub (do weryfikacji po nocy)  
✅ Notka o Franzen M2 (47.25, Qwen3.8-Flash-Next) = drugi kandydat dla genius-v2

---

## 📝 CO DALEJ (po nocy)

**Sobota rano (~14:00 PL):**
1. Sprawdź LB → powinna być liczba z rodziny 40+
2. Jeśli wynik < 45 → debuguj logi łańcucha
3. Jeśli wynik > 55 → sukces! Rozważ genius-v2 (Franzen M2) na 18.10

**Niedziela (18.10):**
- Plan: **genius-v1** na bazie r033 (rekonstrukcja `game_weights` + podmiana modelu)
- Cel: jeszcze lepszy wynik niż Duck harness

---

## ⚠️ JEŚLI ZOBACZYSZ "SUBMITUJ RĘCZNIE"

**IGNORUJ do potwierdzenia od łańcucha nocnego.**

Łańcuch zrobi auto-submit automatycznie. Ręczny submit = ryzyko:
- Spalenie GPU kwoty przed łańcuchem
- Zajęcie daily slot przed auto-submitem
- Crash na niewłaściwym GPU

---

## 📞 KONTAKT

**Po nocy (~14:00 PL):**
- Sprawdź repo → wyniki powinny być w commitach
- Sprawdź LB → powinna być liczba 40-56
- Jeśli coś nie gra → sprawdź logi łańcucha w `arc3-ops.yml` runs

**Przed nocą:**
- NIE ruszaj `request.json`
- NIE dispatchuj `arc3-ops.yml` ręcznie
- NIE submituj niczego ręcznie

---

**Podsumowanie:** Czekaj na łańcuch nocny. Nie rób nic ręcznie. Rano będziesz miał wynik.
