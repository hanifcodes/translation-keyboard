"""Access codes, rate limits, daily caps and input checks.

Everything is in memory. That suits one Render instance; counters reset when
the service restarts or redeploys. See README for moving to Redis.
"""

from __future__ import annotations

import hashlib
import hmac
import threading
import time
import unicodedata
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone


def parse_codes(raw: str) -> tuple[str, ...]:
    return tuple(c.strip() for c in (raw or "").split(",") if c.strip())


def check_code(given: str | None, codes: tuple[str, ...]) -> str | None:
    """Return the matching code, comparing in constant time against every code."""
    if not given or not codes:
        return None
    g = given.encode()
    match = None
    for c in codes:
        if hmac.compare_digest(g, c.encode()):
            match = c
    return match


def code_id(code: str) -> str:
    """Short, non-reversible id for counters and logs; never log the code itself."""
    return hashlib.sha256(code.encode()).hexdigest()[:10]


class SlidingWindow:
    """At most ``limit`` events per ``window`` seconds per key."""

    def __init__(self, limit: int, window: float, clock=time.monotonic) -> None:
        self.limit, self.window, self.clock = limit, window, clock
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def _trim(self, q: deque, now: float) -> None:
        while q and now - q[0] >= self.window:
            q.popleft()

    def hit(self, key: str) -> tuple[bool, float]:
        """Record an event. Returns (allowed, retry_after_seconds)."""
        with self._lock:
            now = self.clock()
            q = self._hits[key]
            self._trim(q, now)
            if len(q) >= self.limit:
                return False, max(0.0, self.window - (now - q[0]))
            q.append(now)
            if len(self._hits) > 50_000:  # crude memory guard
                self._sweep(now)
            return True, 0.0

    def count(self, key: str) -> int:
        with self._lock:
            q = self._hits.get(key)
            if not q:
                return 0
            self._trim(q, self.clock())
            return len(q)

    def _sweep(self, now: float) -> None:
        for k in [k for k, q in self._hits.items() if not q or now - q[-1] >= self.window]:
            del self._hits[k]


class DailyCounter:
    """Counts per key per UTC day."""

    def __init__(self, today=lambda: datetime.now(timezone.utc).date().isoformat()) -> None:
        self.today = today
        self._day = today()
        self._counts: dict[str, int] = defaultdict(int)
        self._lock = threading.Lock()

    def take(self, key: str, cap: int) -> bool:
        with self._lock:
            d = self.today()
            if d != self._day:
                self._day, self._counts = d, defaultdict(int)
            if cap > 0 and self._counts[key] >= cap:
                return False
            self._counts[key] += 1
            return True

    def used(self, key: str) -> int:
        with self._lock:
            return self._counts.get(key, 0) if self._day == self.today() else 0


@dataclass
class Limits:
    per_ip_per_min: int = 40
    per_code_per_min: int = 60
    per_code_per_day: int = 1000
    global_per_day: int = 10000
    failed_codes_per_ip: int = 10      # per 10 minutes
    failed_codes_global: int = 200     # per 10 minutes, stops distributed guessing


@dataclass
class Guard:
    limits: Limits = field(default_factory=Limits)

    def __post_init__(self) -> None:
        L = self.limits
        self.ip_rate = SlidingWindow(L.per_ip_per_min, 60)
        self.code_rate = SlidingWindow(L.per_code_per_min, 60)
        self.fail_ip = SlidingWindow(L.failed_codes_per_ip, 600)
        self.fail_global = SlidingWindow(L.failed_codes_global, 600)
        self.daily = DailyCounter()

    def locked_out(self, ip: str) -> bool:
        L = self.limits
        return self.fail_ip.count(ip) >= L.failed_codes_per_ip or self.fail_global.count("*") >= L.failed_codes_global

    def record_failure(self, ip: str) -> None:
        self.fail_ip.hit(ip)
        self.fail_global.hit("*")

    def admit(self, ip: str, cid: str) -> tuple[bool, str, float]:
        """Check per-minute and daily limits. Returns (ok, reason, retry_after)."""
        ok, retry = self.ip_rate.hit(ip)
        if not ok:
            return False, "rate", retry
        ok, retry = self.code_rate.hit(cid)
        if not ok:
            return False, "rate", retry
        if not self.daily.take("*", self.limits.global_per_day):
            return False, "global_cap", 0.0
        if not self.daily.take(cid, self.limits.per_code_per_day):
            return False, "daily_cap", 0.0
        return True, "", 0.0


# --------------------------------------------------------------------------- input checks

_ALLOWED_CONTROL = {"\n", "\t"}


def clean_text(text: str) -> str:
    """Normalise and strip control characters (keeps newlines, tabs, RTL marks, emoji)."""
    text = unicodedata.normalize("NFC", text)
    out = []
    for ch in text:
        cat = unicodedata.category(ch)
        if cat == "Cc" and ch not in _ALLOWED_CONTROL:
            continue
        out.append(ch)
    return "".join(out).replace("\r\n", "\n").strip()


def looks_abusive(text: str) -> str | None:
    """Very small heuristic filter for automated abuse, not for content moderation.

    Returns a reason, or None. Content safety itself is left to the model
    provider's policies.
    """
    if len(text) >= 200 and len(set(text)) <= 3:
        return "repetitive"
    words = text.split()
    if len(words) >= 40 and len(set(words)) / len(words) < 0.1:
        return "repetitive"
    return None
