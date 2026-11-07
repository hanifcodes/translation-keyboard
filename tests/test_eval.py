import asyncio
import csv
from collections import Counter

from app.engine import MockEngine
from eval.run_eval import COLUMNS, load_sentences, main, run


def test_thirty_diverse_sentences():
    s = load_sentences()
    assert len(s) == 30
    assert len({x["id"] for x in s}) == 30
    cats = Counter(x["category"] for x in s)
    for needed in ["greeting", "condolence", "business request", "joke", "apology"]:
        assert cats[needed] >= 2, needed
    assert {x["tone"] for x in s} == {"casual", "friendly", "formal", "playful"}


def test_eval_writes_review_csv(tmp_path):
    out = tmp_path / "review.csv"
    n = asyncio.run(run(["ha", "ary"], "both", out, engine=MockEngine(delay=0)))
    assert n == 30 * (1 + 2)  # Hausa: latin only; Darija: arabic + latin
    with out.open(encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    assert list(rows[0]) == COLUMNS
    for col in ["score_meaning_1to5", "score_tone_1to5", "score_naturalness_1to5", "score_originality_1to5"]:
        assert all(r[col] == "" for r in rows)
    assert {r["script"] for r in rows if r["language_code"] == "ary"} == {"arabic", "latin"}
    assert all(r["output"] for r in rows)


def test_eval_cli_rejects_unknown_language(capsys):
    assert main(["--languages", "xx", "--mock"]) == 2


def test_eval_cli_mock(tmp_path):
    out = tmp_path / "r.csv"
    assert main(["--languages", "fr", "--mock", "--no-explain", "--out", str(out)]) == 0
    assert out.exists()
