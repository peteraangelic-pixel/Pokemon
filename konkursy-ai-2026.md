# Konkursy AI — przegląd (rewizja 3, stan na 10 października 2026)

Dodane kryteria po Twoich uwagach: **bariera językowa** i **realne szanse (pula / liczba uczestników)**.

## Co się zmieniło

| Konkurs | rev 1 | rev 2 | rev 3 | Powód |
|---|---|---|---|---|
| **ARC-AGI-3** | poza planem | 🥇 #1 | 🥇 **#1, wzmocniony** | Zero angielskiego — czysty kod |
| **Agenthon 2026** | poza planem | sprint 48h | ❌ **odrzucony** | Regulamin: o sobie do Atlanty, nagrody nie pokrywają |
| **Dubai** | #4 | warunkowo | ❌ **odrzucony** | Live pitch po angielsku, na scenie, w Dubaju |
| **Hackathony** | plan B | plan B | 🥈 **#2, ale wybrane** | Błąd: wrzuciłem je do jednego worka |

---

# 🥇 1. ARC-AGI-3 — i teraz jeszcze mocniej

## Dlaczego to nasz numer jeden (trzy powody, nie jeden)

**1. Tylko 28 aktywnych teamów.** 4 494 „zgłoszeń" na Kaggle to w większości martwe konta.
**2. Pole przyspiesza, nie zwalnia:** 27,9% (30 IX) → **55,89% (4 X)**. Lider Tufa Labs 55,89, drugi 48,59, klaster 33–38%.
**3. Wygrywa inżynieria harnessu, nie model.** Tufa Labs wypuściło **„The Duck" na licencji MIT** (Qwen 3.6 27B FP8, jedna karta GPU). Kontrolowany eksperyment OpenAI: **te same ustawienia harnessu = 4,9× wyniku bez zmiany modelu**.

## I to, co jest dla Ciebie kluczowe: **zero angielskiego**

- Zostało **$75 000 dla top-5** ($40k/$15k/$10k/$5k/$5k) — nagroda **za wynik na leaderboardzie, nie za opis**
- Milestone'y ($75k) przepadły, $700k bonusu jest poza zasięgiem (najlepszy model świata: 62,7%)
- **Nie ma wymogu writeupu.** Dla porównania: ARC-AGI-2 ma $275k grand prize *właśnie za napisany opis* — tamten konkurs jest dla nas gorszy, mimo wyższej kwoty

Wgrywasz notebook, dostajesz wynik. To jedyna duża pula na stole, w której język nie gra żadnej roli.

## Terminy i ograniczenia
- **26 X 2026** — entry deadline (trzeba zaakceptować regulamin, żeby w ogóle startować)
- **2 XI 2026** — finałowa submision · **4 XII** — wyniki
- Notebook GPU ≤ 9h, CPU ≤ 9h, **bez internetu**

## Plan
1. **Dziś**: zaakceptować regulamin (warunek konieczny) → fork `Tufalabs/duck-harness` (MIT), gotowy notebook `taaf-duck-harness-kaggle-share.ipynb`
2. **Dni 1–3**: baseline na 25 grach publicznych, liczba na tablicy
3. **Dni 4–14**: iteracja po **context management** i **perception** — osiach, które Tufa Labs samo wskazało jako niewyeksploatowane. Uwaga z ich writeupu: *dorabianie specjalistycznych narzędzi szkodzi*; wygrywa czysty, ogólny interfejs REPL
4. **Dni 15–16**: finałowa submision

Realistyczna szansa na top-5: **10–20%**. Najlepszy stosunek szansy do wkładu ze wszystkiego, co dziś jest otwarte.

---

# 🥈 2. Hackathony — moje zaniedbanie, naprawiam

Miałeś rację, że je zbyłem. Powód był taki: **wrzuciłem je do jednego worka**. A ten worek zawiera i loterię 1:53 000, i strzał 1:841 przy $40 000.

## Pula na uczestnika — jedyny wskaźnik, który tu cokolwiek mówi

| Hackathon | Pula | Zapisanych | $/osoba | Deadline |
|---|---|---|---|---|
| **AWS CDS Agentic AI Partner** | **$40 000** | 841 | **$47,6** | 28 X |
| **Life After Code** | **$45 000** | 1 531 | **$29,4** | 27 X |
| **Qloo Agentic** | **$25 000** | 956 | **$26,2** | 30 X |
| Galuxium Nexus V2 | $14 644 | 968 | $15,1 | 31 X |
| Arbiter Hacks V1 | $3 800 | 247 | $15,4 | 21 XII |
| YouCam API Skin AI | $6 000 | 776 | $7,7 | 2 XI |
| PayPal AI Hackathon | $67 500 | 10 974 | $6,2 | 12 XI |
| OpenCV AI Comp. 2026 | $20 250 | 4 575 | $4,4 | 27 X |
| IEEE ClimateChain | $3 000 | 679 | $4,4 | 25 X |
| Agents for Humans (AWS) | $40 000 | 9 923 | $4,0 | 14 X |
| Nebius × NVIDIA | $50 000 | 20 699 | $2,4 | 30 X |
| Amazon Build/Ship/Shape | $138 000 | 52 920 | $2,6 | 23 X |
| 🥇 **Meta VR Start 2026** | **$1 000 000** | **2 831** | **$353** | **18 XI** |

