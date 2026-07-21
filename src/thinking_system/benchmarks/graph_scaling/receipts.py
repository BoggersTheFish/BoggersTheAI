"""Auditable benchmark receipts."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def build_receipt(
    *,
    run_id: str,
    repo_root: Path,
    command: str,
    dataset: dict[str, Any],
    system: dict[str, Any],
    config: dict[str, Any],
    metrics: dict[str, Any],
    artifacts: list[Path],
    graph_family: str,
    known_caveats: list[str],
    failure_cases: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    commit = _git(repo_root, "rev-parse", "HEAD") or "unknown"
    branch = _git(repo_root, "rev-parse", "--abbrev-ref", "HEAD") or "unknown"
    repo_url = _git(repo_root, "remote", "get-url", "origin")
    dirty = dirty_tree_status(repo_root)
    receipt = {
        "receipt_id": run_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "repo": str(repo_root),
        "repo_url": repo_url,
        "branch": branch,
        "commit": commit,
        "commit_sha": commit,
        "dirty_tree": dirty,
        "machine": machine_info(),
        "dependencies": dependency_info(),
        "dataset": dataset,
        "system": system,
        "model": {"name": system.get("name", "ts-reference"), "hash": None},
        "seed": int(config.get("seed", 0)),
        "graph_family": graph_family,
        "config": config,
        "command": command,
        "metrics": metrics,
        "known_caveats": known_caveats,
        "failure_cases": failure_cases or [],
        "logs_path": "",
        "artifacts": [
            {"path": str(path), "sha256": sha256_file(path)}
            for path in artifacts
            if path.exists()
        ],
    }
    return receipt


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def stable_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def machine_info() -> dict[str, Any]:
    hostname_hash = hashlib.sha256(socket.gethostname().encode("utf-8")).hexdigest()[
        :16
    ]
    return {
        "hostname_hash": hostname_hash,
        "cpu": platform.processor() or platform.machine(),
        "platform": platform.platform(),
        "ram_gb": None,
        "gpu": os.environ.get("CUDA_VISIBLE_DEVICES", None),
        "cuda_version": None,
        "python_version": sys.version.split()[0],
    }


def dependency_info() -> dict[str, str]:
    return {
        "python": sys.version.split()[0],
        "ts_benchmarks": "0.1.0",
    }


def dirty_tree_status(repo_root: Path) -> dict[str, Any]:
    status = _git(repo_root, "status", "--porcelain")
    if status is None:
        return {"available": False, "is_dirty": None, "status": "unknown", "files": []}
    files = [line for line in status.splitlines() if line.strip()]
    return {
        "available": True,
        "is_dirty": bool(files),
        "status": "dirty" if files else "clean",
        "files": files[:100],
    }


def _git(repo_root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()
