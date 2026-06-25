from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REQUIRED_RECEIPT_KEYS = frozenset({
    "release",
    "claim",
    "date",
    "all_gates_passed",
    "metrics",
    "artifacts",
    "proof_boundary",
})


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def canonical_hash(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_value(root: Path, args: list[str], default: str = "unknown") -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=root, text=True).strip()
    except Exception:
        return default


def receipt_schema_valid(receipt: dict[str, Any]) -> bool:
    if not REQUIRED_RECEIPT_KEYS.issubset(receipt):
        return False
    metrics = receipt.get("metrics", {})
    return (
        isinstance(metrics, dict)
        and receipt.get("proof_boundary") == "spectral_reader_suggests_verifier_decides"
        and metrics.get("accepted_without_verifier_support_count") == 0
    )


def build_spectral_receipt(
    *,
    root: Path,
    report: dict[str, Any],
    report_path: Path,
    data_path: Path,
) -> dict[str, Any]:
    receipt = {
        "release": "ts-spectralcompute-v0.1",
        "project": "TS-Metacompute Stack",
        "commit": git_value(root, ["rev-parse", "--short", "HEAD"]),
        "date": datetime.now(timezone.utc).isoformat(),
        "claim": (
            "Spectral mode-space can expose graph tension and suggest repair targets, "
            "but it cannot accept claims without typed verifier support."
        ),
        "scope": "Stdlib deterministic signed-graph spectral reader and repair ranking.",
        "inputs": [str(data_path.relative_to(root))],
        "commands_run": ["python3 scripts/evaluate_spectral_metacompute.py"],
        "metrics": report["metrics"],
        "report_hash": canonical_hash(report),
        "artifacts": [{"path": str(report_path.relative_to(root)), "sha256": file_hash(report_path)}],
        "proof_boundary": "spectral_reader_suggests_verifier_decides",
        "known_limitations": [
            "The v0.1 eigensolver is a small deterministic Jacobi implementation for inspection-scale graphs.",
            "Spectral readings localize tension but do not prove which claim is false.",
            "Ambiguous frustrated loops intentionally abstain when no unique edge pressure exists.",
            "No SciPy acceleration backend is used yet; the repo currently remains stdlib-only.",
        ],
        "all_gates_passed": report["all_gates_passed"],
    }
    receipt["receipt_schema_valid"] = receipt_schema_valid(receipt)
    return receipt
