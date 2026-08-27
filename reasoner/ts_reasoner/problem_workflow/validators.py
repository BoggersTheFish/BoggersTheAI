"""Independent, top-level PRIME verifier callbacks for problem analysis.

These functions perform no I/O, dynamic import, reflection, or mutation.  They
are intentionally ordinary top-level functions so PRIME can fingerprint their
code and every referenced helper at boot.
"""

from __future__ import annotations

import unicodedata
from typing import Any

from prime_v19 import VerifierFinding

from .advice import (
    advice_record_is_valid,
    expected_v18_worker_request_hash,
)
from .canonical import canonical_tree_is_valid, workflow_stable_hash
from .projection import expected_constraint_field, focus_from_field


WORKFLOW_BOUNDARY_OBLIGATION = "workflow_boundary_v1"
CONSTRAINT_FIELD_OBLIGATION = "constraint_field_integrity_v1"
PROVENANCE_OBLIGATION = "provenance_binding_v1"
REPRESENTATION_ECONOMICS_OBLIGATION = "representation_economics_v1"
PROBLEM_NODE_KIND = "ts.problem_analysis"
_EVIDENCE_KEYS = frozenset(
    {
        "schema",
        "obligation_id",
        "proposal_hash",
        "problem_spec",
        "problem_spec_hash",
        "constraint_field",
        "constraint_field_hash",
        "focus",
        "focus_hash",
        "advice",
        "advice_hash",
        "provenance",
        "provenance_hash",
        "parent_binding",
        "node_id",
        "node_kind",
        "node_payload",
        "node_payload_hash",
        "mutation_intent",
        "mutation_intent_hash",
    }
)
_FORBIDDEN_NODE_KEYS = frozenset(
    {
        "bytecode",
        "code",
        "command",
        "delete",
        "edges",
        "executable",
        "operations",
        "overwrite",
        "representation",
        "representation_transition",
    }
)


def _fail(reason: str) -> VerifierFinding:
    return VerifierFinding.fail(reason)


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _valid_text(value: Any, *, maximum: int = 4096) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and value == value.strip()
        and "\x00" not in value
        and value == unicodedata.normalize("NFC", value)
        and len(value.encode("utf-8")) <= maximum
    )


def _valid_text_list(value: Any, *, required: bool) -> bool:
    return (
        isinstance(value, list)
        and len(value) <= 32
        and (bool(value) or not required)
        and all(_valid_text(item) for item in value)
        and len(set(value)) == len(value)
    )


def _valid_problem_id(value: Any) -> bool:
    allowed = "abcdefghijklmnopqrstuvwxyz0123456789_"
    return (
        isinstance(value, str)
        and 1 <= len(value) <= 128
        and value[0] in "abcdefghijklmnopqrstuvwxyz0123456789"
        and all(character in allowed for character in value)
    )


def problem_spec_is_valid(spec: Any) -> bool:
    if not isinstance(spec, dict) or set(spec) != {
        "schema",
        "problem_id",
        "question",
        "context",
        "constraints",
        "desired_outcomes",
        "failure_modes",
        "testable_predictions",
        "scope",
        "provenance",
    }:
        return False
    return (
        spec["schema"] == "boggers-ts-problem-spec-v1"
        and _valid_problem_id(spec["problem_id"])
        and _valid_text(spec["question"])
        and _valid_text_list(spec["context"], required=False)
        and _valid_text_list(spec["constraints"], required=True)
        and _valid_text_list(spec["desired_outcomes"], required=True)
        and _valid_text_list(spec["failure_modes"], required=True)
        and _valid_text_list(spec["testable_predictions"], required=True)
        and _valid_text(spec["scope"])
        and isinstance(spec["provenance"], dict)
        and canonical_tree_is_valid(spec["provenance"])
    )


def parent_binding_is_valid(binding: Any) -> bool:
    return (
        isinstance(binding, dict)
        and set(binding)
        == {
            "graph_lineage_id",
            "parent_root",
            "parent_authority_hash",
            "expected_sequence",
        }
        and _valid_text(binding["graph_lineage_id"], maximum=256)
        and _is_sha256(binding["parent_root"])
        and _is_sha256(binding["parent_authority_hash"])
        and isinstance(binding["expected_sequence"], int)
        and not isinstance(binding["expected_sequence"], bool)
        and binding["expected_sequence"] > 0
    )


