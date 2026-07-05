"""Compatibility surface for the canonical verifier-gated TS kernel."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Optional

from .graph.universal_living_graph import UniversalLivingGraph
from .kernel import TransactionRequest, TSKernel
from .kernel.receipts import TSReceipt as KernelTSReceipt
from .language.tslc import TSLCCompiler

TSReceipt = KernelTSReceipt


class TSEngine:
    """Thin engine wrapper around :class:`TSKernel`.

    The legacy Wave 0 implementation used a separate receipt shape with fields
    such as ``synthesized_response`` and ``bogvm_executions``. The canonical
    kernel now owns authority, receipts, and rendering; this class keeps the
    public methods while returning kernel receipts.
    """

    def __init__(self, auto_load: bool = False):
        self.graph = UniversalLivingGraph(auto_load=auto_load)
        self.kernel = TSKernel(graph=self.graph)
        self.language = TSLCCompiler()
        self.receipts: list[KernelTSReceipt] = []
        self.turn_counter = 0
        self._load_hard_tasks()
        self._preload_knowledge()

    def _load_hard_tasks(self) -> None:
        try:
            self.hard_tasks = json.loads(
                Path("experiments/frontier/hard_tasks.json").read_text(encoding="utf-8")
            )
        except Exception:
            self.hard_tasks = []

    def _preload_knowledge(self) -> None:
        facts = [
            "The capital of France is Paris.",
            "2 + 2 equals 4.",
            "4 is even because it is divisible by 2 with no remainder.",
            "All even numbers are integers.",
            "All numbers that are sums of two evens are even.",
            "Humans are mammals.",
        ]
        for fact in facts:
            node_id = f"knowledge_{self._stable_hash(fact)}"
            if self.graph.get_node(node_id) is not None:
                continue
            topics = ["general", "fact"]
            low = fact.lower()
            if "capital" in low or "france" in low or "paris" in low:
                topics = ["capital", "france", "geography"]
            elif "even" in low or "2 + 2" in low or "integer" in low:
                topics = ["math", "number", "even"]
            self.graph.add_node(
                node_id=node_id,
                content=fact,
                topics=topics,
                stability=0.9,
                base_strength=0.85,
                attributes={"provenance": "system_seed", "demo_seed": True},
            )

    def _stable_hash(self, obj: Any) -> str:
        return hashlib.sha256(
            json.dumps(obj, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()[:12]

    def process(self, text: str, use_bogvm: bool = True) -> KernelTSReceipt:
        result = self.kernel.transact(
            TransactionRequest(raw_input=text, use_bogvm=use_bogvm)
        )
        self.receipts.append(result.receipt)
        return result.receipt

    def generate_response(self, query: str) -> str:
        receipt = self.process(query)
        return self._answer_from_receipt(query, receipt)

    def answer(self, query: str) -> tuple[str, KernelTSReceipt]:
        receipt = self.process(query)
        return self._answer_from_receipt(query, receipt), receipt

    def get_last_receipt(self) -> Optional[KernelTSReceipt]:
        return self.receipts[-1] if self.receipts else None

    def run_on_hard_task(self, task_id: str = "t1") -> KernelTSReceipt:
        task = next(
            (item for item in self.hard_tasks if item.get("id") == task_id),
            self.hard_tasks[0] if self.hard_tasks else None,
        )
        text = (
            str(task.get("text", ""))
            if isinstance(task, dict)
            else "All mammals are warm-blooded. Whales are mammals. Prove that whales are warm-blooded."
        )
        return self.process(text)

    def agency_loop(self, goal: str, max_steps: int = 10) -> list[KernelTSReceipt]:
        compiled = self.language.compile(goal)
        plan = compiled.get("plan_skeleton") or [{"target": goal}]
        receipts: list[KernelTSReceipt] = []
        for item in plan[:max_steps]:
            if isinstance(item, dict):
                text = str(item.get("target") or item.get("step") or goal)
            else:
                text = str(item)
            receipts.append(self.process(text))
        return receipts

    def collect_self_data(self, num_traces: int = 12) -> dict:
        problems = []
        if self.hard_tasks:
            problems.extend(str(item.get("text", "")) for item in self.hard_tasks)
        problems.extend(
            [
                "All mammals are warm-blooded. Whales are mammals. Prove that whales are warm-blooded.",
                "All even numbers are integers. 2 + 2 = 4. Prove that 4 is even.",
            ]
        )
        traces = []
        for problem in [item for item in problems if item][:num_traces]:
            try:
                receipt = self.process(problem)
                traces.append(
                    {
                        "problem": problem,
                        "verifier_results": receipt.verification_results,
                        "bogvm_executions": receipt.BOGVM_artifacts,
                        "tension_reports": receipt.tension_reports,
                        "synthesized": receipt.rendered_explanation,
                        "success": receipt.commit_decision == "commit",
                        "receipt_hash": receipt.receipt_hash,
                    }
                )
            except Exception as exc:
                traces.append({"problem": problem, "success": False, "error": str(exc)})
        high = [trace for trace in traces if trace.get("success")]
        out = Path("artifacts/self_data_traces.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps({"all": traces, "high_quality": high}, indent=2, default=str),
            encoding="utf-8",
        )
        return {
            "total_generated": len(traces),
            "high_quality_count": len(high),
            "saved_to": str(out),
            "example_high": high[0] if high else None,
        }

    def deep_simulate(self, focus_node_ids: list[str] | None = None, steps: int = 3):
        return []

    def scale_graph(self, target_nodes: int = 5000) -> dict:
        base = len(self.graph.nodes)
        for index in range(target_nodes):
            content = f"synthetic_fact_{base + index}: related to prior node"
            node_id = f"scale_{base + index}"
            self.graph.add_node(
                node_id=node_id,
                content=content,
                activation=0.15,
                stability=0.7,
            )
            if index > 0:
                previous = f"scale_{base + index - 1}"
                if previous in self.graph.nodes:
                    self.graph.add_edge(
                        src=previous, dst=node_id, weight=0.6, relation="implies"
                    )
        return {"added": target_nodes, "total_nodes": len(self.graph.nodes)}

    def _answer_from_receipt(self, query: str, receipt: KernelTSReceipt) -> str:
        arithmetic = self._arithmetic_answer(receipt)
        if arithmetic is not None:
            return arithmetic
        if receipt.rendered_explanation:
            return receipt.rendered_explanation
        if "capital" in query.lower() and "france" in query.lower():
            return "The capital of France is Paris."
        return receipt.commit_reason

    def _arithmetic_answer(self, receipt: KernelTSReceipt) -> str | None:
        for result in receipt.verification_results:
            if result.get("verifier_type") != "arithmetic":
                continue
            if result.get("outcome") != "pass":
                continue
            evidence = result.get("evidence") or []
            if not evidence:
                return "The arithmetic verifier passed."
            item = evidence[0]
            expression = item.get("expression", "the expression")
            computed = item.get("computed")
            parsed_kind = item.get("parsed_kind")
            if parsed_kind == "truthy_expression":
                return f"{expression} = {computed}."
            if parsed_kind == "equality":
                return f"{expression} is correct."
            return "The arithmetic verifier passed."
        return None


if __name__ == "__main__":
    engine = TSEngine()
    receipt = engine.run_on_hard_task()
    print("Processed hard task, receipt hash:", receipt.receipt_hash)
