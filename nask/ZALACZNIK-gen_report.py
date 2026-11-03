#!/usr/bin/env python3
"""
gen_report — generuje szablon zgłoszenia podatności pod hack.cert.pl.

Użycie:
    python3 python/gen_report.py \
        --program NASK \
        --title "IDOR w /api/v1/messages/{id} w mSzyfr" \
        --vuln-class 09 \
        --severity Wysoki \
        --poc poc.txt \
        --impact "Odczyt cudzych wiadomości i danych osobowych" \
        --remediation "Dodać walidację właściciela zasobu w endpointzie" \
        --output zgłoszenie.md

Plik wyjściowy można wypełnić i wysłać przez formularz na https://hack.cert.pl/.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "report.md"


def load_poc(source: str) -> str:
    if source == "-":
        return sys.stdin.read()
    return Path(source).read_text(encoding="utf-8")


def build_report(
    program: str,
    title: str,
    vuln_class: str,
    severity: str,
    poc: str,
    impact: str,
    remediation: str,
) -> str:
    return f"""# Zgłoszenie podatności — hack.cert.pl

## Program
{program}

## Tytuł
{title}

## Klasa podatności (z tabeli konkursu)
{vuln_class}

## Poziom krytyczności
{severity}

## Opis
Zgłoszona podatność w programie {program} na platformie hack.cert.pl.

## PoC (Proof of Concept) — kroki odtworzenia
{poc}

## Wpływ (impact)
{impact if impact else "Brak opisu wpływu."}

## Sugestia naprawy
{remediation if remediation else "Brak sugestii naprawy."}

## Oświadczenie
Oświadczam, że:
- testowałem wyłącznie w zakresie (scope) programu na hack.cert.pl,
- nie spowodowałem szkód w usługach ani nie przeprowadziłem ataku DoS,
- zachowam pełną dyskrecję do momentu wdrożenia poprawki przez administratorów,
- zgłoszenie zawiera prawdziwe, odtwórcze PoC.


"""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generuje szablon zgłoszenia podatności pod hack.cert.pl"
    )
    parser.add_argument("--program", required=True, help="NASK | CERT Polska | Gov.pl | mSzyfr | Gmina Władysławowo")
    parser.add_argument("--title", required=True, help="Tytuł zgłoszenia")
    parser.add_argument("--vuln-class", required=True, help="Klasa podatności (np. 09 IDOR)")
    parser.add_argument("--severity", required=True, help="Niski | Średni | Wysoki | Krytyczny")
    parser.add_argument("--poc", required=True, help="Ścieżka do pliku z PoC lub '-' dla stdin")
    parser.add_argument("--impact", default="", help="Opis wpływu luki")
    parser.add_argument("--remediation", default="", help="Sugestia naprawy")
    parser.add_argument("--output", default="zgłoszenie.md", help="Plik wyjściowy (domyślnie: zgłoszenie.md)")
    args = parser.parse_args()

    try:
        poc = load_poc(args.poc)
    except FileNotFoundError:
        print(f"błąd: nie znaleziono pliku PoC: {args.poc}", file=sys.stderr)
        return 1

    report = build_report(
        program=args.program,
        title=args.title,
        vuln_class=args.vuln_class,
        severity=args.severity,
        poc=poc,
        impact=args.impact,
        remediation=args.remediation,
    )

    Path(args.output).write_text(report, encoding="utf-8")
    print(f"[+] zapisano szablon zgłoszenia do: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