def expected_provenance(evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "boggers-ts-problem-provenance-v1",
        "producer": "BoggersTheAI.reasoner.ts_reasoner.problem_workflow",
        "workflow_version": "19.1",
        "projection": "existing_constraint_fields_structured_projection_v1",
        "semantic_claim": "DETERMINISTIC_ANALYSIS_NOT_WORLD_TRUTH",
        "problem_spec_hash": evidence["problem_spec_hash"],
        "constraint_field_hash": evidence["constraint_field_hash"],
        "focus_hash": evidence["focus_hash"],
        "advice_hash": evidence["advice_hash"],
        "advice_top_k": evidence["advice"]["top_k"],
        "advice_mount_receipt_hash": workflow_stable_hash(
            evidence["advice"]["description"]
        ),
        "parent_binding": evidence["parent_binding"],
    }


def expected_canonical_provenance(evidence: dict[str, Any]) -> dict[str, Any]:
    """Stable semantic provenance; excludes transaction/advice observations."""

    return {
        "schema": "boggers-ts-problem-canonical-provenance-v1",
        "producer": "BoggersTheAI.reasoner.ts_reasoner.problem_workflow",
        "workflow_version": "19.1",
        "projection": "existing_constraint_fields_structured_projection_v1",
        "semantic_claim": "DETERMINISTIC_ANALYSIS_NOT_WORLD_TRUTH",
        "problem_spec_hash": evidence["problem_spec_hash"],
        "constraint_field_hash": evidence["constraint_field_hash"],
        "focus_hash": evidence["focus_hash"],
    }


def expected_node_payload(evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "boggers-ts-problem-analysis-v1",
        "semantics": "DETERMINISTIC_ANALYSIS_NOT_WORLD_TRUTH",
        "analysis": {
            "problem_spec": evidence["problem_spec"],
            "constraint_field": evidence["constraint_field"],
            "focus": evidence["focus"],
            "canonical_provenance": expected_canonical_provenance(evidence),
            "advice_boundary": {
                "schema": "boggers-ts-problem-advice-boundary-v1",
                "semantic_authority": "NONE",
                "canonical_influence": False,
                "semantic_use": "RECEIPT_EVIDENCE_ONLY",
            },
        },
        "bindings": {
            "problem_spec_hash": evidence["problem_spec_hash"],
            "constraint_field_hash": evidence["constraint_field_hash"],
            "focus_hash": evidence["focus_hash"],
        },
        "authority_boundary": {
            "schema": "boggers-ts-problem-authority-boundary-v1",
            "canonical_change": "ADD_ONLY_SINGLE_NODE",
            "node_kind": PROBLEM_NODE_KIND,
            "canonical_writer": "PRIME_V19_AUTHORITY_KERNEL",
            "semantic_authority": "DETERMINISTIC_ANALYSIS_ONLY",
            "world_truth_claimed": False,
            "representation_change": "FORBIDDEN",
            "execution": "FORBIDDEN",
        },
    }


def expected_mutation_intent(evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "boggers-ts-problem-mutation-intent-v1",
        "operation": "ADD_ONLY_SINGLE_NODE",
        "node_id": evidence["node_id"],
        "node_kind": evidence["node_kind"],
        "node_payload_hash": evidence["node_payload_hash"],
        "parent_binding": evidence["parent_binding"],
    }


def evidence_bundle_hash(evidence: dict[str, Any]) -> str:
    """Commit the shared evidence view while excluding per-envelope/cyclic fields."""

    shared = {
        key: value
        for key, value in evidence.items()
        if key not in {"obligation_id", "proposal_hash"}
    }
    return workflow_stable_hash(shared)


def expected_proposal_metadata(evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "boggers-ts-problem-proposal-metadata-v1",
        "problem_spec_hash": evidence["problem_spec_hash"],
        "constraint_field_hash": evidence["constraint_field_hash"],
        "focus_hash": evidence["focus_hash"],
        "advice_hash": evidence["advice_hash"],
        "node_payload_hash": evidence["node_payload_hash"],
        "evidence_bundle_hash": evidence_bundle_hash(evidence),
        "mutation": "ADD_ONLY_SINGLE_NODE",
        "semantic_claim": "DETERMINISTIC_ANALYSIS_NOT_WORLD_TRUTH",
    }


