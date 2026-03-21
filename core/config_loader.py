from __future__ import annotations

import logging
from dataclasses import fields
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger("boggers.config")

_SEARCH_PATHS = ("config.yaml", "BoggersTheAI/config.yaml")


def _deep_merge(base: dict, overlay: dict) -> dict:
    merged = dict(base)
    for key, value in overlay.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def find_config(search_paths: tuple[str, ...] = _SEARCH_PATHS) -> Path | None:
    for candidate in search_paths:
        path = Path(candidate)
        if path.exists():
            return path
    return None


def load_yaml(path: Path | str | None = None) -> Dict[str, Any]:
    try:
        import yaml
    except ImportError:
        logger.warning("PyYAML not installed; using defaults")
        return {}

    if path is None:
        path = find_config()
    if path is None:
        logger.info("No config.yaml found; using defaults")
        return {}
    target = Path(path)
    if not target.exists():
        logger.warning("Config path %s does not exist; using defaults", target)
        return {}
    try:
        raw = yaml.safe_load(target.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            logger.warning("Config file did not parse as dict; using defaults")
            return {}
        logger.info("Loaded config from %s", target)
        return raw
    except Exception as exc:
        logger.error("Failed to parse config: %s", exc)
        return {}


def apply_yaml_to_config(config: object, yaml_data: Dict[str, Any]) -> None:
    if not yaml_data:
        return
    field_names = (
        {f.name for f in fields(config)}
        if hasattr(config, "__dataclass_fields__")
        else set()
    )

    for key, value in yaml_data.items():
        if key not in field_names:
            continue
        current = getattr(config, key, None)
        if isinstance(current, dict) and isinstance(value, dict):
            setattr(config, key, _deep_merge(current, value))
        else:
            setattr(config, key, value)

    runtime_section = yaml_data.get("runtime", {})
    if isinstance(runtime_section, dict):
        for attr in (
            "graph_path",
            "insight_vault_path",
            "max_hypotheses_per_cycle",
            "session_id",
            "graph_backend",
            "sqlite_path",
            "snapshot_dir",
        ):
            if attr in runtime_section and attr in field_names:
                setattr(config, attr, runtime_section[attr])

    if "inference" in yaml_data and isinstance(yaml_data["inference"], dict):
        throttle = yaml_data["inference"].get("throttle_seconds")
        if throttle is not None and "throttle_seconds" in field_names:
            setattr(config, "throttle_seconds", int(throttle))


def load_and_apply(config: object, path: Path | str | None = None) -> Dict[str, Any]:
    yaml_data = load_yaml(path)
    if yaml_data:
        from .config_schema import validate_config

        validate_config(yaml_data)
    apply_yaml_to_config(config, yaml_data)
    return yaml_data