**Ważne zastrzeżenie:** „zapisanych" to rejestracje, nie submissiony. Realnie zgłasza projekt zwykle 5–15% zapisanych — czyli **szanse są kilkukrotnie lepsze, niż pokazuje tabela**. Wskaźnik służy tylko do porównania między sobą.

## Dlaczego duże nazwy to zły wybór
Amazon ($138k) brzmi świetnie, dopóki nie zobaczysz 52 920 zapisanych. Nebius×NVIDIA ($50k) ma 20 699. To są marketingowe eventy sponsorów — wygrywają tam zespoły, które najbardziej widowiskowo użyły stacku sponsora. **Nie to, w czym jesteśmy dobrzy.**

## Nasz wybór
**AWS CDS Agentic AI Partner ($40k, 841 zapisanych, deadline 28 X)** — najlepszy stosunek puli do tłumu, temat agentowy (konwersacyjne doświadczenia), i mamy dwa tygodnie. Równolegle **Life After Code** ($45k, 27 X) albo **Qloo Agentic** ($25k, 30 X) jako drugi strzał.

**Meta VR Start ($1M, 2 831, 18 XI)** to dzika karta z najlepszym wskaźnikiem na całej planszy — ale to VR, nie agenci. Jeśli masz ochotę, warto rozważyć; jeśli nie, pomiń.

## Bariera językowa w hackathonach — da się obejść
- **Opis pisemny**: ja piszę po angielsku. Zero problemu.
- **Wideo demo**: screen recording bez głosu + napisy, które wygeneruję. Nie musisz mówić.
- **Live pitch**: omijać. To odrzuca Dubai i Agenthon.

---

# ❌ 3. Agenthon 2026 — odrzucony, i regulamin to potwierdza

Sprawdziłem §10 i §11 oficjalnych zasad (AH26-POL-01):

> **§11:** „Finalist or winner status **does not itself provide** NeurIPS registration, a badge, venue access, a visa, travel authorization, or entry into the host country."
> **§11:** „Unless separately announced, **participants are responsible for** registration, travel, immigration, and venue-entry requirements."
> **§11:** „Alternative presenters or arrangements for exceptional circumstances require written Organizer approval... **No remote or substitute arrangement is guaranteed**."
> **§10:** „Prize categories, amounts, sponsor-funded awards, and **special eligibility conditions will be announced** through an official channel before they apply to the Final Phase."

