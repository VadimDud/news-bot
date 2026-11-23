"""Sample the SBER share book and broker status; observation only, no orders."""
import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import subprocess
import sys

UID = 'e6123145-9665-43e0-8413-cd61b8aa9b13'


def collect():
    logging.disable(logging.CRITICAL)
    from t_tech.invest import Client
    from t_tech.invest.constants import INVEST_GRPC_API_SANDBOX

    with Client(os.environ['TINKOFF_API_TOKEN'], target=INVEST_GRPC_API_SANDBOX) as client:
        book = client.market_data.get_order_book(instrument_id=UID, depth=1)
        status = client.market_data.get_trading_status(instrument_id=UID)
    def level(side):
        if not side:
            return None
        p = side[0].price
        return {'price': str(Decimal(p.units) + Decimal(p.nano).scaleb(-9)),
                'quantity': side[0].quantity}
    return dict(instrument_uid=UID, ticker='SBER', source=INVEST_GRPC_API_SANDBOX,
                book_time=book.orderbook_ts.isoformat() if book.orderbook_ts else None,
                bid=level(book.bids), ask=level(book.asks),
                trading_status=status.trading_status.name,
                api_trading_available=status.api_trade_available_flag,
                limit_orders_available=status.limit_order_available_flag,
                market_orders_available=status.market_order_available_flag)


def archive():
    start = datetime.now(timezone.utc)
    script = Path(__file__).resolve()
    run = script.parents[1] / 'artifacts/runs/sber_quote_observations' / start.strftime('%Y%m%dT%H%M%S%fZ')
    run.mkdir(parents=True, exist_ok=False)
    code = script.read_bytes()
    record = dict(started_utc=start.isoformat(), collector_sha256=hashlib.sha256(code).hexdigest(),
                  study_admission=False, orders_enabled=False)
    try:
        result = subprocess.run(['docker', 'exec', '-i', 'trader-bot-engine', 'python', '-B', '-', '--collect'],
                                input=code, capture_output=True, check=True, timeout=45)
        record.update(quote=json.loads(result.stdout), status='observed')
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        record.update(status='failed', error_type=type(exc).__name__)
    record['finished_utc'] = datetime.now(timezone.utc).isoformat()
    with (run / 'observation.json').open('x') as stream:
        json.dump(record, stream, indent=2)
    print(run, record['status'])
    return int(record['status'] != 'observed')


if __name__ == '__main__':
    if sys.argv[1:] == ['--collect']:
        print(json.dumps(collect()))
    else:
        raise SystemExit(archive())
