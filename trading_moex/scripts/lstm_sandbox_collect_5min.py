"""Read-only T-Bank sandbox candle RPC used by the 5-minute prospective worker.

Fetches 5-minute candles from sandbox API. Handles transient errors via retry.
Validates: complete candles only, sorted by timestamp, 5min boundaries, OHLCV.
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import sys
from datetime import datetime, timedelta, timezone

from t_tech.invest import CandleInterval, Client
from t_tech.invest.constants import INVEST_GRPC_API_SANDBOX

logging.disable(logging.CRITICAL)

# Retry transient download errors
MAX_RETRIES = 3
RETRY_BACKOFF_SEC = 1.0


def _is_5min_boundary(dt: datetime) -> bool:
    """Check if timestamp is at a 5-minute boundary (minute divisible by 5, seconds/micros zero)."""
    return dt.minute % 5 == 0 and dt.second == 0 and dt.microsecond == 0


def main() -> int:
    try:
        if len(sys.argv) < 2:
            raise ValueError("missing start timestamp")
        start = datetime.fromisoformat(sys.argv[1])
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        end = datetime.now(timezone.utc)

        if start >= end:
            raise ValueError("start >= end")

        rows_dict = {}  # key -> row, for dedup
        rows_list = []  # sorted list for final output
        source_hash = None

        import time as time_module
        retry_count = 0

        while retry_count < MAX_RETRIES:
            try:
                with Client(os.environ["TINKOFF_API_TOKEN"], target=INVEST_GRPC_API_SANDBOX) as client:
                    instrument_id = "e6123145-9665-43e0-8413-cd61b8aa9b13"
                    cursor = start

                    while cursor < end:
                        stop = min(cursor + timedelta(days=1), end)
                        response = client.market_data.get_candles(
                            instrument_id=instrument_id, from_=cursor, to=stop,
                            interval=CandleInterval.CANDLE_INTERVAL_5_MIN,
                        )

                        for candle in response.candles:
                            stamp = candle.time.astimezone(timezone.utc)

                            # Validate: complete, in range, normalized to 5min boundary
                            if not candle.is_complete:
                                continue
                            if stamp < start or stamp + timedelta(minutes=5) > end:
                                continue
                            if not _is_5min_boundary(stamp):
                                raise ValueError(f"candle {stamp} not at 5min boundary")

                            # Normalize to UTC-naive ISO format with space separator
                            key = stamp.replace(tzinfo=None).isoformat(" ")

                            # Extract OHLCV
                            values = [
                                quotation.units + quotation.nano / 1e9
                                for quotation in (candle.open, candle.high, candle.low, candle.close)
                            ]
                            volume = candle.volume

                            # Validate OHLCV
                            if not all(math.isfinite(v) for v in values):
                                raise ValueError(f"non-finite price at {key}")
                            if not math.isfinite(volume):
                                raise ValueError(f"non-finite volume at {key}")
                            open_, high, low, close = values
                            if not (0 < low <= open_ <= high and low <= close <= high and volume >= 0):
                                raise ValueError(f"invalid OHLCV at {key}: o={open_} h={high} l={low} c={close} v={volume}")

                            row = [key, *values, volume]

                            # Check for conflicts
                            if key in rows_dict:
                                if rows_dict[key] != row:
                                    raise ValueError(f"conflicting duplicate at {key}")
                                continue

                            rows_dict[key] = row

                        cursor = stop

                # Success: sort and prepare output
                rows_list = sorted(rows_dict.values(), key=lambda r: r[0])
                source_hash = hashlib.sha256(
                    json.dumps(rows_list, separators=(",", ":")).encode()
                ).hexdigest()
                break

            except ValueError:
                raise
            except Exception:
                retry_count += 1
                if retry_count < MAX_RETRIES:
                    time_module.sleep(RETRY_BACKOFF_SEC)
                    continue
                raise

        # Validate sorted timestamps
        for i in range(len(rows_list) - 1):
            if rows_list[i][0] >= rows_list[i + 1][0]:
                raise ValueError(f"timestamps not sorted: {rows_list[i][0]} >= {rows_list[i + 1][0]}")

        output = {
            "source": INVEST_GRPC_API_SANDBOX,
            "rows": rows_list,
            "source_sha256": source_hash,
        }
        print(json.dumps(output))
        return 0

    except ValueError:
        print('{"error":"invalid_market_data"}')
        return 2
    except Exception:
        # Do not expose SDK errors, credentials, or internal details
        print('{"error":"sandbox_download_failed"}')
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
