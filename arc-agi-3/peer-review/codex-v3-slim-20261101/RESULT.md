# v3-slim: odrzucenie po ukończonym teście docelowym

Notebook petersharps/arc3-duck-codex-v3-slim-1101/1 zakończony COMPLETE. Publiczny smoke: **17.35047 / 24 ukończenia**, wobec kontroli **27.49667 / 33**. To nie wynik konkursowy. Kod zachowano bez zmian; brak rekomendacji submisji.

Ta sama lista10 gier i nominalny budżet48min/gra. Poziomy: tn36 3→1,m0r0 2→1,cn04 4→2,dc22 3→3,ka59 3→2,sc25 5→5,s5i5 5→2,ls20 3→3,su15 3→4,g50t 2→1. Brak nowych zer,ale6 gier straciło ukończenia. Grupy według zaobserwowanych w kontroli akcji także tracą: bez kierunkowych −4 poziomy,z kierunkowymi −5. To opis zachowania obserwowanego,nie klasy mechanik z kodu silnika.

ARC3_SMOKE_OK,crashed=[]. Sekcje rzeczywiście niesione w promptach wszystkich10 gier (ACTIVATION.json). Nie jest to nieaktywna ablacją. W logu1,752,216 wygenerowanych tokenów. Udział akcji na niedokończonych poziomach15.98%→34.14%. Liczba zaobserwowanych błędów w końcowych snapshotach25→10 NIE oznacza lepszego agenta: inny zachowany fragment rozmowy i mniej ukończeń.

Nie przypisujemy całego spadku jednej przyczynie: pojedyncze przebiegi nie rozdzielają wariancji od wpływu sekcji. Przykłady niesionych sekcji zawierają niezweryfikowane hipotezy,więc utrwalanie może zakotwiczać fałszywe przekonanie. Brak podstaw do promowania slim lub dalszego nakładania na niego pamięci.

Następna niezależna hipoteza: ograniczyć zakres retained functions do poziomu na dokładnej v3 z sekcjami OFF. W s5i5 helper run odczytywał stare kolory,powodując KeyError Y po przejściu. Sam błąd po ukończeniu nie odbiera zdobytego poziomu;nie stanowi dowodu przyczyny9 utraconych ukończeń. Upstream scope=levelup może ograniczyć przenoszenie nieaktualnego kodu,ale może też pogorszyć transfer użytecznych funkcji. Dlatego osobny test,jedna zmiana env,bez dziedziczenia wyniku slim.

Surowe dane: completed-download/submission-access-20261031/slim-target-output;collector41295604412. Odtworzenie porównania: summarize() z analysis/analyze_v137_smoke.py na obu benchmark.json;wynik COMPARISON.json. Diagnostyka błędów: python analysis/analyze_prompt_snapshots.py --prompts <output>/prompts --out <report>. Snapshoty są dolną granicą obserwacji,nie pełnymi logami wywołań.