**Werdykt:**
- Podróż **nie jest dziś twardym wymogiem** w regulaminie — ale warunki nagród **nie zostały jeszcze ogłoszone** i mogą prezentację w Atlancie do nich dopisać („failure to satisfy an expressly announced presentation or prize condition may affect... prize eligibility")
- Organizatorzy nie pokrywają ani rejestracji na NeurIPS, ani lotu, ani wizy
- Nagroda $1 500 nie pokrywa nawet biletu do Atlanty, o hotelu nie mówiąc
- Prezentacja byłaby po angielsku, na żywo

**Za $1 500, przy 48 godzinach na zbudowanie agenta i z lotem do USA na własny koszt — nie ma sensu. Zgadzam się z Tobą.**

Jeśli chcesz mieć to na piśmie: mogę przygotować krótkiego maila po angielsku do `admin@agenthon.net` z pytaniem, czy prezentacja w Atlancie będzie warunkiem otrzymania nagrody. Koszt: minuta Twojego czasu.

---

# ❌ 4. Dubai Create AI Agents — odrzucony

Zastrzeżenie, którego w rev 1 nie sprawdziłem: **to grant, nie nagroda.**

> „USD 150,000 **grant** to support the development and growth of their AI-agent solution and business — **built in Dubai**, for the world"
> „open to all UAE residents and **international startups interested in expanding into the region**"

Dodatkowo: wymaga pitch decku + wideo po angielsku, a 12 finalistów **demonstruje działającego agenta na żywo na scenie w Dubaju** (maj 2027). Przy barierze językowej i bez chęci robienia venture w ZEA — odpadła.

---

# 5. Reszta (bez zmian)

**Agent-vs-agent (robisz sam):** Pokémon TCG Playground (8 I 2027, bez kasy) · Kaggriculture ($50k, **14 X** ⚠️) · Battlecode (styczeń 2027) · Lux AI (S4 nie ogłoszony) · CodinGame · Screeps · AgentBeats/AgentX · Numerai (~$700 mln AUM)

**Duże pule:** ARC-AGI-2 ($700k — ale $275k z tego to **writeup**, odpuść) · ARC Paper Track ($450k, 9 XI — ja piszę, rozważymy) · Gemma 4 (robisz w innej sesji) · DrivenData GEMS ($300k) · NFL Big Data Bowl 2027 ($100k, 6 I) · RSNA ($77k, 22 X) · Enveda CASMI ($50k, 14 XII)

**Inne platformy:** Zindi · Tianchi · DataFountain · Signate · CodaLab · DataSource.ai · KDD Cup

---

# Plan — rev 3

**Dziś:**
1. **ARC-AGI-3** — zaakceptować regulamin na Kaggle (deadline 26 X). To jest jedna czynność, bez której reszta nie ma sensu.
2. Fork `Tufalabs/duck-harness`, uruchomić baseline.

**Najbliższe 2 tygodnie:**
3. **ARC-AGI-3** — iteracja po context management + perception → submision do **2 XI**
4. **AWS CDS Agentic AI Partner** ($40k / 841 zapisanych) → submision do **28 X**

**Jeśli zostanie czas:**
5. **Qloo Agentic** ($25k, 30 X) lub **Life After Code** ($45k, 27 X)
6. **ARC Paper Track** ($450k, 9 XI) — ja piszę artykuł na bazie tego, czego nauczymy się przy ARC-AGI-3. Ty nic nie musisz mówić ani pisać.

**Odrzucone:** Agenthon (koszt > nagroda, angielski na żywo) · Dubai (live pitch, grant nie nagroda) · ARC-AGI-2 (główna pula za angielski writeup)

**Śledź:** Battlecode 2027 (rejestracja od ~XI) · Lux AI S4 · kolejna płatna edycja Pokémon TCG AI Battle Challenge

---

# 6. Co to jest „Top hackathon themes" na devpost.com

**To nie jest lista nagród i nie są to konkursy.** To ranking **tagów zainteresowań**, posortowany według tego, ile *obecnie otwartych* hackathonów nosi dany tag.

| Kolumna | Co znaczy |
|---|---|
| **Theme** | nazwa tagu (np. Machine Learning/AI) |
| **Hackathons #** | ile hackathonów jest teraz otwartych z tym tagiem |
| **Total prizes** | **suma** pul nagród wszystkich tych hackathonów |

Po kliknięciu w pozycję trafiasz na stronę wyszukiwania (`devpost.com/hackathons?themes[]=...`) z listą hackathonów i datami — dokładnie tak, jak zauważyłeś.

**Aktualna tabela (10 X 2026):**

| # | Theme | Otwartych | Suma nagród |
|---|---|---|---|
| 1 | Beginner Friendly | 94 | $751 000 |
| 2 | **Machine Learning/AI** | 78 | **$1 598 000** |
| 3 | Open Ended | 48 | $405 000 |
| 4 | Social Good | 44 | $124 000 |
| 5 | Education | 31 | $203 000 |
| 6 | Web | 29 | $1 115 000 |
| 7 | Low/No Code | 19 | $75 000 |
| 8 | Productivity | 16 | $217 000 |
| 9 | Design | 16 | $31 000 |
| 10 | Health | 16 | $18 000 |

⚠️ **Dwie pułapki:**
1. **Tagi się pokrywają.** Jeden hackathon może być jednocześnie „Machine Learning/AI" + „Beginner Friendly" + „Open Ended". **Nie wolno sumować tych kwot** — to nie jest $4,5 mln do wzięcia.
2. Po kliknięciu domyślnie pokazuje też **zakończone** hackathony (dlatego „Showing 6785 hackathons"). Trzeba zaznaczyć **Status → Open** w lewym panelu. Parametr w URL-u jest ucinany, więc kliknij ręcznie.

**Najciekawszy wniosek:** ML/AI ma $1 598 000 / 78 = **średnio $20,5 tys. na hackathon** — najwięcej pieniędzy w przeliczeniu na konkurs. A połączenie **Machine Learning/AI + Beginner Friendly** to pieniądze z ML przy słabszej konkurencji.

---

# 7. Agenthon vs ARC-AGI-3 — gdzie większe szanse

## Czas (stan: sobota 10 X, 20:18 CEST)
- **Agenthon**: ostatnie uruchomienie developmentowe **poniedziałek 12 X, 22:00 CEST** → zostało **~50 godzin**
- **ARC-AGI-3**: **22 dni** (submision 2 XI)

## Pytanie: „czy Agenthon nie jest taki trudny?"
Nie jest łatwy. Liczby z leaderboardu T1:
- Lider **0,7674 pass@1** — czyli jego agent rozwiązuje **77% zadań kodowania quant-finance za pierwszym podejściem**. To jest bardzo dobry agent.
- 100 teamów, gęsty klaster 0,19–0,38.

W ~50 godzin musielibyśmy zbudować od zera obraz Dockera z autonomicznym agentem, który: implementuje ich interfejs CLI, działa bez internetu (tylko House Nemotron), i przechodzi **nie tylko pytest, ale i „financial invariants"** — czyli konwencje finansowe (day-count, kapitalizacja, brak look-ahead), które nie są naszą mocną stroną. Do tego rejestracja, zespół, dostęp do repo treningowego, wygenerowanie ZIP-a toolkitu, upload na CodaBench.

**Realistycznie:** szansa na w ogóle *ważną* submision ~50%. Szansa na top-3 ~10%.

## Porównanie

| | **ARC-AGI-3** | **Agenthon T1** |
|---|---|---|
| Pula realna | **$75 000** dla top-5 | $1 500 |
| Kto dostaje kasę | **top-5 z 28 aktywnych = górne 18%** | top-3 ze 100 = górne 3% |
| Czas | **22 dni** | ~50 godzin |
| Punkt startowy | MIT harness, który **już ma ~55%** | zero |
| Domena | abstrakcyjne gry — nasza | quant-finance — nie nasza |
| Angielski | **zero** | prezentacja na NeurIPS (może) |
| Podróż | brak | Atlanta (może) |
| Szansa top | **~15–25%** | ~10% (jeśli zdążymy) |
| **Wartość oczekiwana** | **~0,20 × 15 000 = ~$3 000** | ~0,10 × 1 500 = **~$150** |

**Werdykt: ARC-AGI-3, i to nie jest blisko.** Różnica to ~20× w wartości oczekiwanej, 10× więcej czasu i zero bariery językowej.

Jeśli bardzo Ci zależy na Agenthonie: mogę poświęcić 30–60 minut na ściągnięcie publicznego repo treningowego i ocenę, jak trudny jest naprawdę baseline. Wtedy decydujemy na danych, nie na domysłach. Ale zróbmy to **po** postawieniu ARC-AGI-3, nie zamiast.

---

# 8. Jak puścić to w osobnych sesjach Arena.ai

**Tak, to dobry pomysł — i prawdopodobnie najlepszy sposób, żeby to wszystko dowieźć.** Zasady:

## ✅ Rób tak
- **Jeden konkurs = jedna sesja.** Każda sesja dostaje własny branch; ta jest `arena/7cc8a7e0-pokemon`.
- Sensowny podział:
  - **Sesja A (ta)** → **ARC-AGI-3** (główny cel)
  - **Sesja B** → **AWS CDS Agentic AI** ($40k, deadline 28 X)
  - **Sesja C** → Gemma 4 (piszesz, że już masz)
  - **Sesja D** → Pokémon TCG Playground

## ❌ Tego nie rób
- **Nie puszczaj tego samego konkursu w dwóch sesjach naraz.** Kaggle: jedno konto = jedna osoba, a regulaminy wprost zabraniają wielu tożsamości (Agenthon: „Each person may use one competition identity and belong to one team only"). Dwa teamy z jednego konta = ryzyko dyskwalifikacji.
- **Nie zakładaj, że nowa sesja cokolwiek pamięta.** Każda zaczyna z pustym kontekstem.

## 🔑 Przekazanie kontekstu (najważniejsze)
Ponieważ nowa sesja nic nie wie, **stan musi być w plikach**. Procedura:
1. Ten plik (`konkursy-ai-2026.md`) jest **głównym briefem**. Trzymaj go w repo.
2. W każdej nowej sesji zacznij od: *„Przeczytaj `konkursy-ai-2026.md` i kontynuuj pracę nad [nazwa konkursu]"*.
3. Do każdego konkursu zakładaj osobny plik stanu, np. `arc-agi-3/STATUS.md`, z wypisanym: co już zrobione, wynik baseline'u, następny krok, deadline.

Bez punktu 3 stracisz więcej czasu na odtwarzanie kontekstu, niż zyskasz na równoległości.

---

*Dane na 10 X 2026. Liczby uczestników to rejestracje na Devpost — realna liczba submissionów jest zwykle 5–15% tej wartości. Przed zgłoszeniem sprawdź oficjalną stronę; organizatorzy przesuwają deadline'y (Agenthon już raz przesunął z 28 IX na 12 X).*
