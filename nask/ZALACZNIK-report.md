# Szablon zgłoszenia podatności — hack.cert.pl

Wypełnij wszystkie pola przed wysłaniem przez formularz na platformie.

---

## 1. Program (wybierz jeden)
- [ ] NASK (nask-pib)
- [ ] CERT Polska (cert-polska)
- [ ] Portal Gov.pl (centralny-osrodek-informatyki)
- [ ] mSzyfr (mszyfr)
- [ ] Gmina Władysławowo (cciod-wladyslawowo)

## 2. Tytuł zgłoszenia
Krótki, opisowy tytuł. Przykład: `IDOR w endpointzie /api/v1/messages/{id} umożliwia odczyt cudzych wiadomości w mSzyfr`

## 3. Opis podatności
Co możliwe jest dzięki tej luce? Jaki ma wpływ na poufność, integralność, dostępność?

Przykład:
> Endpoint `GET /api/v1/messages/{id}` w mSzyfr nie weryfikuje, czy zalogowany użytkownik jest właścicielem wiadomości o podanym ID. Dzięki temu zalogowany użytkownik może odczytać dowolną cudzą wiadomość, w tym dane osobowe i treści rozmów.

## 4. Klasa podatności (z tabeli konkursu)
- [ ] 01 Zdalne wykonanie kodu (RCE)
- [ ] 02 Pełne przejęcie konta
- [ ] 03 Dostęp do danych wrażliwych
- [ ] 04 SQL injection
- [ ] 05 SSRF
- [ ] 06 SSTI
- [ ] 07 File Upload
- [ ] 08 XSS
- [ ] 09 Autoryzacja i dostęp (IDOR)
- [ ] 10 Eskalacja uprawnień
- [ ] 11 Problemy z sesją i uwierzytelnianiem
- [ ] 12 Podatności w API
- [ ] 13 Mass Assignment
- [ ] 14 Błędna konfiguracja CORS
- [ ] 15 Path Traversal / LFI / RFI
- [ ] 16 CSRF
- [ ] 17 Open Redirect
- [ ] 18 Web Cache Poisoning
- [ ] 19 HTTP Request Smuggling
- [ ] 20 XXE

## 5. Poziom krytyczności (szacunkowy)
- [ ] Niski (600–4000 PLN)
- [ ] Średni (4000–9000 PLN)
- [ ] Wysoki (9000–20000 PLN)
- [ ] Krytyczny (20000 PLN)

## 6. PoC (Proof of Concept) — krok po kroku
Wymagane przez platformę. Opisz każdy krok, który prowadzi do odtworzenia błędu.

```
1. Wejdź na https://cel-w-scope.pl/
2. Załóż dwa konta testowe: A i B
3. Jako użytkownik A utwórz wiadomość, zapisz jej ID (np. 12345)
4. Jako użytkownik B wyślij żądanie:
   GET /api/v1/messages/12345
   Authorization: Bearer <token_użytkownika_B>
5. Odpowiedź zawiera treść wiadomości użytkownika A — B nie powinien mieć do niej dostępu.
```

Dołącz zrzuty ekranu, jeśli to możliwe.

## 7. Żądania HTTP (surowy request)
Wklej surowe żądania HTTP, które wykorzystują lukę.

```
GET /api/v1/messages/12345 HTTP/1.1
Host: cel-w-scope.pl
Authorization: Bearer <token>
Cookie: session=<session>
```

## 8. Wpływ (impact)
Co może zrobić atakujący dzięki tej luce? Na jakie dane ma dostęp? Czy może przejąć konto, wykonać kod, wyciągnąć bazę?

## 9. Sugestia naprawy (opcjonalnie)
Jak powinni naprawić tę lukę? (np. dodać walidację właściciela zasobu w endpointzie, użyć prepared statements, walidować typ pliku po stronie serwera)

## 10. Oświadczenie
Oświadczam, że:
- Testowałem wyłącznie w zakresie (scope) programu na hack.cert.pl
- Nie造成łam szkód w usługach, nie przeprowadziłem Ataku DoS
- Zachowam dyskrecję do momentu wdrożenia poprawki
- Zgłoszenie zawiera prawdziwe, odtwórcze PoC

---

## Nie dołączaj do zgłoszenia
- Danych osobowych innych użytkowników (oprócz własnych kont testowych)
- Poświadczeń do kont pracowników NASK/CERT
- Materiałów нарушаjących poufność innych osób
