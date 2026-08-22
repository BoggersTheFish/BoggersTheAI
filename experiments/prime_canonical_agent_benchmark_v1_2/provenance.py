"""Frozen-input and source provenance for benchmark v1.2."""

import hashlib
from pathlib import Path
import subprocess


HERE = Path(__file__).resolve().parent
V1 = HERE.parent / "prime_canonical_agent_benchmark_v1"
V11 = HERE.parent / "prime_canonical_agent_benchmark_v1_1"
REPO = HERE.parent.parent


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify(
    directory: Path,
    target_name: str,
    checksum_name: str,
) -> str:
    target = directory / target_name
    checksum = directory / checksum_name

    expected = checksum.read_text(
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
        "v1_2_contract_sha256": _verify(
            HERE,
            "EXPERIMENT_CONTRACT.md",
            "EXPERIMENT_CONTRACT.sha256",
        ),
        "v1_2_lineage_sha256": _verify(
            HERE,
            "LINEAGE.json",
            "LINEAGE.sha256",
        ),
        "v1_2_adaptive_rules_sha256": _verify(
            HERE,
            "ADAPTIVE_RULES.md",
            "ADAPTIVE_RULES.sha256",
        ),
        "v1_2_fixed_comparator_sha256": _verify(
            HERE,
            "DEVELOPMENT_FIXED_COMPARATOR.json",
            "DEVELOPMENT_FIXED_COMPARATOR.sha256",
        ),
        "parent_v1_1_result_sha256": _verify(
            V11,
            "FROZEN_EVALUATION_RESULT.json",
            "FROZEN_EVALUATION_RESULT.sha256",
        ),
    }


def implementation_sha256() -> str:
    """Hash executable parent apparatus plus v1.2 Python sources."""
    digest = hashlib.sha256()
    entries: list[tuple[str, Path]] = []

    for prefix, directory in (
        ("v1", V1),
        ("v1_2", HERE),
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
