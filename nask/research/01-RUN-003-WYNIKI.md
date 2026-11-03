# Przebieg 003 — wyniki rozpoznania (2026-11-03)

Run: [41711039489](https://github.com/peteraangelic-pixel/Pokemon/actions/runs/41711039489),
commit `5103587`, dane: `nask/reports/index-run003.json` (183 KB) i
`nask/reports/analysis-run003.json` (1,9 MB).

**Potwierdzone podatności: 0.** Ten dokument opisuje wyłącznie zaobserwowane
zachowanie publicznych serwisów i wynikającą z niego kolejność pracy.

## 1. Co faktycznie odpowiedziało

479 żądań w 134 s przy 4 req/s (limit programu: 5). 414 odpowiedzi < 400.

| host | ok/zadane | statusy | uwaga |
|---|---:|---|---|
| `dns.pl` | 108/111 | 200, 307, 404 | największa powierzchnia: 10 005 literalów tras |
| `pllum.org.pl` | 48/52 | 200, 404 | Nuxt |
| `116sos.pl` | 45/48 | 200, 404 | Next.js + WordPress |
| `dyzurnet.pl` | 45/46 | 200, 307, 404 | Cloudflare |
| `oad.nask.pl` | 42/46 | 200, 404 | Next.js, 1 746 literalów |
| `bezpiecznymiesiac.pl` | 41/46 | 200, 308, 404 | Next.js + WP |
| `science.nask.pl` | 38/41 | 200, 308, 404 | Next.js + WP |
| `zglos-dezinformacje.nask.pl` | 25/27 | 200, **500** | **2 × 500** |
| `dataannotation.pllum.org.pl` | 11/11 | 200 | SPA, **wszystko 200** (catch-all) |
| `nask.pl` | 9/9 | 302 | przekierowanie na `www.` |
| `www.nask.pl` | 2/2 | 200 | |
| `bezpiecznewybory.pl` | **0/34** | 403 | WAF blokuje |
| `secure.edu.pl` | **0/6** | brak odp. | DNS/HTTPS nie odpowiada |

## 2. Trzy obserwacje, które zmieniają plan

**(a) `zglos-dezinformacje.nask.pl` zwraca 500 na każdą nieznaną ścieżkę.**
Nie 404 — stronę błędu („This page couldn't load… ERROR 258337316"), także dla
`/.well-known/security.txt` i `/manifest.json`. To nie podatność: komunikaty
błędów są wprost wyłączone z konkursu. Ale to znaczy, że **kod 500 nic tu nie
znaczy** i że mapa tej aplikacji musi być robiona inaczej niż statusami.

**(b) `dataannotation.pllum.org.pl` (HIVE) zwraca 200 + HTML na wszystko.**
Wszystkie 11 „sukcesów" to ten sam shell SPA, nie pliki. Bez odejmowania
catch-all (żądanie na losową, nieistniejącą ścieżkę jako wzorzec) każdy skan
tego hosta da 100% fałszywych trafień. To poprawka do narzędzia, nie podatność.

**(c) `bezpiecznewybory.pl` i `secure.edu.pl` są w zakresie, ale niedostępne**
dla automatycznego klienta: 403 z WAF i brak odpowiedzi transportowej. Nie
twierdzimy, że nie mają podatności — twierdzimy, że ta metoda ich nie widzi.

## 3. Formularz zgłoszenia dezinformacji — dokładny kształt (z publicznego bundle'a)

`POST /api/sendForm`, `multipart/form-data`, pola:

| pole | wymagane | uwaga |
|---|---|---|
| `accept` | tak | musi być niepuste |
| `email` | nie | walidacja formatu po stronie klienta |
| `file` | nie | klient przepuszcza `image/png`, `image/jpeg`, ≤ 20 MB |
| `reason` | nie | ≤ 250 znaków |
| `urls` | tak | **do 50 linków, po jednym w linii** |
| `g-recaptcha-response` | tak | **reCAPTCHA v3** |

**Konsekwencja:** formularza **nie da się przetestować automatem** — reCAPTCHA
v3 jest wykonywana w przeglądarce i jej brak kończy żądanie przed wysłaniem
(`executeRecaptcha is not ready`). Każdy test wysyłki (np. hipoteza SSRF przez
pole `urls`) wymaga człowieka w przeglądarce. Narzędzie może przygotować
payload, nie może go wysłać.

## 4. Mapa HIVE (dataannotation) z bundle'a

Trasy widoczne w kodzie klienta: `/admin`, `/admin/logs`, `/annotators`,
`/account`, `/forgot-password`, `/basic-info`, `/conversation`, `/projects`,
`/edit`, baza API `https://dataannotation.pllum.org.pl/api/v1`.

To **mapa funkcji, nie dowód luki** — istnienie trasy `/admin` w bundlu mówi
tylko, że interfejs powstał. Czy serwer sprawdza rolę, rozstrzyga dopiero
porównanie dwóch własnych kont.

## 5. Co dalej

1. **Poprawka narzędzia:** odejmowanie catch-all względem losowej ścieżki
   (konieczne dla HIVE i `zglos-dezinformacje`).
2. **Kolejny przebieg:** więcej assetów na hosta (limit 40 → 120) i głębokość 2,
   żeby dociągnąć bundle, w których siedzą wywołania API.
3. **Praca człowieka (nie da się zastąpić):** założenie własnych kont w HIVE
   i przejście `/admin` oraz `/api/v1` z dwóch sesji; ręczna wysyłka formularza
   z linkiem do własnego serwera kontrolnego.
