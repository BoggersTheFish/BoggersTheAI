"""Canonical kernel demonstration CLI."""

from __future__ import annotations

import argparse
import json
from typing import Any

from ..graph.universal_living_graph import UniversalLivingGraph
from .kernel import TSKernel
from .replay import replay_receipt
from .transaction import TransactionResult

VALID = """All mammals are warm-blooded.
Whales are mammals.
Prove that whales are warm-blooded."""

INVALID = """All mammals are warm-blooded.
Whales are warm-blooded.
Prove that all warm-blooded things are mammals."""

CONTRADICTION = """All mammals are warm-blooded.
Whales are mammals.
Whales are not warm-blooded.
Determine the current status of the claim that whales are warm-blooded."""

REVISION_1 = """All mammals are warm-blooded.
Whales are mammals."""

REVISION_2 = """Introduce stronger authoritative evidence that the current representation of
whales refers to mechanical devices named Whales, not biological animals."""


def _label(entity_id: str) -> str:
    label = entity_id.split(":", 2)[-1].replace("_", "-")
    if label == "whale":
        return "whales"
    return label


def _claim_text(claim: dict) -> str:
    subject = _label(str(claim.get("subject", "")))
    obj = _label(str(claim.get("object", "")))
    predicate = str(claim.get("predicate", ""))
    if predicate == "has_property":
        text = f"{subject} are {obj}"
    elif predicate == "is_a":
        text = f"{subject} are {obj}s"
    elif predicate == "implies_property":
        text = f"all {subject}s are {obj}"
    else:
        text = f"{subject} {predicate} {obj}"
    if claim.get("polarity") == "negative":
        text = text.replace(" are ", " are not ", 1)
    return text


KernelDemoResult = TransactionResult | dict[str, Any]


def _run_cases() -> list[tuple[str, KernelDemoResult]]:
    graph = UniversalLivingGraph(auto_load=False)
    kernel = TSKernel(graph=graph)
    cases: list[tuple[str, KernelDemoResult]] = []
    for name, text in (
        ("valid syllogism", VALID),
        ("invalid converse", INVALID),
        ("contradiction", CONTRADICTION),
    ):
        cases.append((name, kernel.transact(text)))

    revision_graph = UniversalLivingGraph(auto_load=False)
    revision_kernel = TSKernel(graph=revision_graph)
    revision_kernel.transact(REVISION_1)
    cases.append(("representation revision", revision_kernel.transact(REVISION_2)))

    replay_graph = UniversalLivingGraph(auto_load=False)
    first_result = cases[0][1]
    if not isinstance(first_result, TransactionResult):
        raise AssertionError("valid demo case did not return a transaction result")
    replay_post = replay_receipt(replay_graph, first_result.receipt)
    cases.append(("deterministic replay", {"post_state_hash": replay_post}))
    return cases


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run canonical TS kernel demo.")
    parser.add_argument(
        "--json", action="store_true", help="emit full receipts as JSON"
    )
    args = parser.parse_args(argv)

    cases = _run_cases()
    if args.json:
        payload = []
        for name, result in cases:
            if isinstance(result, TransactionResult):
                payload.append({"case": name, "receipt": result.receipt.to_dict()})
            else:
                payload.append({"case": name, "result": result})
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    for name, result in cases:
        print(f"CASE: {name}")
        if isinstance(result, TransactionResult):
            receipt = result.receipt
            print(f"DECISION: {receipt.commit_decision.upper()}")
            if receipt.derived_claims:
                print(f"CLAIM: {_claim_text(receipt.derived_claims[-1])}")
            for verification in receipt.verification_results:
                if verification["verifier_type"] in {"syllogism", "bogvm_execution"}:
                    print(
                        "VERIFIER: "
                        f"{verification['verifier_type']}/{verification['outcome']}"
                    )
            if receipt.BOGVM_artifacts:
                artifact = receipt.BOGVM_artifacts[-1]
                print(
                    "BOGVM: "
                    f"execution_completed={artifact.get('execution_completed')}"
                )
                print(
                    "PROOF_OBLIGATION_SATISFIED: "
                    f"{artifact.get('proof_obligation_satisfied')}"
                )
            print(f"BASE_HASH: {receipt.base_graph_hash}")
            print(f"POST_HASH: {receipt.post_state_hash}")
            if receipt.commit_decision == "reject":
                changed = receipt.base_graph_hash != receipt.post_state_hash
                print(f"PERSISTENT_STATE_CHANGED: {str(changed).lower()}")
            print(f"RECEIPT: {receipt.receipt_hash}")
            print(f"REASON: {receipt.commit_reason}")
        else:
            print(f"POST_HASH: {result['post_state_hash']}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
