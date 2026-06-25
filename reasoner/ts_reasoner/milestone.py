"""Milestone receipt helpers for TS-Reasoner.

The milestone receipt is a public summary artifact. It does not grant proof
authority to generated text, model confidence, or external benchmark labels.
Typed verifier channels remain proof authority.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECEIPT_PATH = ROOT / "artifacts/v4_5_milestone_receipt_pack.json"


def load_milestone_receipt(path: str | Path = DEFAULT_RECEIPT_PATH) -> dict[str, Any]:
    receipt_path = Path(path)
    if not receipt_path.exists():
        raise FileNotFoundError(f"milestone receipt not found: {receipt_path}")
    return json.loads(receipt_path.read_text(encoding="utf-8"))


def milestone_summary(data: dict[str, Any]) -> str:
    gates = data.get("gates", {})

    lines = [
        "TS-Reasoner Milestone Receipt",
        "=============================",
        f"version: {data.get('version')}",
        f"claim: {data.get('claim')}",
        "",
        "headline:",
        f"- input reports: {data.get('input_report_count')}",
        f"- known cases: {data.get('total_known_cases')}",
        f"- known candidates: {data.get('total_known_candidates')}",
        f"- wrong accepts: {data.get('wrong_accept_total')}",
        f"- accepted without typed support: {data.get('accepted_without_typed_support_total')}",
        f"- candidate graph contamination: {data.get('candidate_graph_contamination_total')}",
        f"- all gates passed: {gates.get('all_gates_passed')}",
        "",
        "boundary:",
        f"- confidence is not proof: {data.get('confidence_is_not_proof')}",
        f"- generated text is not proof: {data.get('generated_text_is_not_proof')}",
        f"- typed verifier is proof authority: {data.get('typed_verifier_is_proof_authority')}",
        f"- external benchmark victory claim: {data.get('external_benchmark_victory_claim')}",
        f"- broad NLP claim: {data.get('broad_nlp_claim')}",
        f"- GPT-2 superiority claim: {data.get('gpt2_superiority_claim')}",
        f"- live TensionLM runtime claim: {data.get('live_tensionlm_runtime_claim')}",
    ]

    return "\n".join(lines)


def print_milestone_receipt(path: str | Path = DEFAULT_RECEIPT_PATH) -> str:
    return milestone_summary(load_milestone_receipt(path))


def main() -> int:
    print(print_milestone_receipt())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
