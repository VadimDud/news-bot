"""Фикстуры тестов: изолированная БД в tmp_path.

Модули приложения читают путь БД из ``app.config`` в runtime, поэтому достаточно
перенаправить ``config.DATA_DIR``/``config.DB_PATH`` до вызова хранилища.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    from app import config
    from app import storage

    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "trader.db")
    monkeypatch.setattr(config, "CANDLE_CACHE_DIR", tmp_path / "candles")
    storage.init_db()
    yield