def _common_evidence_valid(context: Any, evidence: Any, config: Any) -> bool:
    if not isinstance(evidence, dict) or set(evidence) != _EVIDENCE_KEYS:
        return False
    if not isinstance(config, dict) or set(config) != {"obligation_id"}:
        return False
    proposal = context.proposal
    binding = evidence["parent_binding"]
    return (
        evidence["schema"] == "boggers-ts-problem-evidence-v1"
        and evidence["obligation_id"] == config["obligation_id"]
        and evidence["proposal_hash"] == proposal.proposal_hash
        and evidence["node_kind"] == PROBLEM_NODE_KIND
        and evidence["node_id"]
        == f"ts.problem_analysis:{evidence['problem_spec_hash']}"
        and _valid_text(evidence["node_id"], maximum=256)
        and all(
            _is_sha256(evidence[key])
            for key in (
                "problem_spec_hash",
                "constraint_field_hash",
                "focus_hash",
                "advice_hash",
                "provenance_hash",
                "node_payload_hash",
                "mutation_intent_hash",
            )
        )
        and parent_binding_is_valid(binding)
        and binding["graph_lineage_id"] == proposal.graph_lineage_id
        and binding["parent_root"] == proposal.parent_root
        and binding["parent_authority_hash"] == proposal.parent_authority_hash
        and binding["expected_sequence"] == proposal.expected_sequence
        and proposal.expected_sequence == context.logical_sequence
        and proposal.metadata == expected_proposal_metadata(evidence)
        and canonical_tree_is_valid(evidence)
    )


def _contains_forbidden_node_key(value: Any) -> bool:
    if isinstance(value, list):
        return any(_contains_forbidden_node_key(item) for item in value)
    if not isinstance(value, dict):
        return False
    if any(key in _FORBIDDEN_NODE_KEYS for key in value):
        return True
    return any(_contains_forbidden_node_key(item) for item in value.values())


def workflow_boundary_v1(context: Any, evidence: Any, config: Any) -> VerifierFinding:
    """Admit exactly one new non-executable semantic-analysis node."""

    if not _common_evidence_valid(context, evidence, config):
        return _fail("workflow evidence envelope is invalid")
    if config["obligation_id"] != WORKFLOW_BOUNDARY_OBLIGATION:
        return _fail("workflow obligation configuration mismatch")
    proposal = context.proposal
    if proposal.scope.value != "deterministic_semantic_commit":
        return _fail("problem analysis requires deterministic semantic scope")
    if len(proposal.operations) != 1 or len(proposal.affected_nodes) != 1:
        return _fail("problem analysis must contain exactly one operation")
    operation = proposal.operations[0]
    if operation.op != "upsert_node":
        return _fail("problem analysis must use one node upsert")
    body = operation.body
    if set(body) != {"node_id", "kind", "payload"}:
        return _fail("problem node operation has an unknown shape")
    if (
        body["node_id"] != evidence["node_id"]
        or body["kind"] != PROBLEM_NODE_KIND
        or proposal.affected_nodes != (evidence["node_id"],)
    ):
        return _fail("problem node identity binding failed")
    if context.snapshot.node(evidence["node_id"]) is not None:
        return _fail("problem analysis is add-only and the node already exists")
    if _contains_forbidden_node_key(body["payload"]):
        return _fail("problem node contains a forbidden authority surface")
    if body["payload"] != evidence["node_payload"]:
        return _fail("proposal node payload differs from evidence")
    if evidence["node_payload"] != expected_node_payload(evidence):
        return _fail("problem node payload is not the bounded canonical shape")
    if workflow_stable_hash(evidence["node_payload"]) != evidence["node_payload_hash"]:
        return _fail("problem node payload hash mismatch")
    if evidence["mutation_intent"] != expected_mutation_intent(evidence):
        return _fail("mutation intent is not add-only and exact")
    if (
        workflow_stable_hash(evidence["mutation_intent"])
        != evidence["mutation_intent_hash"]
    ):
        return _fail("mutation intent hash mismatch")
    if proposal.mutation_intent_hash != evidence["mutation_intent_hash"]:
        return _fail("proposal mutation binding mismatch")
    if proposal.metadata != expected_proposal_metadata(evidence):
        return _fail("proposal metadata binding mismatch")
    return VerifierFinding.pass_("single add-only problem-analysis node verified")


