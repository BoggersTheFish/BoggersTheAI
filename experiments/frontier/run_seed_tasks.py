"""Run the receipt-first Kernel v0.2 frontier seed suite."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = PROJECT_ROOT.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from BoggersTheAI.core.graph.universal_living_graph import UniversalLivingGraph
from BoggersTheAI.core.kernel.kernel import TSKernel
from BoggersTheAI.core.kernel.receipts import validate_receipt_hash
from BoggersTheAI.core.kernel.replay import replay_receipt

DEFAULT_SEED_DIR = Path(__file__).resolve().parent / "seed_tasks"
DEFAULT_RECEIPT_DIR = Path("artifacts") / "seed_receipts"
SAFE_TASK_ID = re.compile(r"^[A-Za-z0-9_.-]+$")


@dataclass(frozen=True, slots=True)
class SeedTask:
    id: str
    title: str
    input: str
    expected_decision: str
    expected_contains: list[str]
    notes: str


@dataclass(frozen=True, slots=True)
class SeedRunResult:
    task: SeedTask
    actual_decision: str
    receipt_hash: str
    replay_verified: bool
    contains_verified: bool
    receipt_path: Path
    passed: bool


def load_seed_tasks(seed_dir: Path = DEFAULT_SEED_DIR) -> list[SeedTask]:
    tasks: list[SeedTask] = []
    for path in sorted(seed_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        tasks.append(
            SeedTask(
                id=str(payload["id"]),
                title=str(payload["title"]),
                input=str(payload["input"]),
                expected_decision=str(payload["expected_decision"]),
                expected_contains=[
                    str(item) for item in payload.get("expected_contains", [])
                ],
                notes=str(payload.get("notes", "")),
            )
        )
    return tasks


def run_seed_suite(
    *,
    seed_dir: Path = DEFAULT_SEED_DIR,
    receipt_dir: Path = DEFAULT_RECEIPT_DIR,
) -> list[SeedRunResult]:
    receipt_dir.mkdir(parents=True, exist_ok=True)
    results: list[SeedRunResult] = []
    for task in load_seed_tasks(seed_dir):
        receipt_name = _receipt_filename(task.id)
        graph = UniversalLivingGraph(auto_load=False)
        kernel = TSKernel(graph=graph)
        transaction = kernel.transact(task.input)
        receipt = transaction.receipt
        receipt_path = receipt_dir / receipt_name
        receipt_path.write_text(
            json.dumps(receipt.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        replay_verified = False
        try:
            replay_graph = UniversalLivingGraph(auto_load=False)
            replay_verified = replay_receipt(
                replay_graph, receipt
            ) == receipt.post_state_hash and validate_receipt_hash(receipt)
        except Exception:
            replay_verified = False

        actual_decision = receipt.commit_decision
        contains_verified = _expected_strings_present(task, receipt.to_dict())
        passed = (
            actual_decision == task.expected_decision
            and replay_verified
            and contains_verified
        )
        results.append(
            SeedRunResult(
                task=task,
                actual_decision=actual_decision,
                receipt_hash=receipt.receipt_hash,
                replay_verified=replay_verified,
                contains_verified=contains_verified,
                receipt_path=receipt_path,
                passed=passed,
            )
        )
    return results


def print_summary(results: list[SeedRunResult]) -> None:
    print("task_id | expected | actual | receipt_hash | replay_verified | pass/fail")
    for result in results:
        print(
            " | ".join(
                [
                    result.task.id,
                    result.task.expected_decision,
                    result.actual_decision,
                    result.receipt_hash[:16],
                    str(result.replay_verified).lower(),
                    "pass" if result.passed else "fail",
                ]
            )
        )


def _expected_strings_present(task: SeedTask, receipt: dict[str, Any]) -> bool:
    if not task.expected_contains:
        return True
    searchable = json.dumps(receipt, sort_keys=True).lower()
    return all(fragment.lower() in searchable for fragment in task.expected_contains)


def _receipt_filename(task_id: str) -> str:
    if not SAFE_TASK_ID.fullmatch(task_id):
        raise ValueError(
            f"unsafe seed task id {task_id!r}; use letters, digits, dot, dash or underscore"
        )
    return f"{task_id}.receipt.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Kernel v0.2 hard seed tasks and replay their receipts."
    )
    parser.add_argument(
        "--seed-dir",
        type=Path,
        default=DEFAULT_SEED_DIR,
        help="directory containing seed task JSON files",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_RECEIPT_DIR,
        help="directory for receipt JSON artifacts",
    )
    args = parser.parse_args(argv)

    results = run_seed_suite(seed_dir=args.seed_dir, receipt_dir=args.output_dir)
    print_summary(results)
    return 0 if all(result.passed for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
