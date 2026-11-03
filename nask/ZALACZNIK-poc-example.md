# Przykład PoC — IDOR w mSzyfr (tylko ilustracja, nie jest to rzeczywista luka)

Ten przykład pokazuje, jak powinien wyglądać dobrze przygotowany PoC.
Nie testuj tego przeciwko systemom, do których nie masz zgody.

---

## Tytuł
IDOR w endpointzie `/api/v1/messages/{id}` umożliwia odczyt cudzych wiadomości

## Kroki odtworzenia
1. Zarejestruj dwa konta testowe w mSzyfr: `user-a@test.pl` i `user-b@test.pl`.
2. Zaloguj się jako `user-a`, wyślij wiadomość do `user-b` o treści "testowa wiadomość IDOR".
3. Złap żądanie w Burp Suite / zapisz ID wiadomości z odpowiedzi (np. `message_id: 98765`).
4. Wyloguj się, zaloguj jako `user-b`.
5. Wyślij żądanie:
   ```
   GET /api/v1/messages/98765 HTTP/1.1
   Host: mszyfr.gov.pl
   Authorization: Bearer <token_user_b>
   Cookie: session=<session_user_b>
   ```
6. Serwer odpowiada `200 OK` z treścią wiadomości wysłanej przez `user-a`.
7. Użytkownik `user-b` nie powinien mieć dostępu do wiadomości `user-a`.

## Dowód
Zrzut ekranu z narzędzia Burp Suite pokazujące żądanie i odpowiedź z treścią cudzej wiadomości.

## Wpływ
Każdy zalogowany użytkownik mSzyfr może odczytać dowolną cudzą wiadomość, w tym dane osobowe i poufne treści rozmów.

## Sugestia naprawy
W endpointzie `/api/v1/messages/{id}` dodać walidację, czy `user_id` z tokena sesji jest właścicielem wiadomości o podanym ID. Zwrócić `403 Forbidden` lub `404 Not Found`, jeśli nie jest.
