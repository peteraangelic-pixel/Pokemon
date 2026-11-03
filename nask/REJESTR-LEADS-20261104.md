# Rejestr leadów + log żądań (noc 3/4.11.2026) — dowód zgodności

**Zasada rejestru:** lead żyje tylko z nazwaną klasą z regulaminu i planem PoC na własnych
kontach. Wszystko, co poniżej oznaczone WYKLUCZONE, **nie idzie do zgłoszenia** (regulamin §8).
**Brak w tym pliku działających payloadów do czegokolwiek pozytywnego — bo pozytywnych nie ma.**

## Log żądań wysłanych w nocy (wszystkie: GET, bez uwierzytelnienia, sekwencyjne ≪ 5 req/s, tylko §5)

| # | żądanie | wynik | wniosek |
|---:|---|---|---|
| 1 | `zglos-dezinformacje.nask.pl/` | 200 | formularz: e-mail opcjonalny, ≤50 linków, 250 znaków, **załącznik .png/.jpg ≤20 MB** (powierzchnia klasy 7) |
| 2 | `dataannotation.pllum.org.pl/` | 302→`/login` | HIVE = SPA z logowaniem; publiczne: login + forgot-password |
| 3 | `dyzurnet.pl/` | 200 | CMS publiczny; media `/media/2026/…` (listingi WYKLUCZONE) |
| 4 | `dataannotation.pllum.org.pl/forgot-password` | 200 | formularz resetu (klasa 2 do testu rano na własnym koncie) |
| 5 | `dns.pl/` | 200 | Drupal; whois publiczny z definicji; `sites/default/files/` publiczne |
| 6 | `oad.nask.pl/` | 200 | **odkrycie powierzchni:** `/podglad-pdf?url=<ścieżka>` przy każdej publikacji |
| 7 | `science.nask.pl/wp-json/` | 404 | WP REST niewystawione (Next shell) → martwe |
| 8 | `oad.nask.pl/podglad-pdf?url=<legalny PDF z /media/>` | 200 | powłoka viewera „Ładowanie PDF…" |
| 9 | `oad.nask.pl/podglad-pdf?url=/media/…/nie_istnieje.pdf` | 200 | walidacja **tylko prefiksu** `/media/`, pobranie leniwe/klienckie |
| 10 | `oad.nask.pl/podglad-pdf?url=/etc/passwd` | **500** | poza prefiksem = nieobsłużony wyjątek, **bez danych** |
| 11 | `oad.nask.pl/podglad-pdf?url=http://169.254.169.254/metadata/…` | **500** | **brak odczytu SSRF** (metadata nie wraca) |
| 12 | `oad.nask.pl/podglad-pdf?url=https://example.com/x.pdf` | **500** | brak fetcha zewnętrznego po stronie serwera |

**Suma: 12 żądań, 0 zmian stanu, 0 hostów spoza §5, 0 payloadów niszczących.**

## Leady

| id | cel | klasa regulaminu | status | plan |
|---|---|---|---|---|
| L1 | HIVE | 9.1–9.3, 12.1–12.2, 13 | **AKTYWNY** | runbook L1 (dwa własne konta, canary) |
| L2 | HIVE reset | 2.1–2.3 | **AKTYWNY** | runbook L2 (token w query? jednorazowość? rotacja sesji?) |
| L3 | zglos-dezinformacje | 7 (upload ze skutkiem), 5 (SSRF **tylko z odczytem reflektywnym**) | **AKTYWNY** | runbook L3; najpierw sprawdzić, czy UI robi podgląd linku |
| L4 | 116sos / science / dyzurnet | 3.1/3.3 (dane wrażliwe), 12.2 | **AKTYWNY (niski priorytet)** | runbook L4; science już martwe (404) |
| L5 | dns.pl | 3.3 / 12.2 | **AKTYWNY (niski)** | runbook L5 z baseline'em catch-all |
| L6 | oad `/podglad-pdf` | 5 / 15 | **MARTWY (dowód: wiersze 8–12 logu)** | nie testować ponownie; 500 bez danych = klasa wykluczona |

## Wprost WYKLUCZONE z nagród (nie zgłaszamy, żeby nie palić reputacji zgłoszeń)

brak nagłówków/HSTS/captchy/flag cookie · mixed content · SPF/DKIM/DMARC bez spoofingu ·
TLS bez scenariusza · wersje/ścieżki/IP/stack trace/listingi katalogów · user enumeration ·
autocomplete · publiczne endpointy debug bez eskalacji · CVE bez PoC · MITM/fizyczny/DevTools ·
self-XSS · tabnabbing · clickjacking bez krytycznej akcji · czysty HTML injection ·
CSRF bez wpływu na stan · **blind SSRF z samym DNS** · open redirect bez scenariusza ·
DoS i testy obciążeniowe (**dyskwalifikacja**) · brak rate-limitu bez scenariusza ·
subdomain takeover bez PoC · błędy UX/literówki · **raporty z samych skanerów**.

## Kalibracja (podtrzymana)

typowo 600–4 000 zł · IDOR z realnym odczytem = 9 000 zł · masowy odczyt/przejęcie = 20 000 zł ·
ta sama przyczyna na dwóch hostach = **jedna** nagroda · duplikat = zero · wysyłka natychmiast po PoC.
