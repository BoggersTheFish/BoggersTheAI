"""Frozen provenance for PRIME canonical agent benchmark v1.3."""

import hashlib
from pathlib import Path
import subprocess


HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parent
V1 = EXPERIMENTS / "prime_canonical_agent_benchmark_v1"
V12 = EXPERIMENTS / "prime_canonical_agent_benchmark_v1_2"
REPO = EXPERIMENTS.parent


def _sha256(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def _verify(
    directory: Path,
    target_name: str,
    checksum_name: str,
) -> str:
    target = directory / target_name

    expected = (
        directory
        / checksum_name
    ).read_text(
        encoding="utf-8"
    ).split()[0]

    actual = _sha256(target)

    if actual != expected:
        raise RuntimeError(
            f"frozen hash mismatch: {target}"
        )

    return actual


def frozen_identities() -> dict:
    return {
        "v1_3_contract_sha256": _verify(
            HERE,
            "EXPERIMENT_CONTRACT.md",
            "EXPERIMENT_CONTRACT.sha256",
        ),
        "v1_3_lineage_sha256": _verify(
            HERE,
            "LINEAGE.json",
            "LINEAGE.sha256",
        ),
        "v1_3_adaptive_rules_sha256": _verify(
            HERE,
            "ADAPTIVE_RULES.md",
            "ADAPTIVE_RULES.sha256",
        ),
        "v1_3_fixed_comparator_sha256": _verify(
            HERE,
            "DEVELOPMENT_FIXED_COMPARATOR.json",
            "DEVELOPMENT_FIXED_COMPARATOR.sha256",
        ),
        "parent_v1_2_result_sha256": _verify(
            V12,
            "FROZEN_EVALUATION_RESULT.json",
            "FROZEN_EVALUATION_RESULT.sha256",
        ),
    }


def implementation_sha256() -> str:
    """Hash only executable dependencies of the v1.3 adaptive core."""

    entries: list[
        tuple[str, Path]
    ] = []

    # Canonical common apparatus.
    for path in V1.glob("*.py"):
        entries.append(
            (
                f"v1/{path.name}",
                path,
            )
        )

    # Frozen parent machinery reused directly
    # by the v1.2-reference condition and
    # receipt infrastructure.
    for name in (
        "verifier.py",
        "receipts.py",
    ):
        entries.append(
            (
                f"v1_2/{name}",
                V12 / name,
            )
        )

    # Explicit hypothesis-bearing v1.3 core.
    for name in (
        "manifest.py",
        "factor_verifier.py",
        "adaptive_runner.py",
        "provenance.py",
    ):
        path = HERE / name

        if path.exists():
            entries.append(
                (
                    f"v1_3/{name}",
                    path,
                )
            )

    digest = hashlib.sha256()

    for relative, path in sorted(
        entries
    ):
        name = relative.encode(
            "utf-8"
        )
        payload = path.read_bytes()

        digest.update(
            len(name).to_bytes(
                8,
                "big",
            )
        )
        digest.update(name)

        digest.update(
            len(payload).to_bytes(
                8,
                "big",
            )
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
            "unexpected commit identity"
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

    return bool(
        result.stdout.strip()
    )
