"""End-to-end TS-Reasoner-v0 pipeline."""

from __future__ import annotations

from typing import Iterable, Optional

from .cig_checker import CIGChecker
from .generator import DeterministicHeuristicGenerator, infer_premises_from_question
from .operation_router import OperationRouter
from .ranker import HeuristicTensionRanker
from .repair import TensionRepairer
from .tension_agents import TensionCoordinator
from .types import ReasonerOutput


class TSReasoner:
    """Generate, score, check, repair, and select a reasoning chain."""

    def __init__(self, ranker=None, generator=None, tension_coordinator=None) -> None:
        self.generator = generator or DeterministicHeuristicGenerator()
        self.cig_checker = CIGChecker()
        self.ranker = ranker or HeuristicTensionRanker()
        self.repairer = TensionRepairer()
        self.tension_coordinator = tension_coordinator or TensionCoordinator()
        self.operation_router = OperationRouter(
            checker=self.cig_checker,
            ranker=self.ranker,
            repairer=self.repairer,
            coordinator=self.tension_coordinator,
        )

    def run(self, question: str, premises: Optional[Iterable[str]] = None) -> ReasonerOutput:
        premise_list = [p.strip() for p in premises] if premises is not None else infer_premises_from_question(question)
        candidates = self.generator.generate(question, premise_list)
        scored = []
        for chain in candidates:
            cig = self.cig_checker.check(chain)
            score = self.ranker.score(chain, cig)
            field = self.tension_coordinator.coordinate(chain, cig, score)
            loop = self.operation_router.run_until_stable(chain)
            scored.append((chain, cig, score, field, loop))
        selected_original, _original_cig, _original_score, _original_field, selected_loop = min(
            scored,
            key=lambda item: (
                item[4]["score"].global_tension,
                -item[4]["score"].stability,
                item[0].chain_id,
            ),
        )
        selected_chain = selected_loop["chain"]
        selected_cig = selected_loop["cig"]
        selected_score = selected_loop["score"]
        selected_field = selected_loop["field"]
        repairs = self.repairer.suggest(selected_chain, selected_score)
        candidate_score_rows = [
            {
                "chain_id": chain.chain_id,
                "global_tension": score.global_tension,
                "local_tension": score.local_tension,
                "stability": score.stability,
                "issue_kinds": [issue.kind for issue in score.issues],
                "coordinated_tensions": field["coordinated_tensions"],
                "selected_next_op": field["selected_next_op"],
                "post_loop_chain_id": loop["chain"].chain_id,
                "post_loop_global_tension": loop["score"].global_tension,
                "post_loop_local_tension": loop["score"].local_tension,
                "post_loop_status": loop["status"],
                "post_loop_cycles": loop["cycle_count"],
                "post_loop_settled": loop["settled"],
            }
            for chain, _cig, score, field, loop in scored
        ]
        trace = {
            "contract_version": "1.0.0",
            "pipeline": "TS-Reasoner-v0",
            "input": {
                "question": question,
                "premises": premise_list,
            },
            "generator": self.generator.name,
            "ranker": self.ranker.__class__.__name__,
            "tension_coordinator": "TensionCoordinator",
            "operation_router": "OperationRouter",
            "selection": {
                "selected_chain_id": selected_chain.chain_id,
                "selected_original_chain_id": selected_original.chain_id,
                "criterion": "lowest_post_loop_global_tension_then_highest_stability",
            },
            "candidate_scores": candidate_score_rows,
            "chosen_action": self._chosen_action(selected_loop),
            "rejected_alternatives": self._rejected_alternatives(candidate_score_rows, selected_chain.chain_id),
            "settled_answer": selected_chain.final_answer,
            "failure_reason": None if selected_loop["settled"] else selected_loop["status"],
            "coordinated_tension_field": selected_field,
            "operation_loop": self._operation_trace(selected_loop),
            "candidate_operation_loops": {
                chain.chain_id: self._operation_trace(loop)
                for chain, _cig, _score, _field, loop in scored
            },
            "graph_view": {
                "nodes": [step.step_id for step in selected_chain.steps],
                "edges": [
                    {"from": dep, "to": step.step_id}
                    for step in selected_chain.steps
                    for dep in step.dependencies
                ],
                "claim_count": len(selected_cig.claims),
                "contradiction_count": len(selected_cig.contradiction_pairs),
            },
        }
        trace.update(self._typed_trace_section(selected_chain, selected_cig))
        return ReasonerOutput(
            question=question,
            premises=premise_list,
            candidates=[chain for chain, _cig, _score, _field, _loop in scored],
            selected_chain=selected_chain,
            tension_score=selected_score,
            cig_check=selected_cig,
            repairs=repairs,
            final_answer=selected_chain.final_answer,
            trace=trace,
        )

    def _operation_trace(self, transition: dict) -> dict:
        return {
            "status": transition["status"],
            "cycles": transition["cycles"],
            "cycle_count": transition["cycle_count"],
            "initial": transition["initial"],
            "final": transition["final"],
            "settled": transition["settled"],
        }

    def _typed_trace_section(self, selected_chain, selected_cig):
        try:
            from .ts_core_adapter import channel_context, channel_results_to_trace, chain_to_graph
            from ts_core import TypedTensionRuntime

            from .reasoning_channels import default_reasoning_channels
        except ModuleNotFoundError as exc:
            return {
                "tension_channels": {},
                "typed_runtime": {
                    "available": False,
                    "reason": f"TS-Core typed kernel unavailable: {exc}",
                },
            }

        typed_graph = chain_to_graph(selected_chain, selected_cig)
        typed_context = channel_context(selected_chain, selected_cig)
        typed_trace = TypedTensionRuntime(default_reasoning_channels()).run(typed_graph, typed_context)
        return {
            "tension_channels": channel_results_to_trace(typed_trace.channel_results),
            "typed_runtime": {
                "available": True,
                "settled": typed_trace.settled,
                "global_tension": typed_trace.global_tension,
                "resolver_events": [event.to_dict() for event in typed_trace.resolver_events],
                "context": {
                    "blocked_edges": typed_context.get("blocked_edges", []),
                    "blocked_equalities": typed_context.get("blocked_equalities", []),
                    "surface_tags": typed_context.get("surface_tags", {}),
                    "abstention": typed_context.get("abstention"),
                    "contradiction_flagged": typed_context.get("contradiction_flagged", False),
                    "quantifier_scope_blocked": typed_context.get("quantifier_scope_blocked", False),
                },
            },
        }

    def _chosen_action(self, transition: dict) -> dict:
        cycles = transition["cycles"]
        last_cycle = cycles[-1] if cycles else {}
        return {
            "status": transition["status"],
            "settled": transition["settled"],
            "selected_op": last_cycle.get("selected_op"),
            "target": last_cycle.get("target"),
            "final_global_tension": transition["score"].global_tension,
        }

    def _rejected_alternatives(self, candidate_rows: list[dict], selected_chain_id: str) -> list[dict]:
        rejected = []
        for row in candidate_rows:
            post_loop_chain_id = row["post_loop_chain_id"]
            if row["chain_id"] == selected_chain_id or post_loop_chain_id == selected_chain_id:
                continue
            rejected.append(
                {
                    "chain_id": row["chain_id"],
                    "post_loop_chain_id": post_loop_chain_id,
                    "global_tension": row["global_tension"],
                    "post_loop_global_tension": row["post_loop_global_tension"],
                    "issue_kinds": row["issue_kinds"],
                    "reason": row["post_loop_status"],
                }
            )
        return rejected


def run_reasoner(
    question: str,
    premises: Optional[Iterable[str]] = None,
    ranker=None,
    generator=None,
    tension_coordinator=None,
) -> ReasonerOutput:
    return TSReasoner(
        ranker=ranker,
        generator=generator,
        tension_coordinator=tension_coordinator,
    ).run(question, premises)
