# Regulamin konkursu — wyciąg z PDF (11 stron)

Źródło: `https://hack.cert.pl/api/v1/public/institutions/nask-pib/programs/nask/editions/1/terms/download`
„Regulamin Konkursu Bug Bounty NASK, edycja 11/2026".

---

## §3 Czas trwania
**3.11.2026 – 30.11.2026.**

## §4 Uczestnicy
- Każdy użytkownik platformy hack.cert.pl.
- Wymagane: **ukończone 18 lat** i **polska rezydencja podatkowa**.
- Wykluczeni: pracownicy i współpracownicy NASK oraz ich najbliższa rodzina.

## §5 Zakres systemów — DOKŁADNA LISTA

| Tier 1 | Tier 2 |
|---|---|
| `nask.pl` | `bezpiecznymiesiac.pl` |
| `dyzurnet.pl` | `secure.edu.pl` |
| `dns.pl` | `bezpiecznewybory.pl` |
| `oad.nask.pl` | `116sos.pl` |
| `zglos-dezinformacje.nask.pl` | `pllum.org.pl` |
| | `science.nask.pl` |
| | `dataannotation.pllum.org.pl` |

Dodatkowo (§5 pkt 2): tylko systemy **dostępne bezpośrednio z internetu**, bez VPN
i bez kont domenowych NASK.

## §6 Zasady testowania
1. Testy bez uwierzytelnienia albo **wyłącznie z własnych kont** (poza kontami domenowymi)
   lub kont testowych. Nie wolno używać kont innych użytkowników.
2. Automatyczne narzędzia: **maksymalnie 5 req/s**.
3. Naruszenie → odrzucenie zgłoszenia.

## §7 Nagrody

| Tier | Niska (0.1–3.9) | Średnia (4.0–6.9) | Wysoka (7.0–8.9) | Krytyczna (9.0–10.0) |
|---|---:|---:|---:|---:|
| **Tier 1** | 600 zł | 4 000 zł | 9 000 zł | **20 000 zł** |
| **Tier 2** | 300 zł | 2 000 zł | 4 500 zł | **10 000 zł** |

Krytyczność wg **CVSS 4.0**. Pula: **100 000 zł** (może wzrosnąć).

Pozostałe punkty, które zmieniają sposób pracy:
- **pkt 5:** zgłoszenia rozpatrywane **sukcesywnie**, zwycięzcy ogłaszani **w trakcie** konkursu
  → nie czekamy z raportem do końca miesiąca.
- **pkt 8:** przy duplikacie decyduje **data i godzina** pierwszego poprawnego zgłoszenia.
- **pkt 9:** ta sama przyczyna źródłowa w różnych serwisach = **jedna podatność**.
- **pkt 10:** do nagrody dodawana jest równowartość podatku zryczałtowanego — NASK odprowadza go sam.
- **pkt 12:** wypłata do 60 dni od ogłoszenia wyników.
- **pkt 13:** zwycięzcy wyłaniani do 30 dni po zakończeniu edycji.

## §8 Typy podatności objęte konkursem (skrót)

1. **RCE** — zdalne wykonanie kodu, eskalacja do kontroli nad systemem
2. **Pełne przejęcie konta** — reset bez dostępu do skrzynki, przejęcie sesji/tokenów,
   logowanie bez hasła, fałszowanie tożsamości
3. **Dostęp do danych wrażliwych** — wyciek danych osobowych, cudze treści, masowy odczyt
4. **SQL injection**
5. **SSRF** — odczyt zasobów z sieci wewnętrznej, dostęp do usług prywatnych, SSRF→RCE
   *(blind SSRF z samym DNS jest WYKLUCZONY)*
6. **SSTI** — wykonanie kodu przez silnik szablonów
7. **File upload** — prowadzący do RCE, obejście MIME/rozszerzeń, obejście walidacji z realnym skutkiem
8. **XSS** — poza wyłączeniami (self-XSS i content injection bez JS są wykluczone)
9. **Autoryzacja i dostęp** — IDOR/BAC, odczyt/modyfikacja/usuwanie cudzych danych,
   **omijanie autoryzacji w warstwie aplikacji (UI/Web)**
10. **Eskalacja uprawnień** — pionowa i pozioma
11. **Sesja i uwierzytelnianie** (bez pełnego przejęcia) — *nagradzane nisko*
12. **API** — omijanie autoryzacji, dostęp do ukrytych endpointów
13. **Mass assignment** — nadpisanie pól typu `role=admin`
14. **Błędna konfiguracja CORS** — tylko gdy pozwala czytać dane lub wykonywać akcje
15. **Path traversal / LFI / RFI**
16. **CSRF z realnym wpływem** — zmiana danych lub stanu konta
17. **Open redirect** — tylko w przepływie OAuth/OIDC, w udokumentowanym łańcuchu lub z HTML injection
18. **Web cache poisoning** i nieautoryzowana modyfikacja treści serwowanych innym
19. **HTTP request smuggling** (CL.TE, TE.CL, TE.TE) — przechwycenie żądań, obejście WAF, dostęp do wewnętrznych endpointów
20. **XXE** — odczyt plików, SSRF, RCE

## §8 Wyłączenia — czego NIE zgłaszać (skrót)

- **Wycieki bez wpływu:** stack trace, wersje oprogramowania, IP, ścieżki, listingi katalogów,
  user enumeration, metadane, autocomplete, publiczne endpointy debugowe bez eskalacji.
- **Konfiguracja bez wektora ataku:** brak nagłówków bezpieczeństwa, HSTS, captcha, flagi cookies,
  SPF/DKIM/DMARC bez spoofingu, wygasłe certyfikaty, otwarty port bez znaczenia,
  nieaktualne biblioteki bez wpływu, **znane CVE bez działającego PoC**.
- **Nierealne założenia:** MITM, fizyczny dostęp, DevTools, archaiczne przeglądarki.
- **Frontend bez wpływu:** self-XSS, tabnabbing, content injection bez kodu, clickjacking bez
  krytycznej akcji, czysty HTML injection.
- **CSRF** bez wpływu na integralność/poufność/dostępność; logout; read-only.
- **Blind SSRF** z dowodem tylko DNS.
- **DoS i testy obciążeniowe — WSZYSTKIE FORMY ZABRONIONE.**
- **Brak rate limitingu** bez realnego scenariusza ataku.
- **Subdomain takeover** bez działającego PoC.
- **Klucze API** bez możliwości nadużycia lub z restrykcjami domenowymi.
- **Social engineering, phishing.**
- **Scenariusze teoretyczne bez PoC.** „Potencjalne" ataki bez ścieżki wykonania.
- **Raporty z automatycznych skanerów bez ręcznego potwierdzenia.**
- Literówki, layout, komunikaty błędów.

---

**Najważniejszy wniosek z §8:** lista wyłączeń jest dłuższa niż lista tego, co płaci.
Konkurs karze „znalazłem 50 błędów konfiguracji" i nagradza **jeden działający łańcuch ataku**.
