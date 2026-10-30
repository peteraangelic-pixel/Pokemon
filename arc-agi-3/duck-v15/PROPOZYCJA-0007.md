# PROPOZYCJA 0007 — eskalacja względem ludzkiego baseline'u

**Status: szkic, NIE shipping.** Nie dołączyłem tego jako `.patch`, bo nie mam r033, na którym
mógłbym sprawdzić `git apply`. Patch, który nie wchodzi, zabija cały notebook — ryzyko większe
niż zysk. To jest instrukcja dla was, z jednoznacznym kryterium weryfikacji.

## Problem

`ESCALATE_ACTIONS` jest **absolutne**: dyrektywa odpala co N akcji na poziomie, niezależnie od
tego, ile akcji ten poziom wymaga. Zmierzone na r085 (32 ukończone poziomy, patrz
`ARC3/local-lab/escalation_audit.py`):

| próg | wstrzyknięć | % puli gry | odpala przed ludzkim baseline'em |
|---|---|---|---|
| 10 | 154 | 15,3% | 31/32 |
| 20 (v14) | 60 | 6,0% | ~25/32 |
| 60 | 12 | 1,2% | 7/32 |
| `max(20, 1,2 × baseline[poziom])` | **8** | **0,8%** | **0/32** |

Czyli: przy progu absolutnym prawie każda zachęta trafia na poziom, na którym agent jest
w normie. Przy progu względnym wszystkie 8 trafia tam, gdzie run realnie traci punkty
(`ls20/2` 175 vs 123, `ls20/3` 222 vs 73, `ka59/4` 69 vs 51, `dc22/2` 131 vs 102, …).

## Szkic zmiany

Miejsce: `inference/agent/tool_agent.py`, `class ToolAgent`, metoda budująca dodatkowe
dyrektywy — blok dodany przez patch 0005:

```python
        escalate_every = _escalate_actions()
        if escalate_every and _plan_commit_enabled():
            on_level = max(0, int(action_num or 0) - int(self._actions_at_level_start or 0))
            if on_level >= escalate_every * (self._arc3_escalations_on_level + 1):
                self._arc3_escalations_on_level = on_level // escalate_every
                lines.append(plan_escalation_prompt(int(current_level or 1), on_level))
```

Zamienić na (uwaga: nazwę atrybutu z baseline'em trzeba **potwierdzić w r033** — w `GameRun`
to `base_actions_per_level`, ale nie wiem, jak `ToolAgent` się do niego dostaje):

```python
        escalate_every = _escalate_actions()
        if escalate_every and _plan_commit_enabled():
            on_level = max(0, int(action_num or 0) - int(self._actions_at_level_start or 0))
            escalate_at = escalate_every
            try:
                _base = list(getattr(self.game_run, "base_actions_per_level", None) or [])
                _i = int(current_level or 1) - 1
                if 0 <= _i < len(_base):
                    _rate = float(os.environ.get("ARC3_ESCALATE_RATE") or 1.2)
                    escalate_at = max(escalate_every, int(float(_base[_i]) * _rate))
            except Exception:
                escalate_at = escalate_every          # brak baseline'u -> zachowanie jak dziś
            _cap = _get_env_int("ARC3_ESCALATE_MAX_PER_LEVEL", 2)
            if _cap and self._arc3_escalations_on_level >= _cap:
                escalate_at = 0                        # poziom oporny: 2 zachęty i cisza
            if escalate_at and on_level >= escalate_at * (self._arc3_escalations_on_level + 1):
                self._arc3_escalations_on_level = on_level // escalate_at
                lines.append(plan_escalation_prompt(int(current_level or 1), on_level))
```

Dwie nowe zmienne środowiskowe: `ARC3_ESCALATE_RATE` (domyślnie 1,2) i
`ARC3_ESCALATE_MAX_PER_LEVEL` (domyślnie 2). Przy braku baseline'u kod zachowuje się **jak
dziś**, więc patch jest bezpieczny, gdyby pole było `None`.

## Jak to zweryfikować u was (5 minut, bez GPU)

```bash
# 1. patch wchodzi na czysty r033
git apply --check -v patches/0007-escalate-relative.patch

# 2. ich własna weryfikacja łańcucha
python3 tools/verify_v13.py          # oczekiwane 7/7 patchy

# 3. logika progu bez scaffoldu (u mnie, test na stubie)
cd ARC3/local-lab && python3 escalation_audit.py r085-benchmark.json --rate 1.2
```

## Czego ten szkic nie rozstrzyga

Czy `ToolAgent` widzi `GameRun`. Jeśli nie — trzeba dodać pole w konstruktorze (jak
`_arc3_escalations_on_level` w 0005) i to już jest większa zmiana niż jeden hunk.
Wtedy prościej: zostaw próg absolutny 20 z v14 i zajmij się `commit(plan)`, bo tam leży
mnożnik akcji, a nie oszczędność tokenów.
