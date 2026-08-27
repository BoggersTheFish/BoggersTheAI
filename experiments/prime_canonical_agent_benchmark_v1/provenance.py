"""Canonical benchmark provenance helpers."""

import hashlib
from pathlib import Path
import subprocess


BENCHMARK_DIR = Path(__file__).resolve().parent
REPO_ROOT = BENCHMARK_DIR.parent.parent


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def contract_sha256() -> str:
    contract = BENCHMARK_DIR / "EXPERIMENT_CONTRACT.md"
    expected_file = BENCHMARK_DIR / "EXPERIMENT_CONTRACT.sha256"

    expected = expected_file.read_text(encoding="utf-8").split()[0]
    actual = _sha256(contract)

    if actual != expected:
        raise RuntimeError("frozen experiment contract hash mismatch")

    return actual


def source_commit() -> str:
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    commit = result.stdout.strip()

    if len(commit) != 40:
        raise RuntimeError("unexpected git commit identity")

    return commit


def source_dirty() -> bool:
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    )
    return bool(result.stdout.strip())


def implementation_sha256() -> str:
    """Hash the complete Python implementation of benchmark v1."""

    digest = hashlib.sha256()

    paths = sorted(
        path
        for path in BENCHMARK_DIR.glob("*.py")
        if path.name != "__pycache__"
    )

    for path in paths:
        relative = path.name.encode("utf-8")
        payload = path.read_bytes()

        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)

    return digest.hexdigest()
