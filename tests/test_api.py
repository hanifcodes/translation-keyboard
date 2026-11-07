"""HTTP-level tests. Need fastapi and httpx (installed from requirements.txt)."""

import json
import logging
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from app import security  # noqa: E402
from app.engine import EngineError, MockEngine  # noqa: E402
from app.main import Settings, create_app  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CODE = "test-code-7f3a9"
SECRET_TEXT = "my private message 4821"


def make(codes=(CODE,), engine=None, **limits):
    s = Settings(access_codes=tuple(codes), max_chars=200, limits=security.Limits(**limits))
    return TestClient(create_app(s, engine or MockEngine(delay=0)))


def events(resp):
    return [json.loads(line) for line in resp.text.splitlines() if line.strip()]


def body(**kw):
    return {"text": "Good morning", "language": "ary", "tone": "friendly", **kw}


def test_index_and_js_served_with_security_headers():
    c = make()
    r = c.get("/")
    assert r.status_code == 200 and "Translation Keyboard" in r.text
    assert "script-src 'self'" in r.headers["content-security-policy"]
    assert r.headers["x-frame-options"] == "DENY"
    assert c.get("/app.js").status_code == 200


def test_health_and_languages():
    c = make()
    h = c.get("/api/health").json()
    assert h == {"status": "ok", "engine": "mock", "access_required": True}
    langs = c.get("/api/languages").json()
    codes = {lang["code"] for g in langs["groups"] for lang in g["languages"]}
    assert {"ha", "ary", "arz", "ar-SA", "apc", "yo", "ig", "pcm", "sw", "fr"} <= codes
    assert c.get("/api/languages").headers["cache-control"] == "no-store"


def test_access_code_required():
    c = make()
    assert c.post("/api/translate", json=body()).status_code == 401
    assert c.post("/api/translate", json=body(), headers={"X-Access-Code": "wrong"}).status_code == 401
    r = c.post("/api/translate", json=body(), headers={"X-Access-Code": CODE})
    assert r.status_code == 200


def test_unlock_and_lockout():
    c = make(failed_codes_per_ip=3)
    assert c.post("/api/unlock", json={"code": CODE}).status_code == 200
    for _ in range(3):
        assert c.post("/api/unlock", json={"code": "nope"}).status_code == 401
    r = c.post("/api/unlock", json={"code": CODE})
    assert r.status_code == 429 and "retry-after" in r.headers


def test_translate_streams_ndjson():
    c = make()
    r = c.post("/api/translate", json=body(script="latin", audience="woman"), headers={"X-Access-Code": CODE})
    assert r.headers["content-type"].startswith("application/x-ndjson")
    ev = events(r)
    assert ev[-1] == {"t": "done"}
    text = "".join(e["d"] for e in ev if e["t"] == "chunk")
    assert "Moroccan Darija" in text and "latin" in text and "Good morning" in text
    assert "<intent>" not in text


@pytest.mark.parametrize("bad,status", [
    ({"language": "xx"}, 422),
    ({"tone": "angry"}, 422),
    ({"script": "arabic", "language": "fr"}, 422),
    ({"audience": "cat"}, 422),
    ({"text": "   "}, 422),
    ({"text": "x" * 201}, 413),
    ({"text": ("Please send the report today. " * 7)[:200]}, 200),
    ({"text": "a" * 199 + "b"}, 422),  # repetitive filler is treated as automated abuse
])
def test_validation(bad, status):
    c = make()
    r = c.post("/api/translate", json=body(**bad), headers={"X-Access-Code": CODE})
    assert r.status_code == status


def test_validation_errors_do_not_echo_text():
    c = make()
    r = c.post("/api/translate", json={"text": SECRET_TEXT, "language": 5}, headers={"X-Access-Code": CODE})
    assert r.status_code == 422
    assert SECRET_TEXT not in r.text


def test_rate_limit_returns_429_with_retry_after():
    c = make(per_ip_per_min=2)
    h = {"X-Access-Code": CODE}
    assert c.post("/api/translate", json=body(), headers=h).status_code == 200
    assert c.post("/api/translate", json=body(), headers=h).status_code == 200
    r = c.post("/api/translate", json=body(), headers=h)
    assert r.status_code == 429 and int(r.headers["retry-after"]) >= 1


def test_daily_cap():
    c = make(per_code_per_day=1)
    h = {"X-Access-Code": CODE}
    assert c.post("/api/translate", json=body(), headers=h).status_code == 200
    r = c.post("/api/translate", json=body(), headers=h)
    assert r.status_code == 429 and r.json()["error"] == "daily_cap"


def test_body_size_limit():
    c = make()
    r = c.post("/api/translate", content=b"x" * 20000, headers={"X-Access-Code": CODE, "Content-Type": "application/json"})
    assert r.status_code == 413


