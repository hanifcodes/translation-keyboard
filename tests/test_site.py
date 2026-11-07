"""Static-hosting checks (GitHub Pages / Live Server)."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_root_index_redirects_to_app_for_github_pages():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    assert 'http-equiv="refresh"' in html and 'url=web/' in html
    assert (ROOT / ".nojekyll").exists()


def test_config_ships_without_a_server_address_or_key():
    js = (ROOT / "web" / "config.js").read_text(encoding="utf-8")
    assert re.search(r'apiBase:\s*""', js), "keep apiBase empty in the repo; users set their own Render URL"
    assert "sk-ant" not in js


def test_app_waits_for_sleeping_server():
    js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
    assert "90000" in js and "wake up" in js
