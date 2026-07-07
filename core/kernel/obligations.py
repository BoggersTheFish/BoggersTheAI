"""Typed verifier channels for the canonical kernel."""

from __future__ import annotations

import ast
import operator
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol

from ..bogvm_bridge import execute_bogvm_assembly
from .arithmetic import ArithmeticParseError, SafeArithmeticEvaluator
from .ir import (
    ClaimNode,
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
    max_chain_depth = 5

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
        consumed: list[str] = []
        for step in proof.steps:
            for premise in step.consumed_premises:
                if premise not in consumed:
                    consumed.append(premise)
        return VerificationResult(
            obligation.id,
            self.verifier_type,
            "pass",
            "bounded syllogistic proof licenses the requested target claim",
            consumed_premises=consumed,
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
        if target.predicate not in {"has_property", "is_a"}:
            return None
        if target.polarity != "positive":
            return None

        subclass_rules = [
            claim
            for claim in document.claims
            if claim.predicate == "is_subclass_of" and claim.polarity == "positive"
        ]
        property_rules = [
            claim
            for claim in document.claims
            if claim.predicate == "implies_property" and claim.polarity == "positive"
        ]
        facts = [
            claim
            for claim in document.claims
            if claim.predicate == "is_a"
            and claim.subject == target.subject
            and claim.id != target.id
            and claim.polarity == "positive"
        ]
        for fact in sorted(facts, key=lambda item: item.id):
            proof = self._search_from_fact(
                fact=fact,
                target=target,
                subclass_rules=sorted(subclass_rules, key=lambda item: item.id),
                property_rules=sorted(property_rules, key=lambda item: item.id),
            )
            if proof is not None:
                return proof
        return None

    def _search_from_fact(
        self,
        *,
        fact: ClaimNode,
        target: ClaimNode,
        subclass_rules: list[ClaimNode],
        property_rules: list[ClaimNode],
    ) -> ProofObject | None:
        frontier: list[tuple[str, str, list[ProofStep], tuple[str, ...]]] = [
            (fact.object, fact.id, [], (fact.object,))
        ]
        for _depth in range(self.max_chain_depth + 1):
            next_frontier: list[tuple[str, str, list[ProofStep], tuple[str, ...]]] = []
            for current_class, current_claim_id, steps, visited in frontier:
                if target.predicate == "is_a" and current_class == target.object:
                    return ProofObject(
                        proof_type="bounded_chained_syllogism",
                        target_claim=target.id,
                        steps=steps,
                        exact_match=True,
                    )
                if target.predicate == "has_property":
                    for rule in property_rules:
                        if (
                            rule.subject != current_class
                            or rule.object != target.object
                        ):
                            continue
                        step = ProofStep(
                            rule_id=rule.id,
                            consumed_premises=[current_claim_id, rule.id],
                            substitution={
                                "x": target.subject,
                                "class": current_class,
                                "property": target.object,
                            },
                            produced_claim=target.id,
                        )
                        return ProofObject(
                            proof_type="bounded_chained_syllogism",
                            target_claim=target.id,
                            steps=[*steps, step],
                            exact_match=True,
                        )
                if len(steps) >= self.max_chain_depth:
                    continue
                for rule in subclass_rules:
                    if rule.subject != current_class:
                        continue
                    next_class = rule.object
                    if next_class in visited:
                        continue
                    produced_claim = (
                        target.id
                        if target.predicate == "is_a" and next_class == target.object
                        else _derived_is_a_claim_id(target.subject, next_class)
                    )
                    step = ProofStep(
                        rule_id=rule.id,
                        consumed_premises=[current_claim_id, rule.id],
                        substitution={
                            "x": target.subject,
                            "from_class": current_class,
                            "to_class": next_class,
                        },
                        produced_claim=produced_claim,
                    )
                    next_frontier.append(
                        (
                            next_class,
                            produced_claim,
                            [*steps, step],
                            (*visited, next_class),
                        )
                    )
            frontier = sorted(next_frontier, key=lambda item: (item[0], item[1]))
            if not frontier:
                break
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


_PROPERTY_OPS: dict[type[ast.AST], Callable[..., int | float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}
_MAX_CODE_PROPERTY_ABS_VALUE = 1_000_000


class CodePropertyVerifier:
    verifier_type = "code_property"

    def verify(
        self,
        obligation: VerifierObligation,
        workspace: Any,
    ) -> VerificationResult:
        spec = obligation.expected_property
        if spec.get("unsupported_input"):
            return VerificationResult(
                obligation.id,
                self.verifier_type,
                "unsupported",
                "code/property verifier supports only bounded arithmetic examples",
                limitations=["bounded_single_argument_arithmetic_examples_only"],
            )

        function_name = str(spec.get("function", "")).strip()
        parameter = str(spec.get("parameter", "")).strip()
        body = str(spec.get("body", "")).strip()
        examples = spec.get("examples", [])
        if (
            not function_name.isidentifier()
            or not parameter.isidentifier()
            or not body
            or not isinstance(examples, list)
            or not examples
        ):
            return VerificationResult(
                obligation.id,
                self.verifier_type,
                "unsupported",
                "code/property obligation is outside the supported bounded shape",
                limitations=["bounded_single_argument_arithmetic_examples_only"],
            )

        evidence: list[dict[str, Any]] = []
        try:
            for example in examples:
                if not isinstance(example, dict):
                    raise ArithmeticParseError("example must be an object")
                input_value = example["input"]
                expected = example["expected"]
                actual = self._evaluate_body(body, parameter, input_value)
                passed = actual == expected
                evidence.append(
                    {
                        "function": function_name,
                        "input": input_value,
                        "expected": expected,
                        "actual": actual,
                        "passed": passed,
                    }
                )
        except (
            ArithmeticError,
            ArithmeticParseError,
            KeyError,
            TypeError,
            ValueError,
        ) as exc:
            return VerificationResult(
                obligation.id,
                self.verifier_type,
                "error",
                f"code/property check failed to parse safely: {exc}",
                limitations=["bounded_single_argument_arithmetic_examples_only"],
            )

        outcome = "pass" if all(item["passed"] for item in evidence) else "fail"
        return VerificationResult(
            obligation.id,
            self.verifier_type,
            outcome,
            (
                "bounded arithmetic code/property examples all passed"
                if outcome == "pass"
                else "bounded arithmetic code/property examples failed"
            ),
            evidence=evidence,
            artifact_hashes=[
                stable_hash(
                    {
                        "function": function_name,
                        "parameter": parameter,
                        "body": body,
                        "examples": evidence,
                    }
                )
            ],
            limitations=[
                "bounded_single_argument_arithmetic_examples_only",
                "not_general_code_verification",
            ],
        )

    def _evaluate_body(
        self,
        expression: str,
        parameter: str,
        value: Any,
    ) -> int | float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ArithmeticParseError("example input must be numeric")
        self._ensure_bounded_number(value)
        try:
            parsed = ast.parse(expression, mode="eval")
        except SyntaxError as exc:
            raise ArithmeticParseError(str(exc)) from exc
        return self._eval_node(parsed.body, parameter, value)

    def _eval_node(
        self,
        node: ast.AST,
        parameter: str,
        value: int | float,
    ) -> int | float:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
                raise ArithmeticParseError("only numeric literals are allowed")
            return self._ensure_bounded_number(node.value)
        if isinstance(node, ast.Name):
            if node.id != parameter:
                raise ArithmeticParseError(f"unsupported variable: {node.id}")
            return value
        if isinstance(node, ast.BinOp) and type(node.op) in _PROPERTY_OPS:
            op = _PROPERTY_OPS[type(node.op)]
            return self._ensure_bounded_number(
                op(
                    self._eval_node(node.left, parameter, value),
                    self._eval_node(node.right, parameter, value),
                )
            )
        if isinstance(node, ast.UnaryOp) and type(node.op) in _PROPERTY_OPS:
            op = _PROPERTY_OPS[type(node.op)]
            return self._ensure_bounded_number(
                op(self._eval_node(node.operand, parameter, value))
            )
        raise ArithmeticParseError(
            f"unsupported arithmetic syntax: {node.__class__.__name__}"
        )

    def _ensure_bounded_number(self, value: int | float) -> int | float:
        if abs(value) > _MAX_CODE_PROPERTY_ABS_VALUE:
            raise ArithmeticParseError("code/property numeric value is out of bounds")
        return value


class BOGVMExecutionVerifier:
    verifier_type = "bogvm_execution"

    def verify(
        self,
        obligation: VerifierObligation,
        workspace: Any,
    ) -> VerificationResult:
        artifact = None
        expected_hash = str(
            obligation.expected_property.get("semantic_proof_object_hash", "")
            or obligation.expected_property.get("proof_object_hash", "")
        )
        for item in workspace.bogvm_artifacts:
            if (
                item.get("target_claim") == obligation.target_claim
                and item.get("semantic_proof_object_hash") == expected_hash
            ):
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
        semantic_anchor_matches = bool(
            artifact.get("semantic_proof_object_hash") == expected_hash
        )
        proof_obligation_satisfied = bool(
            artifact.get("proof_obligation_satisfied", False)
        )
        outcome = (
            "pass"
            if (
                execution_completed
                and proof_matches
                and semantic_anchor_matches
                and proof_obligation_satisfied
            )
            else "fail"
        )
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
                    "semantic_anchor_matches": semantic_anchor_matches,
                    "proof_obligation_satisfied": proof_obligation_satisfied,
                    "vm_receipt_hash": artifact.get("vm_receipt_hash"),
                }
            ],
            limitations=["execution_completion_is_not_semantic_proof"],
        )


class BOGVMObservationVerifier:
    verifier_type = "bogvm_observation"

    def verify(
        self,
        obligation: VerifierObligation,
        workspace: Any,
    ) -> VerificationResult:
        spec = obligation.expected_property
        artifact_hash = str(spec.get("artifact_hash", "")).strip()
        if not artifact_hash:
            return self._fail(obligation, "missing required observation artifact_hash")

        artifact, source, lookup_error = self._find_artifact(spec, workspace)
        if lookup_error:
            return self._fail(obligation, lookup_error)
        if artifact is None:
            return self._fail(
                obligation,
                "no BOGVM observation artifact matched artifact_hash",
            )

        mismatches: list[str] = []
        if artifact.get("artifact_type") != "bogvm_execution":
            mismatches.append("artifact_type is not bogvm_execution")
        if str(artifact.get("artifact_hash", "")) != artifact_hash:
            mismatches.append("artifact_hash mismatch")
        computed_artifact_hash = self._computed_artifact_hash(artifact)
        if computed_artifact_hash != artifact_hash:
            mismatches.append("artifact_hash content mismatch")
        if artifact.get("state_commit_authorized") is not False:
            mismatches.append("raw observation must keep state_commit_authorized false")

        checks = [
            "program_hash",
            "vm_receipt_hash",
            "execution_status",
            "execution_completed",
            "exit_code",
            "state_commit_authorized",
        ]
        for key in checks:
            if key in spec and artifact.get(key) != spec.get(key):
                mismatches.append(f"{key} mismatch")

        if spec.get("emitted_receipt_exists") is True:
            receipt = artifact.get("vm_receipt")
            receipt_hash = artifact.get("vm_receipt_hash")
            if not isinstance(receipt, dict) or not receipt_hash:
                mismatches.append("VM receipt is missing")
            elif receipt.get("receipt_hash") != receipt_hash:
                mismatches.append("VM receipt hash mismatch")
        elif "emitted_receipt_exists" in spec and spec.get("emitted_receipt_exists"):
            mismatches.append("unsupported emitted_receipt_exists expectation")

        evidence = self._evidence(artifact, source)
        if mismatches:
            return VerificationResult(
                obligation.id,
                self.verifier_type,
                "fail",
                "; ".join(sorted(mismatches)),
                evidence=[evidence],
                artifact_hashes=[artifact_hash],
                limitations=[
                    "checks_exact_bogvm_observation_facts_only",
                    "execution_is_not_semantic_proof",
                ],
            )

        return VerificationResult(
            obligation.id,
            self.verifier_type,
            "pass",
            "BOGVM observation artifact facts match the verifier expectation",
            evidence=[evidence],
            artifact_hashes=[artifact_hash],
            limitations=[
                "checks_exact_bogvm_observation_facts_only",
                "execution_is_not_semantic_proof",
            ],
        )

    def _find_artifact(
        self,
        spec: dict[str, Any],
        workspace: Any,
    ) -> tuple[dict[str, Any] | None, str, str]:
        artifact_hash = str(spec.get("artifact_hash", "")).strip()
        embedded = spec.get("artifact")
        if isinstance(embedded, dict):
            return dict(embedded), "expected_property.artifact", ""

        base_nodes = getattr(workspace, "base_nodes", {})
        if not isinstance(base_nodes, dict):
            return None, "", ""
        matches: list[tuple[dict[str, Any], str]] = []
        for node in sorted(
            base_nodes.values(), key=lambda item: getattr(item, "id", "")
        ):
            attributes = getattr(node, "attributes", {})
            if not isinstance(attributes, dict):
                continue
            if attributes.get("observation_type") != "bogvm_execution_observation":
                continue
            artifact = attributes.get("artifact")
            if not isinstance(artifact, dict):
                continue
            if str(artifact.get("artifact_hash", "")) == artifact_hash:
                matches.append((dict(artifact), str(getattr(node, "id", ""))))
        if len(matches) > 1:
            return (
                None,
                "",
                "multiple BOGVM observation artifacts matched artifact_hash",
            )
        if matches:
            return matches[0][0], matches[0][1], ""
        return None, "", ""

    def _computed_artifact_hash(self, artifact: dict[str, Any]) -> str:
        payload = {
            "artifact_type": artifact.get("artifact_type"),
            "program_hash": artifact.get("program_hash"),
            "max_steps": artifact.get("max_steps"),
            "execution_status": artifact.get("execution_status"),
            "execution_completed": artifact.get("execution_completed"),
            "exit_code": artifact.get("exit_code"),
            "vm_receipt_hash": artifact.get("vm_receipt_hash"),
            "error": artifact.get("error"),
            "state_commit_authorized": artifact.get("state_commit_authorized"),
        }
        if "vm_program_hash" in artifact:
            payload["vm_program_hash"] = artifact.get("vm_program_hash")
        if "program_output" in artifact:
            payload["program_output"] = artifact.get("program_output")
        if "details" in artifact or "vm_program_hash" not in artifact:
            payload["details"] = artifact.get("details")
        return stable_hash(payload)

    def _evidence(self, artifact: dict[str, Any], source: str) -> dict[str, Any]:
        return {
            "source": source,
            "artifact_type": artifact.get("artifact_type"),
            "artifact_hash": artifact.get("artifact_hash"),
            "program_hash": artifact.get("program_hash"),
            "vm_receipt_hash": artifact.get("vm_receipt_hash"),
            "execution_status": artifact.get("execution_status"),
            "execution_completed": artifact.get("execution_completed"),
            "exit_code": artifact.get("exit_code"),
            "program_output": artifact.get("program_output"),
            "state_commit_authorized": artifact.get("state_commit_authorized"),
            "emitted_receipt_exists": bool(
                artifact.get("vm_receipt") and artifact.get("vm_receipt_hash")
            ),
        }

    def _fail(
        self,
        obligation: VerifierObligation,
        explanation: str,
    ) -> VerificationResult:
        return VerificationResult(
            obligation.id,
            self.verifier_type,
            "fail",
            explanation,
            limitations=[
                "checks_exact_bogvm_observation_facts_only",
                "execution_is_not_semantic_proof",
            ],
        )


class BOGVMArithmeticProgramVerifier:
    verifier_type = "bogvm_arithmetic_program"

    def verify(
        self,
        obligation: VerifierObligation,
        workspace: Any,
    ) -> VerificationResult:
        spec = obligation.expected_property
        artifact_hash = str(spec.get("artifact_hash", "")).strip()
        if not artifact_hash:
            return self._fail(obligation, "missing required observation artifact_hash")

        artifact, source, lookup_error = BOGVMObservationVerifier()._find_artifact(
            spec,
            workspace,
        )
        if lookup_error:
            return self._fail(obligation, lookup_error)
        if artifact is None:
            return self._fail(
                obligation,
                "no BOGVM observation artifact matched artifact_hash",
            )

        mismatches: list[str] = []
        observation = BOGVMObservationVerifier()
        if artifact.get("artifact_type") != "bogvm_execution":
            mismatches.append("artifact_type is not bogvm_execution")
        if str(artifact.get("artifact_hash", "")) != artifact_hash:
            mismatches.append("artifact_hash mismatch")
        if observation._computed_artifact_hash(artifact) != artifact_hash:
            mismatches.append("artifact_hash content mismatch")
        if artifact.get("state_commit_authorized") is not False:
            mismatches.append("raw observation must keep state_commit_authorized false")
        if artifact.get("execution_status") != "completed":
            mismatches.append("execution_status mismatch")
        if artifact.get("execution_completed") is not True:
            mismatches.append("execution_completed mismatch")
        if artifact.get("exit_code") != 0:
            mismatches.append("exit_code mismatch")
        if "program_hash" in spec and artifact.get("program_hash") != spec.get(
            "program_hash"
        ):
            mismatches.append("program_hash mismatch")

        property_spec = spec.get("property")
        expected_value: int | None = None
        if not isinstance(property_spec, dict):
            mismatches.append("missing checked property")
        elif property_spec.get("type") != "exact_output_i64":
            mismatches.append("unsupported checked property")
        else:
            raw_expected = property_spec.get("expected")
            if isinstance(raw_expected, bool) or not isinstance(raw_expected, int):
                mismatches.append("expected output must be an integer")
            else:
                expected_value = raw_expected

        output = artifact.get("program_output")
        observed_value: int | None = None
        if not isinstance(output, dict):
            mismatches.append("missing strict program output")
        elif output.get("schema") != "bogvm_result_i64_v1":
            mismatches.append("unsupported program output schema")
        else:
            raw_value = output.get("value")
            if isinstance(raw_value, bool) or not isinstance(raw_value, int):
                mismatches.append("observed output must be an integer")
            else:
                observed_value = raw_value

        passed = (
            not mismatches
            and expected_value is not None
            and observed_value is not None
            and observed_value == expected_value
        )
        if (
            not passed
            and expected_value is not None
            and observed_value is not None
            and observed_value != expected_value
        ):
            mismatches.append("observed output does not equal expected output")

        evidence = self._evidence(
            artifact=artifact,
            source=source,
            obligation=obligation,
            expected_value=expected_value,
            observed_value=observed_value,
            passed=passed,
        )
        if not passed:
            return VerificationResult(
                obligation.id,
                self.verifier_type,
                "fail",
                "; ".join(sorted(mismatches)) or "BOGVM arithmetic property failed",
                evidence=[evidence],
                artifact_hashes=[artifact_hash, evidence["evidence_hash"]],
                limitations=[
                    "exact_integer_output_only",
                    "bogvm_execution_is_evidence_not_proof",
                    "not_general_program_verification",
                ],
            )

        return VerificationResult(
            obligation.id,
            self.verifier_type,
            "pass",
            "BOGVM arithmetic program output matched the exact expected integer",
            produced_claims=[obligation.target_claim],
            evidence=[evidence],
            artifact_hashes=[artifact_hash, evidence["evidence_hash"]],
            limitations=[
                "exact_integer_output_only",
                "bogvm_execution_is_evidence_not_proof",
                "not_general_program_verification",
            ],
        )

    def _evidence(
        self,
        *,
        artifact: dict[str, Any],
        source: str,
        obligation: VerifierObligation,
        expected_value: int | None,
        observed_value: int | None,
        passed: bool,
    ) -> dict[str, Any]:
        property_payload = {
            "type": "exact_output_i64",
            "expected": expected_value,
            "observed": observed_value,
        }
        evidence = {
            "source": source,
            "verifier_type": self.verifier_type,
            "target_claim": obligation.target_claim,
            "target_observation_artifact_hash": artifact.get("artifact_hash"),
            "target_program_hash": artifact.get("program_hash"),
            "expected_program_hash": obligation.expected_property.get("program_hash"),
            "observed_program_hash": artifact.get("program_hash"),
            "program_hash_checked": "program_hash" in obligation.expected_property,
            "checked_property": property_payload,
            "normalized_expected_value": expected_value,
            "observed_value": observed_value,
            "program_output": artifact.get("program_output"),
            "execution_status": artifact.get("execution_status"),
            "exit_code": artifact.get("exit_code"),
            "raw_observation_state_commit_authorized": artifact.get(
                "state_commit_authorized"
            ),
            "semantic_claim_authorized_by_verifier": passed,
        }
        evidence["evidence_hash"] = stable_hash(evidence)
        return evidence

    def _fail(
        self,
        obligation: VerifierObligation,
        explanation: str,
    ) -> VerificationResult:
        return VerificationResult(
            obligation.id,
            self.verifier_type,
            "fail",
            explanation,
            limitations=[
                "exact_integer_output_only",
                "bogvm_execution_is_evidence_not_proof",
                "not_general_program_verification",
            ],
        )


class CommitPolicyVerifier:
    verifier_type = "commit_policy"

    def verify(
        self,
        obligation: VerifierObligation,
        workspace: Any,
    ) -> VerificationResult:
        required = [
            item
            for item in getattr(workspace, "obligations", [])
            if item.required and item.id != obligation.id
        ]
        results_by_obligation: dict[str, list[VerificationResult]] = {}
        for result in workspace.verification_results:
            results_by_obligation.setdefault(result.obligation_id, []).append(result)

        missing = [
            item.id for item in required if not results_by_obligation.get(item.id)
        ]
        duplicate = [
            item.id
            for item in required
            if len(results_by_obligation.get(item.id, [])) > 1
        ]
        failed = [
            result
            for item in required
            for result in results_by_obligation.get(item.id, [])
            if result.outcome != "pass"
        ]
        if missing or duplicate or failed:
            issues = []
            if missing:
                issues.append("missing required results: " + ", ".join(sorted(missing)))
            if duplicate:
                issues.append(
                    "duplicate required results: " + ", ".join(sorted(duplicate))
                )
            if failed:
                issues.append(
                    "failed required results: "
                    + ", ".join(sorted(result.obligation_id for result in failed))
                )
            return VerificationResult(
                obligation.id,
                self.verifier_type,
                "fail",
                "; ".join(issues),
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

    if not proof.steps:
        return {
            "artifact_type": "bogvm_execution",
            "execution_completed": False,
            "proof_obligation_satisfied": False,
            "state_commit_authorized": False,
            "error": "proof object contains no executable steps",
            "proof_object_hash": proof.hash(),
        }

    step = proof.steps[-1]
    rule = document.claim_by_id(step.rule_id)
    target = document.claim_by_id(proof.target_claim)
    if rule is None or target is None:
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
        "object": rule.object.replace("entity:", "").replace(":", "_"),
        "claim": target.id.replace("claim:", "").replace(":", "_").replace("-", "_"),
    }
    assembly = "\n".join(
        [
            f"CREATE_NODE {symbols['subject']}",
            f"CREATE_NODE {symbols['class']}",
            f"CREATE_NODE {symbols['object']}",
            f"CREATE_EDGE {symbols['subject']} {symbols['class']} support",
            f"CREATE_EDGE {symbols['class']} {symbols['object']} support",
            (
                f"CREATE_CLAIM {symbols['claim']} "
                f"{symbols['subject']} {symbols['object']}"
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

    vm_artifact = execute_bogvm_assembly(assembly, max_steps=128)
    if not vm_artifact.get("vm_receipt"):
        return {
            "artifact_type": "bogvm_execution",
            "assembly": assembly,
            "program_hash": vm_artifact.get("program_hash"),
            "execution_completed": False,
            "proof_obligation_satisfied": False,
            "state_commit_authorized": False,
            "error": vm_artifact.get("error", "BOGVM execution failed closed"),
            "proof_object_hash": proof.hash(),
            "vm_receipt_hash": vm_artifact.get("vm_receipt_hash"),
            "vm_receipt": vm_artifact.get("vm_receipt"),
            "artifact_hash": stable_hash(
                {
                    "assembly": assembly,
                    "error": vm_artifact.get("error"),
                    "proof_object_hash": proof.hash(),
                }
            ),
        }

    artifact = {
        "artifact_type": "bogvm_execution",
        "assembly": vm_artifact.get("assembly", assembly),
        "program_hash": vm_artifact.get("program_hash"),
        "vm_program_hash": vm_artifact.get("vm_program_hash"),
        "proof_object_hash": proof.hash(),
        "execution_status": vm_artifact.get("execution_status"),
        "execution_completed": bool(vm_artifact.get("execution_completed")),
        "exit_code": vm_artifact.get("exit_code"),
        "proof_obligation_satisfied": False,
        "state_commit_authorized": False,
        "vm_receipt_hash": vm_artifact.get("vm_receipt_hash"),
        "vm_receipt": vm_artifact.get("vm_receipt"),
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


def _derived_is_a_claim_id(subject: str, obj: str) -> str:
    return (
        "claim:"
        + stable_hash(
            {
                "subject": subject,
                "predicate": "is_a",
                "object": obj,
                "polarity": "positive",
            }
        )[:20]
    )
