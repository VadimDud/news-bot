"""Template coverage for operational live status."""

from pathlib import Path

import jinja2


def _render(status):
    root = Path(__file__).resolve().parents[1] / "app" / "web" / "templates"
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(root))
    return env.get_template("_live_status.html").render(status=status)


def test_template_shows_reconciliation_blocker():
    html = _render({
        "running": True,
        "dry_run": False,
        "last_update": None,
        "last_error": None,
        "circuit_breaker": {"tripped": False},
        "risk": {},
        "reconciliation": {"ok": False, "issues": ["FIGI: quantity mismatch"]},
        "prices": [],
        "entries": {},
        "portfolio": [],
        "signals": {},
        "log": [],
    })

    assert "новые ордера заблокированы" in html
    assert "FIGI: quantity mismatch" in html


def test_template_shows_reconciliation_ok():
    html = _render({
        "running": False,
        "dry_run": True,
        "last_update": None,
        "last_error": None,
        "circuit_breaker": {},
        "risk": {},
        "reconciliation": {"ok": True, "issues": []},
        "prices": [],
        "entries": {},
        "portfolio": [],
        "signals": {},
        "log": [],
    })

    assert "локальное состояние совпадает" in html


def test_live_page_contains_adaptive_drag_contract():
    root = Path(__file__).resolve().parents[1] / "app" / "web" / "templates"
    html = (root / "live.html").read_text(encoding="utf-8")

    assert "adaptive-drag-layer" in html
    assert "beginDrag" in html
    assert "risk_reward" in html
    assert "dry_run: true" in html
