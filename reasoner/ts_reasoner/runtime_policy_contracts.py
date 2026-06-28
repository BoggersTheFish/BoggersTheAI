from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable

from ts_reasoner.runtime_kernel import VerifierFirstRuntimeKernel

POLICY_CONTRACT_SCHEMA = "ts_reasoner_runtime_policy_contracts_v1"

ACTION_CONTRACTS: dict[str, dict[str, Any]] = {
    "quarantine": {
        "required_state_keys": ["quarantined_claims", "patches"],
        "required_receipt_keys": [
            "action",
            "accepted_common_ground_mutated_by_candidate",
            "candidate_graph_contamination_count",
            "typed_verifier_support_remains_proof_boundary",
        ],
        "candidate_may_mutate_accepted_common_ground": False,
    },
    "open_repair": {
        "required_state_keys": ["repair_targets", "patches"],
        "required_receipt_keys": [
            "action",
            "accepted_common_ground_mutated_by_candidate",
            "candidate_graph_contamination_count",
            "typed_verifier_support_remains_proof_boundary",
        ],
        "candidate_may_mutate_accepted_common_ground": False,
    },
    "branch_world": {
        "required_state_keys": ["branch_worlds", "patches"],
        "required_receipt_keys": [
            "action",
            "accepted_common_ground_mutated_by_candidate",
            "candidate_graph_contamination_count",
            "typed_verifier_support_remains_proof_boundary",
        ],
        "candidate_may_mutate_accepted_common_ground": False,
    },
    "quarantine_pack": {
        "required_state_keys": ["quarantined_claims", "patches"],
        "required_receipt_keys": [
            "action",
            "accepted_common_ground_mutated_by_candidate",
            "candidate_graph_contamination_count",
            "typed_verifier_support_remains_proof_boundary",
        ],
        "candidate_may_mutate_accepted_common_ground": False,
    },
    "pack_checked": {
        "required_state_keys": ["patches"],
        "required_receipt_keys": [
            "action",
            "accepted_common_ground_mutated_by_candidate",
            "candidate_graph_contamination_count",
            "typed_verifier_support_remains_proof_boundary",
        ],
        "candidate_may_mutate_accepted_common_ground": False,
    },
    "abstain": {
        "required_state_keys": ["accepted_claims"],
        "required_receipt_keys": [
            "action",
            "accepted_common_ground_mutated_by_candidate",
            "candidate_graph_contamination_count",
            "typed_verifier_support_remains_proof_boundary",
        ],
        "candidate_may_mutate_accepted_common_ground": False,
    },
    "checkpoint": {
        "required_checkpoint_keys": [
            "schema",
            "case_id",
            "state",
            "actions",
            "ledger",
            "head_hash",
        ],
        "candidate_may_mutate_accepted_common_ground": False,
    },
    "restore": {
        "required_restore_keys": ["restored_state"],
        "candidate_may_mutate_accepted_common_ground": False,
    },
}


@dataclass(frozen=True)
class RuntimePolicyContractResult:
    case_id: str
    action: str
    contract_valid: bool
    missing_state_keys: list[str]
    missing_receipt_keys: list[str]
    candidate_graph_contamination_count: int
    explanation: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def policy_contract_document() -> dict[str, Any]:
    return {
        "schema": POLICY_CONTRACT_SCHEMA,
        "contracts": ACTION_CONTRACTS,
        "proof_boundary": {
            "candidate_generation_is_proof": False,
            "generated_text_is_proof": False,
            "model_confidence_is_proof": False,
            "typed_verifier_support_remains_proof_boundary": True,
        },
    }


def validate_runtime_action_contract(
    case_id: str,
    action: str,
    state: dict[str, Any],
    receipt: dict[str, Any],
    contamination: int,
) -> RuntimePolicyContractResult:
    contract = ACTION_CONTRACTS.get(action)
    if contract is None:
        return RuntimePolicyContractResult(
            case_id=case_id,
            action=action,
            contract_valid=False,
            missing_state_keys=[],
            missing_receipt_keys=[],
            candidate_graph_contamination_count=contamination,
            explanation="Runtime action is not declared in the policy contract document.",
        )

    required_state = [str(key) for key in contract.get("required_state_keys", [])]
    required_receipt = [str(key) for key in contract.get("required_receipt_keys", [])]
    missing_state = [key for key in required_state if key not in state]
    missing_receipt = [key for key in required_receipt if key not in receipt]

    boundary_ok = (
        receipt.get("accepted_common_ground_mutated_by_candidate") is False
        and receipt.get("typed_verifier_support_remains_proof_boundary") is True
        and int(receipt.get("candidate_graph_contamination_count", contamination)) == 0
        and contamination == 0
    )

    contract_valid = not missing_state and not missing_receipt and boundary_ok

    return RuntimePolicyContractResult(
        case_id=case_id,
        action=action,
        contract_valid=contract_valid,
        missing_state_keys=missing_state,
        missing_receipt_keys=missing_receipt,
        candidate_graph_contamination_count=contamination,
        explanation="Runtime action was checked against an explicit policy contract.",
    )


def evaluate_policy_contract_cases(
    cases: Iterable[dict[str, Any]],
) -> dict[str, object]:
    kernel = VerifierFirstRuntimeKernel()
    results = []
    passed = 0
    total = 0
    contamination = 0

    for raw in cases:
        total += 1
        result = kernel.process_event(
            event=dict(raw["event"]),
            state=dict(raw["initial_state"]),
            case_id=str(raw["case_id"]),
        )
        contract = validate_runtime_action_contract(
            case_id=str(raw["case_id"]),
            action=result.action,
            state=result.state,
            receipt=result.receipt,
            contamination=result.candidate_graph_contamination_count,
        )

        expected_action = str(raw["expected_action"])
        expected_contract_valid = bool(raw["expected_contract_valid"])
        expected_contamination = int(
            raw["expected_candidate_graph_contamination_count"]
        )

        case_passed = (
            result.action == expected_action
            and contract.contract_valid == expected_contract_valid
            and contract.candidate_graph_contamination_count == expected_contamination
        )

        if case_passed:
            passed += 1

        contamination += contract.candidate_graph_contamination_count
        row = contract.to_dict()
        row["expected_action"] = expected_action
        row["expected_contract_valid"] = expected_contract_valid
        row["passed"] = case_passed
        results.append(row)

    return {
        "release": "v9.8.0",
        "case_count": total,
        "passed_cases": passed,
        "failed_cases": total - passed,
        "runtime_policy_contract_accuracy": passed / total if total else 0.0,
        "contract_schema": POLICY_CONTRACT_SCHEMA,
        "candidate_graph_contamination_count": contamination,
        "all_gates_passed": total > 0 and passed == total and contamination == 0,
        "results": results,
    }
