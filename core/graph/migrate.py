from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger("boggers.graph.migrate")

CURRENT_SCHEMA_VERSION = 2


def get_schema_version(data: dict) -> int:
    return int(data.get("schema_version", 1))


def migrate_v1_to_v2(data: dict) -> dict:
    for node in data.get("nodes", []):
        if "base_strength" not in node:
            node["base_strength"] = 0.5
        if "attributes" not in node:
            node["attributes"] = {}
    for edge in data.get("edges", []):
        if "relation" not in edge:
            edge["relation"] = "relates"
    data["schema_version"] = 2
    logger.info("Migrated graph from v1 to v2")
    return data


_MIGRATIONS = {
    1: migrate_v1_to_v2,
}


def migrate_graph_data(data: dict) -> dict:
    version = get_schema_version(data)
    while version < CURRENT_SCHEMA_VERSION:
        migrator = _MIGRATIONS.get(version)
        if migrator is None:
            logger.warning("No migration path from v%d", version)
            break
        data = migrator(data)
        version = get_schema_version(data)
    return data


def migrate_json_file(path: str | Path) -> bool:
    target = Path(path)
    if not target.exists():
        return False
    raw = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return False
    version = get_schema_version(raw)
    if version >= CURRENT_SCHEMA_VERSION:
        return False
    migrated = migrate_graph_data(raw)
    target.write_text(json.dumps(migrated, indent=2), encoding="utf-8")
    logger.info("Migrated %s to schema v%d", target, CURRENT_SCHEMA_VERSION)
    return True
