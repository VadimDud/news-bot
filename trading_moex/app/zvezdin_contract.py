"""Loading and semantic validation for the declarative Zvezdin contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator

from .zvezdin_engine import StrategyConfig


CONTRACT_VERSION = "1.1.0"


def load_contract(source: str | Path | Mapping[str, Any]) -> dict[str, Any]:
    """Load a JSON contract and apply the engine's explicit defaults.

    JSON Schema defaults are annotations, not assignments. This function is the
    single place that turns the declarative document into runtime parameters.
    """

    if isinstance(source, Mapping):
        document = dict(source)
    else:
        document = json.loads(Path(source).read_text(encoding="utf-8"))
    if document.get("version") != CONTRACT_VERSION:
        raise ValueError(f"unsupported contract version: {document.get('version')!r}")
    if document.get("usage") != "TESTING_ONLY_NOT_FOR_TRADING":
        raise ValueError("Zvezdin contract is testing-only and not for trading")
    if "$schema" in document:
        raise ValueError("a JSON Schema is not a runtime configuration document")
    required = {
        "hyperparameters", "indicators", "fsm_states", "zone_rules",
        "candle_rules", "execution_rules",
    }
    missing = required.difference(document)
    if missing:
        raise ValueError(f"missing contract sections: {sorted(missing)}")
    schema_path = Path(__file__).resolve().parents[1] / "config" / "zvezdin_contract_v1_1.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(document), key=lambda error: list(error.path))
    if errors:
        first = errors[0]
        location = ".".join(str(item) for item in first.path) or "$"
        raise ValueError(f"contract schema error at {location}: {first.message}")
    return document


def strategy_config_from_contract(source: str | Path | Mapping[str, Any]) -> StrategyConfig:
    document = load_contract(source)
    values = dict(document["hyperparameters"])
    # Runtime-only execution knobs are represented explicitly in the contract.
    values["rvol_days"] = values.pop("rvol_days_D", values.get("rvol_days", 20))
    values.setdefault("fixed_spread", 0.0)
    values.setdefault("fixed_slippage", 0.0)
    config = StrategyConfig(**{
        key: value for key, value in values.items()
        if key in StrategyConfig.__dataclass_fields__
    })
    validate_strategy_config(config)
    return config


def strategy_config_for_ticker(
    source: str | Path | Mapping[str, Any],
    ticker: str,
) -> StrategyConfig:
    """Load the base config and apply an optional per-ticker profile."""

    document = load_contract(source)
    values = dict(document["hyperparameters"])
    profile = document.get("ticker_profiles", {}).get(ticker.upper(), {})
    if not isinstance(profile, Mapping):
        raise ValueError(f"ticker profile for {ticker!r} must be an object")
    values.update(profile)
    values["rvol_days"] = values.pop("rvol_days_D", values.get("rvol_days", 20))
    values.setdefault("fixed_spread", 0.0)
    values.setdefault("fixed_slippage", 0.0)
    config = StrategyConfig(**{
        key: value for key, value in values.items()
        if key in StrategyConfig.__dataclass_fields__
    })
    validate_strategy_config(config)
    return config


def validate_strategy_config(config: StrategyConfig) -> None:
    """Validate cross-field invariants not expressible in JSON Schema."""

    if config.zone_width_atr_ratio > config.zone_cluster_atr_ratio:
        raise ValueError("zone width ratio cannot exceed cluster radius ratio")
    if config.rvol_k_v < 1:
        raise ValueError("rvol_k_v must be at least 1")
    if config.max_concurrent_positions != 1:
        raise ValueError("the single-instrument engine supports one position")


def load_default_config() -> StrategyConfig:
    path = Path(__file__).resolve().parents[1] / "config" / "zvezdin_default_config_v1_1.json"
    return strategy_config_from_contract(path)