def constraint_field_integrity_v1(
    context: Any, evidence: Any, config: Any
) -> VerifierFinding:
    """Recompute the exact field projection and active frontier."""

    if not _common_evidence_valid(context, evidence, config):
        return _fail("constraint-field evidence envelope is invalid")
    if config["obligation_id"] != CONSTRAINT_FIELD_OBLIGATION:
        return _fail("constraint-field obligation configuration mismatch")
    spec = evidence["problem_spec"]
    if not problem_spec_is_valid(spec):
        return _fail("problem specification failed bounded validation")
    if workflow_stable_hash(spec) != evidence["problem_spec_hash"]:
        return _fail("problem specification hash mismatch")
    expected_field = expected_constraint_field(spec)
    if evidence["constraint_field"] != expected_field:
        return _fail("constraint field differs from deterministic projection")
    if workflow_stable_hash(expected_field) != evidence["constraint_field_hash"]:
        return _fail("constraint field hash mismatch")
    expected_focus = focus_from_field(expected_field)
    if evidence["focus"] != expected_focus:
        return _fail("active constraint frontier was not recomputed exactly")
    if workflow_stable_hash(expected_focus) != evidence["focus_hash"]:
        return _fail("constraint focus hash mismatch")
    analysis = evidence["node_payload"]["analysis"]
    if (
        analysis["problem_spec"] != spec
        or analysis["constraint_field"] != expected_field
        or analysis["focus"] != expected_focus
    ):
        return _fail("node analysis does not bind the recomputed field")
    return VerifierFinding.pass_("deterministic constraint-field projection verified")


def provenance_binding_v1(context: Any, evidence: Any, config: Any) -> VerifierFinding:
    """Bind source, sealed-v18 proposal evidence, parent, and exact payload."""

    if not _common_evidence_valid(context, evidence, config):
        return _fail("provenance evidence envelope is invalid")
    if config["obligation_id"] != PROVENANCE_OBLIGATION:
        return _fail("provenance obligation configuration mismatch")
    if not advice_record_is_valid(evidence["advice"]):
        return _fail("sealed-v18 advice violated its proposal-only contract")
    advice = evidence["advice"]
    if advice["mode"] == "PRESENT":
        if advice["proposal_batch"]["request_hash"] != expected_v18_worker_request_hash(
            evidence["problem_spec"]["question"], advice["top_k"]
        ):
            return _fail("sealed-v18 worker request is not problem/top-k bound")
    if workflow_stable_hash(advice) != evidence["advice_hash"]:
        return _fail("sealed-v18 advice hash mismatch")
    provenance = expected_provenance(evidence)
    if evidence["provenance"] != provenance:
        return _fail("workflow provenance was not recomputed exactly")
    if workflow_stable_hash(provenance) != evidence["provenance_hash"]:
        return _fail("workflow provenance hash mismatch")
    if context.proposal.provenance_hash != evidence["provenance_hash"]:
        return _fail("proposal provenance binding mismatch")
    analysis = evidence["node_payload"]["analysis"]
    if analysis["canonical_provenance"] != expected_canonical_provenance(evidence):
        return _fail("node canonical provenance mismatch")
    if analysis["advice_boundary"] != {
        "schema": "boggers-ts-problem-advice-boundary-v1",
        "semantic_authority": "NONE",
        "canonical_influence": False,
        "semantic_use": "RECEIPT_EVIDENCE_ONLY",
    }:
        return _fail("node advice boundary permits canonical influence")
    return VerifierFinding.pass_("problem provenance and proposal-only advice verified")


def representation_economics_v1(
    context: Any, evidence: Any, config: Any
) -> VerifierFinding:
    """Registered fail-closed economics verifier; this workflow has no such path."""

    del context, evidence
    if not isinstance(config, dict) or config != {
        "obligation_id": REPRESENTATION_ECONOMICS_OBLIGATION
    }:
        return _fail("representation economics configuration mismatch")
    return VerifierFinding.fail(
        "problem-analysis workflow forbids representation transitions"
    )