def test_explain():
    c = make()
    r = c.post("/api/explain", json=body(translation="Salam"), headers={"X-Access-Code": CODE})
    assert r.status_code == 200
    d = r.json()
    assert set(d) >= {"meaning_back", "cultural_notes", "naturalness_flags", "confidence"}


def test_engine_error_is_friendly():
    class Broken(MockEngine):
        async def stream(self, req):
            yield "partial "
            raise EngineError("The translation service is unavailable right now.")

        async def explain(self, req, translation):
            raise EngineError("The explanation service is unavailable right now.")

    c = make(engine=Broken(delay=0))
    h = {"X-Access-Code": CODE}
    ev = events(c.post("/api/translate", json=body(), headers=h))
    assert ev[-1]["t"] == "error"
    r = c.post("/api/explain", json=body(translation="x"), headers=h)
    assert r.status_code == 502 and "unavailable" in r.json()["message"]


def test_message_text_is_never_logged(caplog):
    caplog.set_level(logging.DEBUG)
    c = make()
    h = {"X-Access-Code": CODE}
    c.post("/api/translate", json=body(text=SECRET_TEXT), headers=h)
    c.post("/api/explain", json=body(text=SECRET_TEXT, translation=SECRET_TEXT), headers=h)
    c.post("/api/translate", json=body(text=SECRET_TEXT, language="xx"), headers=h)
    c.post("/api/translate", json=body(text=SECRET_TEXT), headers={"X-Access-Code": "bad"})
    assert caplog.records, "request log lines expected"
    for rec in caplog.records:
        msg = rec.getMessage()
        assert SECRET_TEXT not in msg
        assert CODE not in msg


def test_open_dev_mode_only_with_mock():
    c = make(codes=())
    assert c.get("/api/health").json()["access_required"] is False
    assert c.post("/api/translate", json=body()).status_code == 200

    class RealLike:  # anything that isn't the mock engine counts as a paid engine
        name = "claude"
        model = "x"

        async def stream(self, req):
            yield "x"

        async def explain(self, req, t):
            return {}

    c2 = TestClient(create_app(Settings(access_codes=(), limits=security.Limits()), RealLike()))
    assert c2.post("/api/translate", json=body()).status_code == 503, "never an open proxy for a paid key"
    assert c2.get("/api/health").json()["access_required"] is True


def test_no_key_or_secret_in_browser_files():
    for f in (ROOT / "web").iterdir():
        text = f.read_text(encoding="utf-8")
        assert "ANTHROPIC" not in text and "sk-ant" not in text and "api_key" not in text.lower()
        assert "localStorage" not in text or "Nothing is written to localStorage" in text


def test_static_files_served():
    c = make()
    for path in ["/config.js", "/languages.json", "/index.html"]:
        assert c.get(path).status_code == 200, path
    assert c.get("/main.py").status_code == 404
    assert c.get("/../app/main.py").status_code == 404


def test_cors_allows_live_server_only():
    c = make()
    pre = c.options("/api/translate", headers={
        "Origin": "http://127.0.0.1:5500",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type,x-access-code",
    })
    assert pre.status_code == 200
    assert pre.headers["access-control-allow-origin"] == "http://127.0.0.1:5500"
    assert "x-access-code" in pre.headers["access-control-allow-headers"].lower()

    r = c.post("/api/translate", json=body(), headers={"Origin": "http://localhost:5500", "X-Access-Code": CODE})
    assert r.headers["access-control-allow-origin"] == "http://localhost:5500"
    err = c.post("/api/translate", json=body(), headers={"Origin": "http://localhost:5500"})
    assert err.status_code == 401 and err.headers["access-control-allow-origin"] == "http://localhost:5500"

    evil = c.get("/api/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in evil.headers


def test_dotenv_loader(tmp_path, monkeypatch):
    from app.main import load_dotenv

    env = tmp_path / ".env"
    env.write_text('# comment\nTK_T1=one\nexport TK_T2="two words"\nTK_T3=\nTK_EXISTING=file\nbad line\n', encoding="utf-8")
    monkeypatch.delenv("TK_NO_DOTENV", raising=False)
    monkeypatch.setenv("TK_EXISTING", "real")
    for k in ["TK_T1", "TK_T2", "TK_T3"]:
        monkeypatch.delenv(k, raising=False)
    load_dotenv(env)
    import os
    assert os.environ["TK_T1"] == "one"
    assert os.environ["TK_T2"] == "two words"
    assert "TK_T3" not in os.environ
    assert os.environ["TK_EXISTING"] == "real", "real environment variables win"
    for k in ["TK_T1", "TK_T2"]:
        monkeypatch.delenv(k, raising=False)
