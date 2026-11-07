from app.security import (
    DailyCounter,
    Guard,
    Limits,
    SlidingWindow,
    check_code,
    clean_text,
    code_id,
    looks_abusive,
    parse_codes,
)


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def test_parse_and_check_codes():
    codes = parse_codes(" alpha-123 , beta-456,, ")
    assert codes == ("alpha-123", "beta-456")
    assert check_code("beta-456", codes) == "beta-456"
    assert check_code("beta-45", codes) is None
    assert check_code("", codes) is None
    assert check_code(None, codes) is None
    assert check_code("x", ()) is None


def test_code_id_is_not_the_code():
    cid = code_id("super-secret")
    assert "secret" not in cid and len(cid) == 10


def test_sliding_window():
    clock = Clock()
    w = SlidingWindow(3, 60, clock=clock)
    assert all(w.hit("a")[0] for _ in range(3))
    ok, retry = w.hit("a")
    assert not ok and 0 < retry <= 60
    assert w.hit("b")[0], "keys are independent"
    clock.t += 61
    assert w.hit("a")[0]


def test_daily_counter_resets_on_new_day():
    day = ["2026-01-01"]
    d = DailyCounter(today=lambda: day[0])
    assert d.take("k", 2) and d.take("k", 2)
    assert not d.take("k", 2)
    day[0] = "2026-01-02"
    assert d.take("k", 2)
    assert d.used("k") == 1


def test_guard_rate_and_daily_caps():
    g = Guard(Limits(per_ip_per_min=100, per_code_per_min=100, per_code_per_day=3, global_per_day=100))
    assert [g.admit("1.1.1.1", "c")[0] for _ in range(3)] == [True] * 3
    ok, reason, _ = g.admit("1.1.1.1", "c")
    assert not ok and reason == "daily_cap"
    assert g.admit("1.1.1.1", "other")[0]

    g2 = Guard(Limits(per_ip_per_min=2))
    g2.admit("ip", "c"), g2.admit("ip", "c")
    assert g2.admit("ip", "c")[1] == "rate"


def test_guard_global_cap():
    g = Guard(Limits(global_per_day=1))
    assert g.admit("a", "c1")[0]
    assert g.admit("b", "c2")[1] == "global_cap"


def test_lockout_after_failed_codes():
    g = Guard(Limits(failed_codes_per_ip=3, failed_codes_global=1000))
    for _ in range(3):
        assert not g.locked_out("ip")
        g.record_failure("ip")
    assert g.locked_out("ip")
    assert not g.locked_out("other-ip")


def test_global_lockout():
    g = Guard(Limits(failed_codes_per_ip=100, failed_codes_global=5))
    for i in range(5):
        g.record_failure(f"ip{i}")
    assert g.locked_out("new-ip")


def test_clean_text_keeps_language_content():
    s = "  مرحبا‏ 👋\r\nẸ káàárọ̀\x00\x07 "
    out = clean_text(s)
    assert "\x00" not in out and "\x07" not in out
    assert "مرحبا" in out and "👋" in out and "‏" in out and "\n" in out
    assert out == out.strip()


def test_looks_abusive():
    assert looks_abusive("a" * 300) == "repetitive"
    assert looks_abusive("buy " * 60) == "repetitive"
    assert looks_abusive("Could you please send me the report today?") is None
