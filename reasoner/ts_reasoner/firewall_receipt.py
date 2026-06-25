"""CLI helpers for the v5.0 verifier-first reasoning firewall receipt."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIREWALL_RECEIPT_PATH = ROOT / "artifacts/v5_0_reasoning_firewall_receipt.json"


def load_firewall_receipt(path: str | Path = DEFAULT_FIREWALL_RECEIPT_PATH) -> dict[str, Any]:
    receipt_path = Path(path)
    if not receipt_path.exists():
        raise FileNotFoundError(f"reasoning firewall receipt not found: {receipt_path}")
    return json.loads(receipt_path.read_text(encoding="utf-8"))


def firewall_summary(data: dict[str, Any]) -> str:
    gates = data.get("gates", {})

    lines = [
        "TS-Reasoner Verifier-First Reasoning Firewall",
        "================================================",
        f"version: {data.get('version')}",
        f"claim: {data.get('claim')}",
        "",
        "headline:",
        f"- input reports: {data.get('input_report_count')}",
        f"- total cases: {data.get('total_cases')}",
        f"- total candidates: {data.get('total_candidates')}",
        f"- verifier confidence overrides: {data.get('total_verifier_overrides')}",
        f"- unsupported-claim candidates: {data.get('total_unsupported_claim_candidate_count')}",
        f"- wrong accepts: {data.get('wrong_accept_total')}",
        f"- accepted without typed support: {data.get('accepted_without_typed_support_total')}",
        f"- accepted with unsupported claims: {data.get('accepted_with_unsupported_claims_total')}",
        f"- candidate graph contamination: {data.get('candidate_graph_contamination_total')}",
        f"- all gates passed: {gates.get('all_gates_passed')}",
        "",
        "boundary:",
        f"- confidence is not proof: {data.get('confidence_is_not_proof')}",
        f"- generated text is not proof: {data.get('generated_text_is_not_proof')}",
        f"- candidate source is not proof: {data.get('candidate_source_is_not_proof')}",
        f"- typed verifier is proof authority: {data.get('typed_verifier_is_proof_authority')}",
        f"- candidate claims do not contaminate graph: {data.get('candidate_claims_do_not_contaminate_graph')}",
        f"- broad NLP claim: {data.get('broad_nlp_claim')}",
        f"- general theorem proving claim: {data.get('general_theorem_proving_claim')}",
        f"- external benchmark victory claim: {data.get('external_benchmark_victory_claim')}",
        f"- live TensionLM runtime claim: {data.get('live_tensionlm_runtime_claim')}",
    ]

    return "\n".join(lines)


def print_firewall_receipt(path: str | Path = DEFAULT_FIREWALL_RECEIPT_PATH) -> str:
    return firewall_summary(load_firewall_receipt(path))


def main() -> int:
    print(print_firewall_receipt())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
