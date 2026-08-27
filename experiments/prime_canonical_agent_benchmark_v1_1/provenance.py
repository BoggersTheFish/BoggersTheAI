"""Successor benchmark provenance and frozen-input verification."""

import hashlib
from pathlib import Path
import subprocess


HERE = Path(__file__).resolve().parent
V1 = HERE.parent / "prime_canonical_agent_benchmark_v1"
REPO = HERE.parent.parent


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_sha_file(
    directory: Path,
    target_filename: str,
    checksum_filename: str,
) -> str:
    target = directory / target_filename
    checksum_file = directory / checksum_filename

    expected = checksum_file.read_text(
        encoding="utf-8"
    ).split()[0]

    actual = _sha256(target)

    if actual != expected:
        raise RuntimeError(
            f"frozen hash mismatch: {target.name}"
        )

    return actual


def frozen_identities() -> dict:
    return {
        "v1_contract_sha256": _verify_sha_file(
            V1,
            "EXPERIMENT_CONTRACT.md",
            "EXPERIMENT_CONTRACT.sha256",
        ),
        "v1_development_selection_sha256": _verify_sha_file(
            V1,
            "DEVELOPMENT_BASELINE_SELECTION.json",
            "DEVELOPMENT_BASELINE_SELECTION.sha256",
        ),
        "v1_retirement_sha256": _verify_sha_file(
            V1,
            "RETIREMENT.md",
            "RETIREMENT.sha256",
        ),
        "v1_1_contract_sha256": _verify_sha_file(
            HERE,
            "EXPERIMENT_CONTRACT.md",
            "EXPERIMENT_CONTRACT.sha256",
        ),
        "v1_1_lineage_sha256": _verify_sha_file(
            HERE,
            "LINEAGE.json",
            "LINEAGE.sha256",
        ),
        "v1_1_adaptive_rules_sha256": _verify_sha_file(
            HERE,
            "ADAPTIVE_RULES.md",
            "ADAPTIVE_RULES.sha256",
        ),
    }


def implementation_sha256() -> str:
    """Hash executable Python sources from parent apparatus + successor."""

    digest = hashlib.sha256()
    entries: list[tuple[str, Path]] = []

    for prefix, directory in (
        ("v1", V1),
        ("v1_1", HERE),
    ):
        for path in directory.glob("*.py"):
            entries.append(
                (f"{prefix}/{path.name}", path)
            )

    for relative, path in sorted(entries):
        name = relative.encode("utf-8")
        payload = path.read_bytes()

        digest.update(
            len(name).to_bytes(8, "big")
        )
        digest.update(name)

        digest.update(
            len(payload).to_bytes(8, "big")
        )
        digest.update(payload)

    return digest.hexdigest()


def source_commit() -> str:
    result = subprocess.run(
        [
            "git",
            "-C",
            str(REPO),
            "rev-parse",
            "HEAD",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    commit = result.stdout.strip()

    if len(commit) != 40:
        raise RuntimeError(
            "unexpected git commit identity"
        )

    return commit


def source_dirty() -> bool:
    result = subprocess.run(
        [
            "git",
            "-C",
            str(REPO),
            "status",
            "--porcelain",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    return bool(result.stdout.strip())
