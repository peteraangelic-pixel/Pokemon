# Weryfikacja benchmark v2.4 REAL (c87 9611889) — 2026-10-21

Trzecia iteracja po audytach. Pomiary u nas (sandbox 2 rdzenie, v67):

- Phase1 FFI: REAL, spójna z serią (~75 gier/s).
- Phase1b Rust: parser nadal zwraca **total=0 / gps=0.0**, chociaz
  gauntlet biegnie. Regex dalej zakłada format "36W-8L", a binarka
  wypisuje "Overall: 0.818 (36-8 d0)". Jedyna faza, ktorej fix sie
  nie powiodl — do naprawy: parsować "(\d+)-(\d+)" po "Overall:".
- Phase2 liga: dziala (u nas 3/4 pilotow; v80 tylko na c87).
- Phase3 belief Judge: próżnia naprawiona (opp=YumeNeko z Fez):
  fez_detections=1445 stanow/20 gier. Ale judge_plays=0 z konstrukcji:
  pilot v67 gra talia trolley BEZ Judge (1213), wiec metryka ma sens
  tylko dla agenta z Judge w talii (ich v85); mianowniki to decyzje,
  nie gry.
- Phase4 transformer: warstwy REAL (petla po L): D256/L4 11.45 ms,
  D512/L8 50.24 ms na forward (NumPy CPU). Etykieta FFN2048 przy
  FFN=1024 w kodzie — kosmetyka. Najlepszy proxy z dotychczasowych.
- Phase5: uczciwa etykieta "game generation only" (74.2 gier/s),
  nota o BENCH_PC — OK.
- Phase6 ablacja: seat swap OK, lecz (1) na naszym drzewie CRASH
  FileNotFoundError — twarda zaleznosc od agentow tylko z c87
  (v80/v81/v85) bez straznika istnienia, ubija caly tryb "all";
  (2) "ablacja" v81 vs v67 to NIE jeden wlacznik: v81 = v79 + soft
  lethal + mask + Judge/Boss anti-Fez (inna baza niz v67), wiec delta
  nie izoluje samego lethal. Prawdziwa ablacj wymaga tego samego
  agenta z flaga env lethal on/off.

Werdykt: v2.4 najlepszy z serii (4/5 fixow realnych), lecz parser 1b
nadal zwraca zero, faza 6 zawiesza sie poza c87, a jej wniosek
"lethal wl/wyl" jest metodologicznie przesadzony.
