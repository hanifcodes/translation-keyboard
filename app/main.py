"""Translation Keyboard - FastAPI app.

Privacy: request bodies are never logged. The request log line contains only
method, path, status and duration. Validation errors are returned without
echoing the submitted text.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, Field

ROOT_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT_DIR / "web"
STATIC_FILES = {"app.js": "text/javascript", "config.js": "text/javascript", "languages.json": "application/json"}
DEFAULT_ORIGINS = "http://localhost:5500,http://127.0.0.1:5500"


def load_dotenv(path: Path = ROOT_DIR / ".env") -> None:
    """Minimal .env reader (KEY=VALUE lines) so local runs work on any OS without extra packages.
    Real environment variables always win. Set TK_NO_DOTENV=1 to skip (tests do)."""
    if os.environ.get("TK_NO_DOTENV") or not path.is_file():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip().removeprefix("export ").strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key and value:
            os.environ.setdefault(key, value)


load_dotenv()

from . import security  # noqa: E402
from .engine import EngineError, MockEngine, Request as EngineRequest, build_engine  # noqa: E402
from .export_languages import payload as languages_payload  # noqa: E402
from .languages import AUDIENCES, TONES, get_profile  # noqa: E402

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s %(message)s")
for noisy in ("anthropic", "httpx", "httpcore"):
    logging.getLogger(noisy).setLevel(logging.WARNING)
log = logging.getLogger("tk")

CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
    "connect-src 'self'; font-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'; object-src 'none'"
)


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


@dataclass
class Settings:
    access_codes: tuple[str, ...] = ()
    max_chars: int = 1000
    max_body: int = 16_000
    limits: security.Limits = None  # type: ignore[assignment]
    allowed_origins: tuple[str, ...] = tuple(DEFAULT_ORIGINS.split(","))

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            access_codes=security.parse_codes(os.environ.get("ACCESS_CODES", "")),
            allowed_origins=tuple(o.rstrip("/") for o in security.parse_codes(os.environ.get("ALLOWED_ORIGINS", DEFAULT_ORIGINS))),
            max_chars=_int("MAX_CHARS", 1000),
            limits=security.Limits(
                per_ip_per_min=_int("RATE_PER_IP_PER_MIN", 40),
                per_code_per_min=_int("RATE_PER_CODE_PER_MIN", 60),
                per_code_per_day=_int("DAILY_CAP_PER_CODE", 1000),
                global_per_day=_int("DAILY_CAP_GLOBAL", 10000),
            ),
        )


class TranslateIn(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    language: str = Field(min_length=1, max_length=16)
    tone: str = "friendly"
    script: str | None = None
    audience: str = "unknown"


class ExplainIn(TranslateIn):
    translation: str = Field(min_length=1, max_length=8000)


class UnlockIn(BaseModel):
    code: str = Field(min_length=1, max_length=200)


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, retry_after: float = 0) -> None:
        self.status, self.code, self.message, self.retry_after = status, code, message, retry_after


def create_app(settings: Settings | None = None, engine=None) -> FastAPI:
    settings = settings or Settings.from_env()
    if settings.limits is None:
        settings.limits = security.Limits()
    engine = engine or build_engine()
    guard = security.Guard(settings.limits)
    is_mock = isinstance(engine, MockEngine)

    app = FastAPI(title="Translation Keyboard", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.engine, app.state.guard, app.state.settings = engine, guard, settings

    # ---------------------------------------------------------------- middleware
    @app.middleware("http")
    async def guard_and_log(request: Request, call_next):
        start = time.perf_counter()
        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > settings.max_body:
            response: Response = JSONResponse({"error": "too_large", "message": "That message is too long."}, status_code=413)
        else:
            response = await call_next(request)
        response.headers["Content-Security-Policy"] = CSP
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        # Path only: no query string, no body, no headers.
        log.info("%s %s %s %.0fms", request.method, request.url.path, response.status_code, (time.perf_counter() - start) * 1000)
        return response

    # Lets the page call this server when it is opened from VS Code Live Server
    # or GitHub Pages. Added last, so it wraps everything (errors get CORS headers too).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.allowed_origins),
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-Access-Code"],
        allow_credentials=False,
        max_age=600,
    )

    @app.exception_handler(ApiError)
    async def api_error(_: Request, exc: ApiError):
        headers = {"Retry-After": str(max(1, int(exc.retry_after + 0.999)))} if exc.retry_after else None
        return JSONResponse({"error": exc.code, "message": exc.message}, status_code=exc.status, headers=headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError):
        fields = sorted({str(e.get("loc", ["", "?"])[-1]) for e in exc.errors()})
        return JSONResponse({"error": "invalid", "message": "Some of the request was invalid.", "fields": fields}, status_code=422)

    # ---------------------------------------------------------------- helpers
    def client_ip(request: Request) -> str:
        return request.client.host if request.client else "unknown"

    def authorise(request: Request) -> str:
        """Return a counter id for this caller or raise ApiError."""
        ip = client_ip(request)
        if settings.access_codes:
            if guard.locked_out(ip):
                raise ApiError(429, "locked", "Too many wrong codes. Please wait a few minutes.", 600)
            code = security.check_code(request.headers.get("x-access-code"), settings.access_codes)
            if not code:
                guard.record_failure(ip)
                raise ApiError(401, "access", "Please enter a valid access code.")
            cid = security.code_id(code)
        elif is_mock:
            cid = "open-dev"
        else:
            raise ApiError(503, "not_configured", "This server has no access codes set, so it is locked.")
        ok, reason, retry = guard.admit(ip, cid)
        if not ok:
            if reason == "rate":
                raise ApiError(429, "rate", "You're going a little fast. Try again in a moment.", retry)
            if reason == "daily_cap":
                raise ApiError(429, "daily_cap", "This access code has reached today's limit. It resets at midnight UTC.")
            raise ApiError(503, "global_cap", "The service has reached today's limit. Please try again tomorrow.")
        return cid

    def to_request(body: TranslateIn) -> EngineRequest:
        profile = get_profile(body.language)
        if not profile:
            raise ApiError(422, "language", "That language isn't available.")
        if body.tone not in TONES:
            raise ApiError(422, "tone", "That tone isn't available.")
        if body.audience not in AUDIENCES:
            raise ApiError(422, "audience", "That option isn't available.")
        script = body.script or profile.default_script
        if script not in profile.scripts:
            raise ApiError(422, "script", f"{profile.name} isn't available in that script.")
        text = security.clean_text(body.text)
        if not text:
            raise ApiError(422, "empty", "Type something to translate.")
        if len(text) > settings.max_chars:
            raise ApiError(413, "too_long", f"Please keep messages under {settings.max_chars} characters.")
        if security.looks_abusive(text):
            raise ApiError(422, "abuse", "That message looks automated, so it wasn't sent.")
        return EngineRequest(text=text, profile=profile, tone=body.tone, script=script, audience=body.audience)

    # ---------------------------------------------------------------- pages
    @app.get("/", include_in_schema=False)
    async def index():
        return FileResponse(WEB_DIR / "index.html", media_type="text/html")

    @app.get("/index.html", include_in_schema=False)
    async def index_html():
        return FileResponse(WEB_DIR / "index.html", media_type="text/html")

    def static_route(name: str, media_type: str):
        async def serve():
            return FileResponse(WEB_DIR / name, media_type=media_type)
        app.get(f"/{name}", include_in_schema=False)(serve)

    for name, media_type in STATIC_FILES.items():
        static_route(name, media_type)

    # ---------------------------------------------------------------- api
    @app.get("/api/health")
    async def health():
        return {"status": "ok", "engine": engine.name, "access_required": bool(settings.access_codes) or not is_mock}

    @app.get("/api/languages")
    async def languages():
        return languages_payload(settings.max_chars)

    @app.post("/api/unlock")
    async def unlock(body: UnlockIn, request: Request):
        ip = client_ip(request)
        if not settings.access_codes:
            if is_mock:
                return {"ok": True}
            raise ApiError(503, "not_configured", "This server has no access codes set, so it is locked.")
        if guard.locked_out(ip):
            raise ApiError(429, "locked", "Too many wrong codes. Please wait a few minutes.", 600)
        if not security.check_code(body.code, settings.access_codes):
            guard.record_failure(ip)
            raise ApiError(401, "access", "That code didn't work. Check it and try again.")
        return {"ok": True}

    @app.post("/api/translate")
    async def translate(body: TranslateIn, request: Request):
        authorise(request)
        req = to_request(body)

        async def events():
            try:
                async for chunk in engine.stream(req):
                    yield json.dumps({"t": "chunk", "d": chunk}, ensure_ascii=False) + "\n"
                yield json.dumps({"t": "done"}) + "\n"
            except EngineError as exc:
                yield json.dumps({"t": "error", "m": str(exc)}) + "\n"
            except Exception as exc:  # noqa: BLE001
                log.warning("stream failed: %s", type(exc).__name__)
                yield json.dumps({"t": "error", "m": "Something went wrong. Please try again."}) + "\n"

        return StreamingResponse(
            events(),
            media_type="application/x-ndjson",
            headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
        )

    @app.post("/api/explain")
    async def explain(body: ExplainIn, request: Request):
        authorise(request)
        req = to_request(body)
        translation = security.clean_text(body.translation)
        try:
            result = await engine.explain(req, translation)
        except EngineError as exc:
            raise ApiError(502, "engine", str(exc)) from None
        return result

    return app


app = create_app()
