"""Externalized small-reasoning benchmark harness for TS-Reasoner."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

from .cig_checker import CIGChecker
from .generator import DeterministicHeuristicGenerator
from .pipeline import run_reasoner
from .ranker import HeuristicTensionRanker
from .tension_agents import TensionCoordinator
from .types import ReasoningChain


@dataclass(frozen=True)
class BenchmarkTask:
    task_id: str
    category: str
    source: str
    external_prompt: str
    question: str
    premises: List[str]
    acceptable_answers: List[str]
    expected_status: str = "expected_pass"
    notes: str = ""


def load_benchmark(path: str | Path) -> List[BenchmarkTask]:
    tasks: List[BenchmarkTask] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            tasks.append(
                BenchmarkTask(
                    task_id=str(row["id"]),
                    category=str(row["category"]),
                    source=str(row.get("source", "unknown")),
                    external_prompt=str(row.get("external_prompt", "")),
                    question=str(row["question"]),
                    premises=[str(premise) for premise in row.get("premises", [])],
                    acceptable_answers=[str(answer) for answer in row["acceptable_answers"]],
                    expected_status=str(row.get("expected_status", "expected_pass")),
                    notes=str(row.get("notes", "")),
                )
            )
    return tasks


class BenchmarkRunner:
    """Run externalized tasks through simple baselines and the control loop."""

    def __init__(self, tension_coordinator: TensionCoordinator | None = None, random_seed: int = 17) -> None:
        self.generator = DeterministicHeuristicGenerator()
        self.checker = CIGChecker()
        self.ranker = HeuristicTensionRanker()
        self.tension_coordinator = tension_coordinator
        self.random_seed = random_seed

    def evaluate(self, tasks: Sequence[BenchmarkTask]) -> Dict[str, object]:
        rows = [self._evaluate_task(task) for task in tasks]
        baselines = ["direct", "random_selector", "ranker_only", "full_control_loop"]
        baseline_summary = {
            baseline: self._summarize_baseline(rows, baseline)
            for baseline in baselines
        }
        by_category = {
            category: {
                baseline: self._summarize_baseline(
                    [row for row in rows if row["category"] == category],
                    baseline,
                )
                for baseline in baselines
            }
            for category in sorted({row["category"] for row in rows})
        }
        return {
            "version": "v0.8.0",
            "task_count": len(rows),
            "baselines": baseline_summary,
            "by_category": by_category,
            "by_expected_status": self._summarize_expected_status(rows, baselines),
            "tasks": rows,
            "claim": "Externalized small reasoning tasks compare direct, random, ranker-only, and full bounded tension-control baselines.",
        }

    def _evaluate_task(self, task: BenchmarkTask) -> Dict[str, object]:
        candidates = self.generator.generate(task.question, task.premises)
        direct = candidates[0]
        random_candidate = self._random_candidate(task, candidates)
        ranker_chain, ranker_score = self._ranker_only(candidates)
        full = run_reasoner(
            task.question,
            task.premises,
            tension_coordinator=self.tension_coordinator,
        )
        full_loop = full.trace["operation_loop"]
        return {
            "task_id": task.task_id,
            "category": task.category,
            "source": task.source,
            "external_prompt": task.external_prompt,
            "question": task.question,
            "premises": task.premises,
            "acceptable_answers": task.acceptable_answers,
            "expected_status": task.expected_status,
            "baselines": {
                "direct": self._baseline_row(direct, task),
                "random_selector": self._baseline_row(random_candidate, task),
                "ranker_only": self._baseline_row(ranker_chain, task, ranker_score.global_tension),
                "full_control_loop": {
                    "answer": full.final_answer,
                    "correct": answer_matches(full.final_answer, task.acceptable_answers),
                    "selected_chain_id": full.selected_chain.chain_id,
                    "global_tension": full.tension_score.global_tension,
                    "cycles_used": full_loop["cycle_count"],
                    "settled": full_loop["settled"],
                    "status": full_loop["status"],
                },
            },
        }

    def _baseline_row(
        self,
        chain: ReasoningChain,
        task: BenchmarkTask,
        global_tension: float | None = None,
    ) -> Dict[str, object]:
        tension = global_tension
        if tension is None:
            tension = self.ranker.score(chain, self.checker.check(chain)).global_tension
        return {
            "answer": chain.final_answer,
            "correct": answer_matches(chain.final_answer, task.acceptable_answers),
            "selected_chain_id": chain.chain_id,
            "global_tension": tension,
        }

    def _random_candidate(self, task: BenchmarkTask, candidates: Sequence[ReasoningChain]) -> ReasoningChain:
        rng = random.Random(f"{self.random_seed}:{task.task_id}")
        return list(candidates)[rng.randrange(len(candidates))]

    def _ranker_only(self, candidates: Sequence[ReasoningChain]) -> tuple[ReasoningChain, object]:
        scored = []
        for chain in candidates:
            score = self.ranker.score(chain, self.checker.check(chain))
            scored.append((chain, score))
        return min(scored, key=lambda item: (item[1].global_tension, -item[1].stability, item[0].chain_id))

    def _summarize_baseline(self, rows: Sequence[Dict[str, object]], baseline: str) -> Dict[str, object]:
        if not rows:
            return {"accuracy": 0.0, "correct": 0, "total": 0}
        baseline_rows = [row["baselines"][baseline] for row in rows]
        correct = sum(1 for row in baseline_rows if row["correct"])
        summary: Dict[str, object] = {
            "accuracy": round(correct / len(baseline_rows), 4),
            "correct": correct,
            "total": len(baseline_rows),
            "mean_global_tension": round(
                sum(float(row["global_tension"]) for row in baseline_rows) / len(baseline_rows),
                4,
            ),
        }
        if baseline == "full_control_loop":
            summary["settled_rate"] = round(
                sum(1 for row in baseline_rows if row["settled"]) / len(baseline_rows),
                4,
            )
            summary["mean_cycles_used"] = round(
                sum(int(row["cycles_used"]) for row in baseline_rows) / len(baseline_rows),
                4,
            )
        return summary

    def _summarize_expected_status(
        self,
        rows: Sequence[Dict[str, object]],
        baselines: Sequence[str],
    ) -> Dict[str, object]:
        return {
            status: {
                baseline: self._summarize_baseline(
                    [row for row in rows if row["expected_status"] == status],
                    baseline,
                )
                for baseline in baselines
            }
            for status in sorted({str(row["expected_status"]) for row in rows})
        }


def answer_matches(answer: str, acceptable_answers: Iterable[str]) -> bool:
    normalized = _normalize(answer)
    return any(_normalize(acceptable) in normalized for acceptable in acceptable_answers)


def _normalize(text: str) -> str:
    return " ".join(text.lower().replace(".", "").split())
