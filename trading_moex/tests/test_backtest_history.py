from pathlib import Path
import asyncio

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_backtest_history_persists_form_context_and_error():
    from app import storage

    params = {"direction": 2, "atr_k": 0.5}
    run_id = storage.create_run(
        "SBER", "1day", "elliott_candles", params, "2026-01-01", "2026-02-01"
    )

    storage.finish_run(run_id, None, "MOEX вернул пустые данные")

    run = storage.get_run(run_id)
    assert run["ticker"] == "SBER"
    assert run["period"] == "1day"
    assert run["strategy"] == "elliott_candles"
    assert run["params"] == params
    assert run["start_date"] == "2026-01-01"
    assert run["end_date"] == "2026-02-01"
    assert run["status"] == "error"
    assert run["error"] == "MOEX вернул пустые данные"


def test_strategy_parameter_panels_disable_inactive_fields():
    template = Path(__file__).resolve().parent.parent / "app/web/templates/index.html"
    source = template.read_text()

    assert 'disabled{% endif %}' in source
    assert 'control.disabled = !active' in source
    assert '{{ r.error }}' in source
    assert 'Период: {{ r.start_date }}' in source


async def test_backtest_form_values_are_saved_to_history(monkeypatch):
    from app import storage
    from app.web import app as web_app

    class Request:
        match_info = {}
        query = {}

        async def post(self):
            return {
                "ticker": "SBER",
                "period": "1day",
                "strategy": "elliott_candles",
                "start": "2026-01-01",
                "end": "2026-02-01",
                "cash": "150000",
                "commission": "0.001",
                "direction": "2",
                "atr_k": "0.75",
            }

    async def skip_backtest(*args):
        return None

    monkeypatch.setattr(web_app, "_run_backtest_job", skip_backtest)
    response = await web_app.backtest_run(Request())
    await asyncio.sleep(0)

    assert response.status == 200
    run = storage.list_runs(1)[0]
    assert run["ticker"] == "SBER"
    assert run["strategy"] == "elliott_candles"
    assert run["start_date"] == "2026-01-01"
    assert run["end_date"] == "2026-02-01"
    assert run["params"]["direction"] == 2
    assert run["params"]["atr_k"] == 0.75
