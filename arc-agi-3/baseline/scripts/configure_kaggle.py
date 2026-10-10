"""Create a project-local Kaggle token file without printing its contents.

The official ARC starter uses ``.kaggle/access_token`` and the modern Kaggle
CLI reads it through ``KAGGLE_API_TOKEN``. For this checkout, the user-owned
root ``kaggle.json`` is the local source credential and is already ignored by
Git. This script copies only its token to the ARC project's ignored location.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
DEFAULT_SOURCE = REPO_ROOT / "kaggle.json"
DEFAULT_DESTINATION = ROOT / ".kaggle" / "access_token"


def configure(source: Path, destination: Path, *, force: bool = False) -> None:
    if not source.is_file():
        raise SystemExit(f"Credential source does not exist: {source}")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Credential source is not valid JSON: {exc}") from exc

    token = payload.get("key")
    if not isinstance(token, str) or not token.strip():
        raise SystemExit("Credential source has no non-empty 'key' field.")

    if destination.exists() and not force:
        raise SystemExit(
            f"Refusing to overwrite existing {destination}. Use --force to replace it."
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(token.strip() + "\n", encoding="utf-8")
    os.chmod(destination, 0o600)
    print(f"Wrote ignored local token file: {destination.relative_to(REPO_ROOT)} (mode 600).")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--destination", type=Path, default=DEFAULT_DESTINATION)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    configure(args.source.resolve(), args.destination.resolve(), force=args.force)


if __name__ == "__main__":
    main()
