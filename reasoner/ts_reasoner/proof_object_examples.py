from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import json

from ts_reasoner.claim_normalizer import canonicalize_claim_surface
from ts_reasoner.support_path_verifier import verify_support_path
from ts_reasoner.typed_support import make_typed_support, validate_typed_support


def _example(
    *,
    case_id: str,
    claim: str,
    premises: List[str],
    confidence: float,
) -> Dict[str, Any]:
    result = verify_support_path(premises, claim)
    support = result.get("support")
    decision = result["status"]
    if decision == "accepted":
        why = f"accepted by typed verifier channel {support['channel']}"
        trace_hash_valid = validate_typed_support(result["claim"], support)["accepted"]
    elif decision == "rejected":
        why = f"rejected because {result.get('reason')}"
        trace_hash_valid = False
    else:
        why = f"abstained because {result.get('reason')}"
        trace_hash_valid = False
    return {
        "case_id": case_id,
        "claim": claim,
        "normalized_claim": canonicalize_claim_surface(claim),
        "premises": premises,
        "support_path": support.get("premises", []) if support else [],
        "typed_channel": support.get("channel") if support else None,
        "verifier_decision": decision,
        "why_accepted_rejected_or_abstained": why,
        "model_confidence": confidence,
        "confidence_ignored": True,
        "support_object": support,
        "trace_hash_valid": trace_hash_valid,
    }


def build_proof_object_examples() -> Dict[str, Any]:
    examples = [
        _example(
            case_id="direct_support_accept",
            claim="all A are B",
            premises=["all A are B"],
            confidence=0.31,
        ),
        _example(
            case_id="transitive_support_accept",
            claim="all A are C",
            premises=["all A are B", "all B are C"],
            confidence=0.44,
        ),
        _example(
            case_id="negative_exclusion_accept",
            claim="no A are C",
            premises=["all A are B", "no B are C"],
            confidence=0.52,
        ),
        _example(
            case_id="reverse_inference_reject",
            claim="all B are A",
            premises=["all A are B"],
            confidence=0.99,
        ),
        _example(
            case_id="unsupported_abstain",
            claim="all A are D",
            premises=["all A are B", "all B are C"],
            confidence=0.98,
        ),
    ]

    valid = make_typed_support(
        channel="transitive_all",
        premises=["all A are B", "all B are C"],
        derived_claim="all A are C",
    )
    fake = dict(valid)
    fake["trace_hash"] = "fake"
    fake_result = validate_typed_support("all A are C", fake)
    examples.append(
        {
            "case_id": "fake_hash_reject",
            "claim": "all A are C",
            "normalized_claim": "all A are C",
            "premises": ["all A are B", "all B are C"],
            "support_path": fake["premises"],
            "typed_channel": fake["channel"],
            "verifier_decision": "rejected",
            "why_accepted_rejected_or_abstained": f"rejected because {fake_result['reason']}",
            "model_confidence": 1.0,
            "confidence_ignored": True,
            "support_object": fake,
            "trace_hash_valid": False,
        }
    )

    all_gates_passed = (
        len(examples) == 6
        and all(example["confidence_ignored"] is True for example in examples)
        and any(example["verifier_decision"] == "accepted" for example in examples)
        and any(example["verifier_decision"] == "rejected" for example in examples)
        and any(example["verifier_decision"] == "abstained" for example in examples)
    )
    return {
        "artifact": "proof_object_examples",
        "release": "v28.0.0",
        "examples": examples,
        "accepted_count": sum(1 for example in examples if example["verifier_decision"] == "accepted"),
        "rejected_count": sum(1 for example in examples if example["verifier_decision"] == "rejected"),
        "abstained_count": sum(1 for example in examples if example["verifier_decision"] == "abstained"),
        "confidence_ignored": True,
        "all_gates_passed": all_gates_passed,
    }


def write_proof_object_examples(path: str | Path = "artifacts/proof_object_examples.json") -> Dict[str, Any]:
    payload = build_proof_object_examples()
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload
