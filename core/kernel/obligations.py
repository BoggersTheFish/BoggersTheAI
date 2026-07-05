"""Typed verifier channels for the canonical kernel."""

from __future__ import annotations

import sys
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Protocol

from .arithmetic import ArithmeticParseError, SafeArithmeticEvaluator
from .ir import (
    ProofObject,
    ProofStep,
    TSIRDocument,
    VerifierObligation,
    stable_hash,
)


@dataclass(frozen=True, slots=True)
class VerificationResult:
    obligation_id: str
    verifier_type: str
    outcome: str
    explanation: str
    consumed_premises: list[str] = field(default_factory=list)
    produced_claims: list[str] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    artifact_hashes: list[str] = field(default_factory=list)
    deterministic: bool = True
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class Verifier(Protocol):
    verifier_type: str

    def verify(
        self,
        obligation: VerifierObligation,
        workspace: Any,
    ) -> VerificationResult: ...


class StructuralVerifier:
    verifier_type = "structural"

    def verify(
        self,
        obligation: VerifierObligation,
        workspace: Any,
    ) -> VerificationResult:
        document: TSIRDocument = workspace.document
        entity_ids = {entity.id for entity in document.entities}
        claim_ids = {claim.id for claim in document.claims}
        errors: list[str] = []

        for claim in document.claims:
            if claim.subject not in entity_ids:
                errors.append(f"claim {claim.id} references missing subject")
            if claim.object not in entity_ids:
                errors.append(f"claim {claim.id} references missing object")

        for relation in document.relations:
            known = entity_ids | claim_ids
            if relation.source not in known:
                errors.append(f"relation references missing source {relation.source}")
            if relation.target not in known:
                errors.append(f"relation references missing target {relation.target}")

        for diagnostic in document.diagnostics:
            if diagnostic.get("severity") == "error":
                errors.append(str(diagnostic.get("message", "parser error")))

        if errors:
            return VerificationResult(
                obligation.id,
                self.verifier_type,
                "fail",
                "; ".join(sorted(errors)),
                limitations=["structural_validation_only"],
            )

        return VerificationResult(
            obligation.id,
            self.verifier_type,
            "pass",
            "TSIR structure is internally consistent.",
        )


class SyllogismVerifier:
    verifier_type = "syllogism"

    def verify(
        self,
        obligation: VerifierObligation,
        workspace: Any,
    ) -> VerificationResult:
        proof = self.build_proof(obligation, workspace.document)
        if proof is None:
            target = workspace.document.claim_by_id(obligation.target_claim)
            explanation = "no licensed syllogistic inference supports target claim"
            if target and target.predicate == "implies_property":
                explanation = "converse inference is not licensed by the premises"
            return VerificationResult(
                obligation.id,
                self.verifier_type,
                "fail",
                explanation,
                consumed_premises=list(obligation.premises),
                limitations=["supports_only_universal_rule_plus_membership"],
            )

        workspace.proof_objects.append(proof)
        produced = [proof.target_claim]
        return VerificationResult(
            obligation.id,
            self.verifier_type,
            "pass",
            "universal rule and membership fact license the target property claim",
            consumed_premises=proof.steps[0].consumed_premises,
            produced_claims=produced,
            evidence=[
                {"proof_object_hash": proof.hash(), "proof_type": proof.proof_type}
            ],
            artifact_hashes=[proof.hash()],
        )

    def build_proof(
        self,
        obligation: VerifierObligation,
        document: TSIRDocument,
    ) -> ProofObject | None:
        target = document.claim_by_id(obligation.target_claim)
        if target is None:
            return None
        if target.predicate != "has_property" or target.polarity != "positive":
            return None

        rules = [
            claim
            for claim in document.claims
            if claim.predicate == "implies_property" and claim.polarity == "positive"
        ]
        facts = [
            claim
            for claim in document.claims
            if claim.predicate == "is_a"
            and claim.subject == target.subject
            and claim.polarity == "positive"
        ]
        for rule in sorted(rules, key=lambda item: item.id):
            if rule.object != target.object:
                continue
            for fact in sorted(facts, key=lambda item: item.id):
                if fact.object != rule.subject:
                    continue
                step = ProofStep(
                    rule_id=rule.id,
                    consumed_premises=[rule.id, fact.id],
                    substitution={"x": target.subject},
                    produced_claim=target.id,
                )
                return ProofObject(
                    proof_type="universal_instantiation_modus_ponens",
                    target_claim=target.id,
                    steps=[step],
                    exact_match=True,
                )
        return None


class ArithmeticVerifier:
    verifier_type = "arithmetic"

    def __init__(self) -> None:
        self.evaluator = SafeArithmeticEvaluator()

    def verify(
        self,
        obligation: VerifierObligation,
        workspace: Any,
    ) -> VerificationResult:
        expression = str(
            obligation.expected_property.get("expression")
            or obligation.target_claim
            or ""
        ).strip()
        try:
            receipt = self.evaluator.verify(expression)
        except ArithmeticParseError as exc:
            return VerificationResult(
                obligation.id,
                self.verifier_type,
                "error",
                f"arithmetic parse failed: {exc}",
                limitations=["allowlisted_arithmetic_ast_only"],
            )
        outcome = "pass" if receipt.passed else "fail"
        return VerificationResult(
            obligation.id,
            self.verifier_type,
            outcome,
            "arithmetic proposition evaluated deterministically",
            evidence=[asdict(receipt)],
            artifact_hashes=[stable_hash(asdict(receipt))],
        )


class BOGVMExecutionVerifier:
    verifier_type = "bogvm_execution"

    def verify(
        self,
        obligation: VerifierObligation,
        workspace: Any,
    ) -> VerificationResult:
        artifact = None
        expected_hash = str(obligation.expected_property.get("proof_object_hash", ""))
        for item in workspace.bogvm_artifacts:
            if item.get("proof_object_hash") == expected_hash:
                artifact = item
                break
        if artifact is None:
            return VerificationResult(
                obligation.id,
                self.verifier_type,
                "fail",
                "no BOGVM artifact matched the proof object",
            )
        execution_completed = bool(artifact.get("execution_completed", False))
        proof_matches = bool(artifact.get("proof_object_hash") == expected_hash)
        outcome = "pass" if execution_completed and proof_matches else "fail"
        return VerificationResult(
            obligation.id,
            self.verifier_type,
            outcome,
            (
                "BOGVM execution completed for the proof-object-derived program"
                if outcome == "pass"
                else "BOGVM execution did not satisfy execution requirements"
            ),
            artifact_hashes=[str(artifact.get("artifact_hash", ""))],
            evidence=[
                {
                    "execution_completed": execution_completed,
                    "proof_object_matches": proof_matches,
                    "vm_receipt_hash": artifact.get("vm_receipt_hash"),
                }
            ],
            limitations=["execution_completion_is_not_semantic_proof"],
        )


class CommitPolicyVerifier:
    verifier_type = "commit_policy"

    def verify(
        self,
        obligation: VerifierObligation,
        workspace: Any,
    ) -> VerificationResult:
        failed = [
            result
            for result in workspace.verification_results
            if result.outcome != "pass"
            and workspace.is_required_obligation(result.obligation_id)
        ]
        if failed:
            return VerificationResult(
                obligation.id,
                self.verifier_type,
                "fail",
                "mandatory verifier obligations did not all pass",
                evidence=[result.to_dict() for result in failed],
            )
        return VerificationResult(
            obligation.id,
            self.verifier_type,
            "pass",
            "all mandatory verifier obligations passed",
        )


def compile_proof_to_bogvm_artifact(proof: ProofObject, document: TSIRDocument) -> dict:
    """Compile the proof object into a deterministic BOGVM program and execute it.

    The VM program is derived from the proof object: rule premise, membership
    premise, substitution and target claim are all represented in node or claim
    symbols. The independent syllogism verifier remains the semantic authority.
    """

    step = proof.steps[0]
    rule = document.claim_by_id(step.rule_id)
    fact = document.claim_by_id(step.consumed_premises[1])
    target = document.claim_by_id(proof.target_claim)
    if rule is None or fact is None or target is None:
        return {
            "artifact_type": "bogvm_execution",
            "execution_completed": False,
            "proof_obligation_satisfied": False,
            "state_commit_authorized": False,
            "error": "proof object references missing claims",
            "proof_object_hash": proof.hash(),
        }

    symbols = {
        "subject": target.subject.replace("entity:", "").replace(":", "_"),
        "class": rule.subject.replace("entity:", "").replace(":", "_"),
        "property": rule.object.replace("entity:", "").replace(":", "_"),
        "claim": target.id.replace("claim:", "").replace(":", "_").replace("-", "_"),
    }
    assembly = "\n".join(
        [
            f"CREATE_NODE {symbols['subject']}",
            f"CREATE_NODE {symbols['class']}",
            f"CREATE_NODE {symbols['property']}",
            f"CREATE_EDGE {symbols['subject']} {symbols['class']} support",
            f"CREATE_EDGE {symbols['class']} {symbols['property']} support",
            (
                f"CREATE_CLAIM {symbols['claim']} "
                f"{symbols['subject']} {symbols['property']}"
            ),
            f"ACTIVATE {symbols['subject']} 1000",
            f"PROPAGATE {symbols['subject']} support 2",
            f"VERIFY {symbols['claim']}",
            f"ACCEPT {symbols['claim']}",
            "EMIT_RECEIPT",
            "HALT",
            "",
        ]
    )

    core_vm = Path(__file__).resolve().parents[2] / "core-vm"
    if str(core_vm) not in sys.path:
        sys.path.insert(0, str(core_vm))

    try:
        from bogvm.assembler import Assembler
        from bogvm.vm import run_file_with_block_receipt

        assembler = Assembler()
        program_bytes = assembler.assemble_text(assembly)
        with tempfile.NamedTemporaryFile(suffix=".bogbin", delete=True) as temp:
            temp.write(program_bytes)
            temp.flush()
            vm_receipt, exit_code = run_file_with_block_receipt(temp.name)
    except Exception as exc:
        return {
            "artifact_type": "bogvm_execution",
            "execution_completed": False,
            "proof_obligation_satisfied": False,
            "state_commit_authorized": False,
            "error": str(exc),
            "assembly": assembly,
            "proof_object_hash": proof.hash(),
            "artifact_hash": stable_hash({"assembly": assembly, "error": str(exc)}),
        }

    artifact = {
        "artifact_type": "bogvm_execution",
        "assembly": assembly,
        "program_hash": stable_hash({"assembly": assembly}),
        "proof_object_hash": proof.hash(),
        "execution_completed": exit_code == 0
        and vm_receipt.get("execution_status") == "completed",
        "proof_obligation_satisfied": False,
        "state_commit_authorized": False,
        "vm_receipt_hash": vm_receipt.get("receipt_hash"),
        "vm_receipt": vm_receipt,
    }
    artifact["artifact_hash"] = stable_hash(
        {
            "assembly": assembly,
            "proof_object_hash": artifact["proof_object_hash"],
            "vm_receipt_hash": artifact["vm_receipt_hash"],
            "execution_completed": artifact["execution_completed"],
        }
    )
    return artifact
