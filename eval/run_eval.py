"""Generate translations for native-speaker review and write them to a CSV.

Usage (from the repo root):

    python -m eval.run_eval --languages ha,ary,arz --out eval/review.csv
    python -m eval.run_eval --languages all --scripts both

Uses the real Claude engine if ANTHROPIC_API_KEY is set, otherwise the mock
engine (handy for checking the CSV layout without spending credits).

The CSV has empty 1-5 score columns for reviewers: meaning, tone, naturalness
and originality (does it sound like a person wrote it, not a translator).
The test sentences are synthetic, so storing them here is fine; never put real
user messages into this file.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import sys
from pathlib import Path

from app.engine import EngineError, MockEngine, Request, build_engine
from app.languages import PROFILES

HERE = Path(__file__).resolve().parent
SENTENCES = HERE / "sentences.json"

COLUMNS = [
    "row_id", "sentence_id", "category", "language_code", "language", "script", "tone", "audience",
    "source_text", "output", "ai_meaning_back", "ai_confidence", "ai_flags", "engine", "model",
    "score_meaning_1to5", "score_tone_1to5", "score_naturalness_1to5", "score_originality_1to5",
    "reviewer_better_version", "reviewer_notes", "reviewer_initials", "reviewer_region",
]

SCORING_GUIDE = (
    "Scores: 1 = wrong/unusable, 2 = poor, 3 = understandable but off, 4 = good, 5 = exactly what a native would send. "
    "Meaning = same message; Tone = right formality and warmth; Naturalness = no translated feel; "
    "Originality = sounds like a person from there wrote it, not a word-for-word rendering."
)


def load_sentences(path: Path = SENTENCES) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


async def run(languages: list[str], scripts: str, out: Path, engine=None, explain: bool = True) -> int:
    engine = engine or build_engine()
    sentences = load_sentences()
    rows = 0
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8-sig") as fh:  # BOM so Excel shows Arabic correctly
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        for code in languages:
            p = PROFILES[code]
            script_list = list(p.scripts) if scripts == "both" else [p.default_script]
            for script in script_list:
                for s in sentences:
                    req = Request(text=s["text"], profile=p, tone=s["tone"], script=script, audience=s["audience"])
                    try:
                        output = "".join([c async for c in engine.stream(req)])
                        info = await engine.explain(req, output) if explain else {}
                    except EngineError as exc:
                        output, info = f"ERROR: {exc}", {}
                    rows += 1
                    w.writerow({
                        "row_id": rows, "sentence_id": s["id"], "category": s["category"],
                        "language_code": code, "language": p.name, "script": script,
                        "tone": s["tone"], "audience": s["audience"], "source_text": s["text"], "output": output,
                        "ai_meaning_back": info.get("meaning_back", ""), "ai_confidence": info.get("confidence", ""),
                        "ai_flags": "; ".join(f"{f['phrase']}: {f['issue']}" for f in info.get("naturalness_flags", [])),
                        "engine": engine.name, "model": getattr(engine, "model", ""),
                    })
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--languages", default="all", help="Comma-separated codes or 'all'. Codes: " + ",".join(PROFILES))
    ap.add_argument("--scripts", choices=["default", "both"], default="default", help="'both' adds Latin-letter rows for Arabic dialects")
    ap.add_argument("--out", default=str(HERE / "review.csv"))
    ap.add_argument("--no-explain", action="store_true", help="Skip the AI meaning-back column (faster, cheaper)")
    ap.add_argument("--mock", action="store_true", help="Force the mock engine")
    args = ap.parse_args(argv)

    codes = list(PROFILES) if args.languages == "all" else [c.strip() for c in args.languages.split(",") if c.strip()]
    unknown = [c for c in codes if c not in PROFILES]
    if unknown:
        print(f"Unknown language code(s): {', '.join(unknown)}", file=sys.stderr)
        return 2
    engine = MockEngine(delay=0) if args.mock else None
    n = asyncio.run(run(codes, args.scripts, Path(args.out), engine=engine, explain=not args.no_explain))
    print(f"Wrote {n} rows to {args.out}")
    print(SCORING_GUIDE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
