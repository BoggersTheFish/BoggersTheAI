"""Canonical verifier-gated TS transaction kernel."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from ..graph.universal_living_graph import UniversalLivingGraph
from .commit import commit_document, render_claim
from .ir import ClaimNode, Provenance, TSOperation, VerifierObligation, stable_hash
from .obligations import (
    ArithmeticVerifier,
    BOGVMExecutionVerifier,
    CodePropertyVerifier,
    CommitPolicyVerifier,
    StructuralVerifier,
    SyllogismVerifier,
    VerificationResult,
    compile_proof_to_bogvm_artifact,
)
from .receipts import TSReceipt, build_receipt
from .replay import replay_receipt
from .representation import PARSER_VERSION, DeterministicTSParser
from .tension import build_tension_report
from .transaction import (
    CommitDecision,
    TransactionRequest,
    TransactionResult,
    TransactionWorkspace,
    graph_snapshot,
    graph_state_hash,
)


class TSKernel:
    """One transaction path and acceptance authority for TS reasoning."""

    def __init__(
        self,
        graph: Any | None = None,
        *,
        parent_receipt_hash: str | None = None,
    ) -> None:
        self.graph = (
            graph if graph is not None else UniversalLivingGraph(auto_load=False)
        )
        self.parser = DeterministicTSParser()
        self.structural_verifier = StructuralVerifier()
        self.syllogism_verifier = SyllogismVerifier()
        self.arithmetic_verifier = ArithmeticVerifier()
        self.code_property_verifier = CodePropertyVerifier()
        self.bogvm_verifier = BOGVMExecutionVerifier()
        self.commit_policy = CommitPolicyVerifier()
        self.parent_receipt_hash = parent_receipt_hash
        self.receipts: list[TSReceipt] = []

    def can_handle(self, text: str) -> bool:
        parsed = self.parser.parse(text).document
        if parsed.obligations:
            return True
        return any(
            operation.operation_type
            in {"DECLARE_RULE", "CREATE_CLAIM", "BRANCH_REPRESENTATION"}
            for operation in parsed.operations
        )

    def transact(self, request: TransactionRequest | str) -> TransactionResult:
        if isinstance(request, str):
            request = TransactionRequest(raw_input=request)

        base_nodes, base_edges = graph_snapshot(self.graph)
        base_hash = graph_state_hash(self.graph)
        document = self.parser.parse(request.raw_input).document
        workspace = TransactionWorkspace(
            base_graph_hash=base_hash,
            document=document,
            base_nodes=base_nodes,
            base_edges=base_edges,
        )

        structural_obligation = VerifierObligation(
            id="kernel:structural",
            verifier_type="structural",
            target_claim="__document__",
            required=True,
        )
        self._append_obligation(workspace, structural_obligation)
        self._append_result(
            workspace,
            self.structural_verifier.verify(structural_obligation, workspace),
        )

        for obligation in sorted(document.obligations, key=lambda item: item.id):
            self._append_obligation(workspace, obligation)
            try:
                if obligation.verifier_type == "syllogism":
                    result = self.syllogism_verifier.verify(obligation, workspace)
                    self._append_result(workspace, result)
                    if result.outcome == "pass":
                        self._materialize_proof_claim(workspace, obligation)
                        if request.use_bogvm:
                            self._run_bogvm_for_latest_proof(workspace)
                elif obligation.verifier_type == "arithmetic":
                    self._append_result(
                        workspace,
                        self.arithmetic_verifier.verify(obligation, workspace),
                    )
                elif obligation.verifier_type == "code_property":
                    self._append_result(
                        workspace,
                        self.code_property_verifier.verify(obligation, workspace),
                    )
                else:
                    self._append_result(
                        workspace,
                        VerificationResult(
                            obligation.id,
                            obligation.verifier_type,
                            "unsupported",
                            "no verifier channel registered for obligation",
                        ),
                    )
            except Exception as exc:
                self._append_result(
                    workspace,
                    VerificationResult(
                        obligation.id,
                        obligation.verifier_type,
                        "error",
                        f"{exc.__class__.__name__}: {exc}",
                    ),
                )

        for proof in workspace.proof_objects:
            proof_hash = proof.hash()
            bog_obligation = VerifierObligation(
                id="kernel:bogvm:" + proof_hash[:16],
                verifier_type="bogvm_execution",
                target_claim=proof.target_claim,
                expected_property={"semantic_proof_object_hash": proof_hash},
                required=True,
            )
            self._append_obligation(workspace, bog_obligation)
            self._append_result(
                workspace, self.bogvm_verifier.verify(bog_obligation, workspace)
            )

        initial_tension = build_tension_report(
            document,
            verification_results=workspace.verification_results,
            obligations=workspace.obligations,
        )
        decision, reason = self._decide(workspace, initial_tension)

        commit_obligation = VerifierObligation(
            id="kernel:commit_policy",
            verifier_type="commit_policy",
            target_claim="__commit__",
            required=True,
        )
        if decision in {CommitDecision.COMMIT, CommitDecision.BRANCH}:
            self._append_obligation(workspace, commit_obligation)
            commit_result = self.commit_policy.verify(commit_obligation, workspace)
            self._append_result(workspace, commit_result)
            if commit_result.outcome != "pass":
                decision = CommitDecision.REJECT
                reason = commit_result.explanation

        final_tension = build_tension_report(
            document,
            verification_results=workspace.verification_results,
            obligations=workspace.obligations,
        )
        if (
            decision in {CommitDecision.COMMIT, CommitDecision.BRANCH}
            and final_tension.by_type.get("verification_tension", 0.0) > 0.0
        ):
            decision = CommitDecision.REJECT
            reason = "commit policy rejected unresolved mandatory obligations"

        claim_status_by_id = self._claim_commit_statuses(workspace, decision)
        accepted_claim_ids = {
            claim_id
            for claim_id, status in claim_status_by_id.items()
            if status == "accepted"
        }
        if decision == CommitDecision.COMMIT:
            workspace.committed_graph_delta = commit_document(
                self.graph,
                document,
                accepted_claim_ids=accepted_claim_ids,
                claim_status_by_id=claim_status_by_id,
            )
        elif decision == CommitDecision.BRANCH:
            workspace.committed_graph_delta = commit_document(
                self.graph,
                document,
                accepted_claim_ids=set(),
                commit_branch_only=True,
            )

        self._mark_bogvm_commit_authorization(workspace, decision)
        post_hash = graph_state_hash(self.graph)
        rendered = self._render(decision, reason, workspace)
        receipt = build_receipt(
            raw_input=request.raw_input,
            parser_version=PARSER_VERSION,
            base_graph_hash=base_hash,
            proposed_operations=[asdict(op) for op in document.operations],
            representation_warnings=list(document.diagnostics),
            tension_reports=[initial_tension.to_dict(), final_tension.to_dict()],
            verifier_obligations=[asdict(item) for item in workspace.obligations],
            verification_results=[
                result.to_dict() for result in workspace.verification_results
            ],
            bogvm_artifacts=workspace.bogvm_artifacts,
            derived_claims=[asdict(claim) for claim in workspace.derived_claims],
            rejected_claims=[
                asdict(claim)
                for claim in document.claims
                if claim.id in set(workspace.rejected_claims)
            ],
            commit_decision=decision.value,
            commit_reason=reason,
            post_state_hash=post_hash,
            parent_receipt_hash=self.parent_receipt_hash,
            renderer_metadata={
                "rendered_language_is_not_proof": True,
                "renderer": "deterministic_kernel_renderer",
                "replay_verified": False,
            },
            reasoning_artifacts=[
                {"artifact_type": "TSIR", "hash": document.hash()},
                *[
                    {"artifact_type": "proof_object", "hash": proof.hash()}
                    for proof in workspace.proof_objects
                ],
            ],
            execution_artifacts=workspace.bogvm_artifacts,
            proof_artifacts=[
                {
                    "artifact_type": "proof_object",
                    "hash": proof.hash(),
                    "payload": asdict(proof),
                }
                for proof in workspace.proof_objects
            ],
            rendered_explanation=rendered,
            committed_graph_delta=workspace.committed_graph_delta,
        )
        receipt.renderer_metadata["replay_verified"] = (
            self._verify_replay_from_workspace(workspace, receipt)
        )
        receipt.receipt_hash = stable_hash(receipt.canonical_payload())
        self.receipts.append(receipt)
        self.parent_receipt_hash = receipt.receipt_hash
        return TransactionResult(decision=decision, receipt=receipt, rendered=rendered)

    def replay(
        self, receipt: TSReceipt | dict[str, Any], graph: Any | None = None
    ) -> str:
        from .replay import replay_receipt

        return replay_receipt(graph or self.graph, receipt)

    def _append_result(
        self,
        workspace: TransactionWorkspace,
        result: VerificationResult,
    ) -> None:
        workspace.verification_results.append(result)

    def _append_obligation(
        self,
        workspace: TransactionWorkspace,
        obligation: VerifierObligation,
    ) -> None:
        workspace.add_obligation(obligation)

    def _materialize_proof_claim(
        self,
        workspace: TransactionWorkspace,
        obligation: VerifierObligation,
    ) -> None:
        target = workspace.document.claim_by_id(obligation.target_claim)
        if target is None:
            return
        accepted = ClaimNode(
            id=target.id,
            subject=target.subject,
            predicate=target.predicate,
            object=target.object,
            polarity=target.polarity,
            modality="verified",
            status="accepted",
            provenance=Provenance(
                "verifier",
                detail=f"derived_by:{obligation.id}",
                reliability=1.0,
            ),
        )
        workspace.document.claims = [
            accepted if claim.id == accepted.id else claim
            for claim in workspace.document.claims
        ]
        workspace.derived_claims.append(accepted)
        workspace.document.operations.append(
            TSOperation(
                operation_type="DERIVE_CLAIM",
                target=accepted.id,
                payload={"derived_by": obligation.id},
                provenance=accepted.provenance,
            )
        )

    def _run_bogvm_for_latest_proof(self, workspace: TransactionWorkspace) -> None:
        if not workspace.proof_objects:
            return
        proof = workspace.proof_objects[-1]
        artifact = compile_proof_to_bogvm_artifact(proof, workspace.document)
        artifact["target_claim"] = proof.target_claim
        artifact["semantic_proof_object_hash"] = proof.hash()
        semantic_pass = any(
            result.outcome == "pass"
            and result.verifier_type == "syllogism"
            and proof.target_claim in result.produced_claims
            for result in workspace.verification_results
        )
        artifact["proof_obligation_satisfied"] = semantic_pass
        artifact["state_commit_authorized"] = False
        workspace.bogvm_artifacts.append(artifact)

    def _decide(
        self,
        workspace: TransactionWorkspace,
        tension_report: Any,
    ) -> tuple[CommitDecision, str]:
        structural = [
            result
            for result in workspace.verification_results
            if result.obligation_id == "kernel:structural"
        ]
        if structural and structural[-1].outcome != "pass":
            return CommitDecision.REJECT, structural[-1].explanation
        if any(
            operation.operation_type == "BRANCH_REPRESENTATION"
            for operation in workspace.document.operations
        ):
            return (
                CommitDecision.BRANCH,
                "representation challenge branches the entity instead of changing confidence",
            )
        if tension_report.by_type.get("contradiction_tension", 0.0) > 0.0:
            return (
                CommitDecision.QUARANTINE,
                "conflicting positive and negative claims are preserved for repair",
            )
        failed_required = [
            result
            for result in workspace.verification_results
            if result.outcome != "pass"
            and workspace.is_required_obligation(result.obligation_id)
        ]
        if failed_required:
            for result in failed_required:
                workspace.rejected_claims.append(result.obligation_id)
            return (
                CommitDecision.REJECT,
                "; ".join(sorted(result.explanation for result in failed_required)),
            )
        if not workspace.document.operations:
            return CommitDecision.ABSTAIN, "no supported TSIR operation was proposed"
        return (
            CommitDecision.COMMIT,
            "mandatory verifiers passed and commit is authorized",
        )

    def _claim_commit_statuses(
        self,
        workspace: TransactionWorkspace,
        decision: CommitDecision,
    ) -> dict[str, str]:
        if decision != CommitDecision.COMMIT:
            return {}
        statuses: dict[str, str] = {}
        produced: set[str] = set()
        consumed: set[str] = set()
        for result in workspace.verification_results:
            if result.outcome != "pass":
                continue
            produced.update(result.produced_claims)
            consumed.update(result.consumed_premises)
        for claim_id in sorted(produced):
            statuses[claim_id] = "accepted"
        for claim_id in sorted(consumed):
            statuses.setdefault(claim_id, "transaction_assumption")
        if workspace.document.obligations:
            return statuses
        for claim in workspace.document.claims:
            if claim.status in {
                "proposed",
                "asserted",
                "transaction_assumption",
                "unverified_premise",
            }:
                statuses.setdefault(claim.id, "unverified_premise")
        return statuses

    def _render(
        self,
        decision: CommitDecision,
        reason: str,
        workspace: TransactionWorkspace,
    ) -> str:
        if workspace.derived_claims and decision == CommitDecision.COMMIT:
            claim = workspace.derived_claims[-1]
            return (
                f"{render_claim(claim, workspace.document)}. "
                "The receipt contains the proof object and verifier results."
            )
        arithmetic = [
            result
            for result in workspace.verification_results
            if result.verifier_type == "arithmetic" and result.outcome == "pass"
        ]
        if arithmetic and decision == CommitDecision.COMMIT:
            evidence = arithmetic[-1].evidence[0] if arithmetic[-1].evidence else {}
            expression = evidence.get("expression", "the arithmetic proposition")
            computed = evidence.get("computed")
            parsed_kind = evidence.get("parsed_kind")
            if parsed_kind == "truthy_expression":
                return f"{expression} = {computed}. The arithmetic verifier passed."
            return "The arithmetic verifier passed."
        code_property = [
            result
            for result in workspace.verification_results
            if result.verifier_type == "code_property" and result.outcome == "pass"
        ]
        if code_property and decision == CommitDecision.COMMIT:
            return "The bounded code/property verifier passed."
        if decision == CommitDecision.QUARANTINE:
            return "The claim is under contradiction tension; no clean certainty was committed."
        if decision == CommitDecision.BRANCH:
            return "The representation was branched because authoritative evidence challenged the entity."
        return reason

    def _mark_bogvm_commit_authorization(
        self,
        workspace: TransactionWorkspace,
        decision: CommitDecision,
    ) -> None:
        for artifact in workspace.bogvm_artifacts:
            expected_hash = str(artifact.get("semantic_proof_object_hash", ""))
            bogvm_passed = any(
                result.verifier_type == "bogvm_execution"
                and result.outcome == "pass"
                and result.obligation_id == "kernel:bogvm:" + expected_hash[:16]
                for result in workspace.verification_results
            )
            artifact["state_commit_authorized"] = (
                decision == CommitDecision.COMMIT
                and bool(artifact.get("proof_obligation_satisfied", False))
                and bogvm_passed
            )

    def _verify_replay_from_workspace(
        self,
        workspace: TransactionWorkspace,
        receipt: TSReceipt,
    ) -> bool:
        replay_graph = UniversalLivingGraph(auto_load=False)
        for node in sorted(workspace.base_nodes.values(), key=lambda item: item.id):
            replay_graph.add_node(
                node_id=node.id,
                content=node.content,
                topics=node.topics,
                activation=node.activation,
                stability=node.stability,
                base_strength=node.base_strength,
                last_wave=node.last_wave,
                attributes=node.attributes,
                embedding=node.embedding,
            )
        for edge in sorted(
            workspace.base_edges,
            key=lambda item: (item.src, item.dst, item.relation, item.weight),
        ):
            if edge.src in replay_graph.nodes and edge.dst in replay_graph.nodes:
                replay_graph.add_edge(
                    edge.src,
                    edge.dst,
                    weight=edge.weight,
                    relation=edge.relation,
                )
        return (
            replay_receipt(replay_graph, receipt, verify_hash=False)
            == receipt.post_state_hash
        )
