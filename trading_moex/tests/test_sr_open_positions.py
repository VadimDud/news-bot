from app.sr_research import sanity_checks


def test_sanity_checks_reject_open_broker_position():
    report = {"results": [{"ticker": "SBER", "status": "ok", "trades_total": 0,
                            "trades": [], "open_positions": [{"size": 10}]}]}
    checks = sanity_checks(report)
    assert checks["no_open_broker_positions"] is False
    assert checks["passed"] is False
