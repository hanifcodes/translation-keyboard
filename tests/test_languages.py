import unicodedata

import pytest

from app.languages import ARABIC, LATIN, PROFILES, REGION_ORDER, TONES, grouped_public

REQUIRED = ["ha", "ary", "arz", "ar-SA", "apc", "yo", "ig", "pcm", "sw", "fr"]
ARABIC_DIALECTS = ["ary", "arz", "ar-SA", "apc"]


def test_all_requested_languages_exist():
    assert set(REQUIRED) <= set(PROFILES)


@pytest.mark.parametrize("code", sorted(PROFILES))
def test_profile_is_complete(code):
    p = PROFILES[code]
    assert p.needs_native_review is True, "every profile stays flagged until natives sign off"
    assert p.region in REGION_ORDER
    assert len(p.greetings) >= 3
    assert len(p.politeness) >= 3
    assert len(p.idioms) >= 3
    assert len(p.avoid) >= 3
    assert len(p.examples) == 3
    assert p.weak_spots.strip()
    assert p.resource_level in {"lower", "higher"}
    assert p.default_script in p.scripts
    for e in p.examples:
        assert e.source and e.target and e.note
        assert e.source != e.target


@pytest.mark.parametrize("code", ARABIC_DIALECTS)
def test_arabic_dialects_offer_both_scripts_and_rtl(code):
    p = PROFILES[code]
    assert set(p.scripts) == {ARABIC, LATIN}
    assert p.direction(ARABIC) == "rtl"
    assert p.direction(LATIN) == "ltr"
    assert p.lang_tag(LATIN).endswith("-Latn")
    assert p.latin_conventions
    for e in p.examples:
        assert any(unicodedata.bidirectional(ch) == "AL" for ch in e.target), "Arabic-script example expected"
        assert e.target_latin, "Latin-letter example expected"
        assert not any(unicodedata.bidirectional(ch) == "AL" for ch in e.target_latin)


def test_arabic_dialect_examples_differ():
    """The same English idea must come out differently per dialect."""
    greetings = {c: PROFILES[c].examples[0].target for c in ARABIC_DIALECTS}
    assert len(set(greetings.values())) == len(greetings)


def test_lower_resource_languages_are_labelled():
    for code in ["ha", "yo", "ig", "pcm", "ary"]:
        assert PROFILES[code].resource_level == "lower"


def test_grouped_public_is_safe_and_ordered():
    groups = grouped_public()
    regions = [g["region"] for g in groups]
    assert regions == [r for r in REGION_ORDER if r in regions]
    for g in groups:
        for lang in g["languages"]:
            assert "examples" not in lang and "idioms" not in lang
            assert lang["needs_native_review"] is True


def test_tones():
    assert list(TONES) == ["casual", "friendly", "formal", "playful"]


def test_static_languages_json_is_up_to_date():
    """web/languages.json powers Preview mode (Live Server / GitHub Pages)."""
    from pathlib import Path

    from app.export_languages import render

    path = Path(__file__).resolve().parent.parent / "web" / "languages.json"
    assert path.read_text(encoding="utf-8") == render(), "run: python -m app.export_languages"


def test_page_uses_relative_asset_paths():
    """Absolute paths like /app.js break under Live Server and GitHub Pages project sites."""
    import re
    from pathlib import Path

    html = (Path(__file__).resolve().parent.parent / "web" / "index.html").read_text(encoding="utf-8")
    srcs = re.findall(r'<script[^>]*src="([^"]+)"', html)
    assert srcs == ["config.js", "app.js"]
