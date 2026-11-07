"""Write web/languages.json so the page can show the language list without a server
(VS Code Live Server, GitHub Pages preview).

Run after editing app/languages.py:

    python -m app.export_languages

A test fails if the file is out of date.
"""

from __future__ import annotations

import json
from pathlib import Path

from .languages import AUDIENCES, TONES, grouped_public

OUT = Path(__file__).resolve().parent.parent / "web" / "languages.json"


def payload(max_chars: int = 1000) -> dict:
    return {"groups": grouped_public(), "tones": list(TONES), "audiences": list(AUDIENCES), "max_chars": max_chars}


def render() -> str:
    return json.dumps(payload(), ensure_ascii=False, indent=1) + "\n"


def main() -> None:
    OUT.write_text(render(), encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
