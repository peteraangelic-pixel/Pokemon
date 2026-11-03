# Rekonesans NASK — dane zmierzone, 2026-11-03

Wszystko poniżej pochodzi z **własnych pomiarów**: Certificate Transparency (certspotter),
nagłówki HTTP, treść stron. Zero zgadywania. Liczba żądań do domen w zakresie: **204**
(limiter 4,5 req/s, regulamin dopuszcza 5).

---

## 1. Inwentarz 12 domen z zakresu (§5)

| domena | tier | HTTP | tech (z nagłówków) | wniosek |
|---|---:|---:|---|---|
| `nask.pl` | 1 | 302 | Azure CDN, `x-azure-ref`, `x-cache-info` | przekierowuje na www, statyczna |
| `dyzurnet.pl` | 1 | 200 | Cloudflare, `x-nextjs-cache` | aplikacja Next.js |
| `dns.pl` | 1 | 200 | własny stack, 1 cookie sesyjne | rejestr domen, wyszukiwarka |
| `oad.nask.pl` | 1 | 200 | Azure + Envoy + Next.js | aplikacja, Ośrodek Analizy Dezinformacji |
| `zglos-dezinformacje.nask.pl` | 1 | 200 | Next.js + Azure, **1 formularz** | **główny cel**: przyjmuje zgłoszenia |
| `bezpiecznymiesiac.pl` | 2 | 200 | Azure, 3 cookies | statyczna kampania |
| `secure.edu.pl` | 2 | **brak** | — | nie odpowiada po HTTPS — sprawdzić DNS |
| `bezpiecznewybory.pl` | 2 | **403** | WAF (custom, `x-iinfo`-like) | zablokowane dla nas, nie zablokowane dla przeglądarki |
| `116sos.pl` | 2 | 200 | Next.js + WordPress, 1 formularz | **dane wrażliwe** (zdrowie) |
| `pllum.org.pl` | 2 | 200 | Azure, Nuxt, 2 cookies | statyczna prezentacja modelu |
| `science.nask.pl` | 2 | 200 | Next.js + WordPress | CMS |
| `dataannotation.pllum.org.pl` | 2 | 200 | Azure + Envoy, SPA 713 B | **drugi cel**: HIVE — aplikacja do anotacji |

### Nagłówki — co zaobserwowano

```
x-azure-ref, x-cache, x-cache-info     → nask.pl, oad, zglos-dezinformacje, bezpiecznymiesiac, pllum, dataannotation
x-envoy-upstream-service-time          → oad, dataannotation  (Envoy = proxy przed aplikacją)
x-nextjs-cache, __NEXT_DATA__          → dyzurnet, oad, science, 116sos, zglos-dezinformacje
server: cloudflare                     → dyzurnet
server: AmazonS3 (403)                 → files.badanie.nask.pl  (poza zakresem)
x-xss-protection, x-frame-options      → ksod, certyfikacja, taskmanagement (poza zakresem)
```

**Wniosek architektoniczny:** prawie wszystko stoi za Azure Front Door + Envoy i jest
aplikacją Next.js. To znaczy, że logika dostępu żyje w **middleware po stronie Next.js**
oraz w API routes — a nie w klasycznym backendzie. To ukierunkowuje atak: poz. 9 (BAC),
poz. 12 (API), poz. 13 (mass assignment).

---

## 2. Wynik negatywny — i dlaczego jest wartościowy

Test 16 ścieżek ekspozycji × 12 domen = 192 żądania + 12 baseline'ów:

```
/.git/HEAD  /.env  /.env.local  /config.json  /backup.zip  /.svn/entries
/server-status  /actuator/env  /actuator/health  /.well-known/security.txt
/api/v1/users  /api/users  /api/v1/config  /graphql  /swagger.json  /openapi.json
```

**Wynik: zero realnych ekspozycji.** Każda ścieżka zwracała 200, ale była to strona
catch-all SPA (HTML, ~51 KB na dns.pl, ~30 KB na zglos-dezinformacje, 713 B na dataannotation).

### Dwie pułapki metodologiczne, które musiałem obejść

1. **Catch-all z wplecioną ścieżką.** `dns.pl` zwraca w canonicalu żądaną ścieżkę, więc
   `/.env` i `/.git/HEAD` dają różne odpowiedzi. Rozwiązanie: normalizacja — ścieżka
   zastępowana tokenem `PLACEHOLDER` przed hashowaniem.
2. **Rotujący token CSRF.** `zglos-dezinformacje` wstawia do HTML losowy token, więc każde
   dwa żądania różnią się o 1 znak. Rozwiązanie: zwijanie ciągów ≥16 znaków hex do `<HEX>`.

Dopiero po obu normalizacjach **i** po dodaniu twardej reguły „plik to nie HTML" wynik spadł
z 200 fałszywych trafień do zera.

**Wniosek: powierzchnia ataku nie jest w plikach konfiguracyjnych.** Nie tracić na to czasu.

---

## 3. Co jest poza zakresem, choć należy do NASK

Z Certificate Transparency dla `nask.pl` wyszło **108 nazw hostów**. Wypisane w §5 są **dwie**
(`nask.pl`, `oad.nask.pl`). Pozostałe 106 to systemy wewnętrzne i deweloperskie — **nie wolno ich testować**:

```
dev.ncp.ebsi, uat.ncp.ebsi, api-pilot.ebsi.node1/2, uself-keycloak.lspncp.ebsi
gitlab.snkom, nextcloud.snkom, chat.snkom, jitsi.snkom, auth.snkom, mx.snkom
zakupy, zamowienia, taskmanagement, ksod, certyfikacja, inwentaryzacja, secret.eadministracja
pigeon, smog, rd.variot, cs.pib, technologie, standard, ekspert, en
u1…u7 / u1b…u7b .pilot-dc4eu.ebsi, .pilot-vector.ebsi
```

Kilka z nich wygląda bardzo kusząco (`gitlab.snkom`, `secret.eadministracja`, `nextcloud.snkom`).
**Nie dotykamy.** Zakres konkursu to dokładnie lista z §5, a testowanie systemów poza zgodą
to nie „brak nagrody", tylko problem prawny. To jest najczęstszy sposób, w jaki ludzie
dyskwalifikują się w takich konkursach.

---

## 4. Tier-2 hosty spoza CT

Dla porządku: `dyzurnet.pl` ma `testowo.dyzurnet.pl` w CT — **poza zakresem**. `pllum.org.pl`
ma `dataannotation.pllum.org.pl` — **w zakresie** (wypisane wprost w §5).

---

## 5. Otwarte pytania do domknięcia w pierwszym dniu

| pytanie | jak sprawdzić | po co |
|---|---|---|
| Czy `secure.edu.pl` w ogóle żyje? | DNS A/AAAA + HTTP na 80 | jeśli nie żyje, wypada z planu |
| Czy `bezpiecznewybory.pl` blokuje tylko nasz UA? | przeglądarka + inny UA | WAF blokujący skanery to nie podatność |
| Czy na `zglos-dezinformacje` jest rejestracja czy tylko formularz? | wejść w przeglądarce | decyduje, czy IDOR jest w ogóle wykonalny |
| Czy HIVE (`dataannotation`) ma role? | rejestracja, dwa konta | to warunek całej ścieżki A |
| Jakie API woła SPA HIVE? | DevTools → Network, potem `naskrecon scan` na bundle | mapa endpointów |
