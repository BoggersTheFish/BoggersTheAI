from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from .kernel.receipts import validate_receipt_hash


@dataclass(slots=True)
class TraceProcessorConfig:
    traces_dir: str = "traces"
    min_confidence: float = 0.75
    max_samples: int = 5000
    output_dir: str = "dataset"
    split_ratio: float = 0.8


class TraceProcessor:
    def __init__(self, config: object | None = None) -> None:
        self.config = self._resolve_config(config)
        self.traces_dir = Path(self.config.traces_dir)
        self.output_dir = Path(self.config.output_dir)

    def build_dataset(self, max_samples: int = 5000) -> dict:
        cap = max(1, min(int(max_samples), int(self.config.max_samples)))
        rows: List[Dict[str, Any]] = []
        rejected_rows: List[Dict[str, Any]] = []
        category_counts: Dict[str, int] = {}
        confidence_values: List[float] = []

        if self.traces_dir.exists():
            for trace_file in sorted(self.traces_dir.glob("*.jsonl")):
                for raw in self._read_jsonl(trace_file):
                    category = self._trace_category(raw)
                    category_counts[category] = category_counts.get(category, 0) + 1
                    if not self._is_training_eligible(raw):
                        rejected_rows.append(
                            {
                                "trace_category": category,
                                "query": raw.get("query", ""),
                                "reason": "not_a_replay_verified_committed_transaction",
                            }
                        )
                        continue
                    confidence = float(raw.get("confidence", 0.0))
                    if confidence < float(self.config.min_confidence):
                        continue
                    item = self._to_alpaca(raw)
                    if item is None:
                        continue
                    rows.append(item)
                    confidence_values.append(confidence)
                    if len(rows) >= cap:
                        break
                if len(rows) >= cap:
                    break

        split_idx = int(len(rows) * float(self.config.split_ratio))
        train_rows = rows[:split_idx]
        val_rows = rows[split_idx:]

        self.output_dir.mkdir(parents=True, exist_ok=True)
        train_path = self.output_dir / "train.jsonl"
        val_path = self.output_dir / "val.jsonl"
        rejected_path = self.output_dir / "rejected_traces.jsonl"
        self._write_jsonl(train_path, train_rows)
        self._write_jsonl(val_path, val_rows)
        self._write_jsonl(rejected_path, rejected_rows)

        avg_confidence = (
            sum(confidence_values) / len(confidence_values)
            if confidence_values
            else 0.0
        )
        return {
            "samples_built": len(rows),
            "train_samples": len(train_rows),
            "val_samples": len(val_rows),
            "avg_confidence": round(avg_confidence, 4),
            "min_confidence": float(self.config.min_confidence),
            "traces_dir": str(self.traces_dir),
            "output_dir": str(self.output_dir),
            "train_path": str(train_path),
            "val_path": str(val_path),
            "rejected_path": str(rejected_path),
            "category_counts": category_counts,
        }

    def _resolve_config(self, config: object | None) -> TraceProcessorConfig:
        if config is None:
            return TraceProcessorConfig()
        if isinstance(config, TraceProcessorConfig):
            return config

        if isinstance(config, dict):
            inference = config.get("inference", {})
            self_imp = (
                inference.get("self_improvement", {})
                if isinstance(inference, dict)
                else {}
            )
            dataset_build = (
                self_imp.get("dataset_build", {}) if isinstance(self_imp, dict) else {}
            )
            return TraceProcessorConfig(
                traces_dir=str(self_imp.get("traces_dir", "traces")),
                min_confidence=float(dataset_build.get("min_confidence", 0.75)),
                max_samples=int(dataset_build.get("max_samples", 5000)),
                output_dir=str(dataset_build.get("output_dir", "dataset")),
                split_ratio=float(dataset_build.get("split_ratio", 0.8)),
            )

        inference_cfg = getattr(config, "inference", {})
        self_imp = (
            inference_cfg.get("self_improvement", {})
            if isinstance(inference_cfg, dict)
            else {}
        )
        dataset_build = (
            self_imp.get("dataset_build", {}) if isinstance(self_imp, dict) else {}
        )
        return TraceProcessorConfig(
            traces_dir=str(self_imp.get("traces_dir", "traces")),
            min_confidence=float(dataset_build.get("min_confidence", 0.75)),
            max_samples=int(dataset_build.get("max_samples", 5000)),
            output_dir=str(dataset_build.get("output_dir", "dataset")),
            split_ratio=float(dataset_build.get("split_ratio", 0.8)),
        )

    def _to_alpaca(self, raw: Dict[str, Any]) -> Dict[str, str] | None:
        query = str(raw.get("query", "")).strip()
        answer = str(raw.get("answer", "")).strip()
        reasoning_trace = str(raw.get("reasoning_trace", "")).strip()
        tension = float(raw.get("graph_tension", 0.0))
        cycle = int(raw.get("cycle_count", 0))

        if not query or not answer:
            return None

        return {
            "instruction": query,
            "input": f"Graph context (tension: {tension:.2f}, cycle: {cycle})",
            "output": f"{answer}\n\nReasoning trace: {reasoning_trace}",
        }

    def _trace_category(self, raw: Dict[str, Any]) -> str:
        explicit = str(raw.get("trace_category", "")).strip()
        receipt = raw.get("receipt")
        if isinstance(receipt, dict):
            decision = str(receipt.get("commit_decision", ""))
            if decision == "commit":
                if explicit and explicit != "verified_success":
                    return explicit
                return (
                    "verified_success"
                    if self._is_training_eligible(raw)
                    else "committed_unverified_trace"
                )
            if decision == "reject":
                return "repair_candidate"
            if decision == "abstain":
                return "abstention"
            if decision == "quarantine":
                return "quarantine_trace"
            if decision == "branch":
                return "adversarial_branch_trace"
        if explicit and explicit != "verified_success":
            return explicit
        return "unverified_confidence_trace"

    def _is_training_eligible(self, raw: Dict[str, Any]) -> bool:
        receipt = raw.get("receipt")
        if not isinstance(receipt, dict):
            return False
        if receipt.get("commit_decision") != "commit":
            return False
        if not validate_receipt_hash(receipt):
            return False
        renderer_metadata = receipt.get("renderer_metadata", {})
        replay_verified = bool(raw.get("replay_verified", False)) or bool(
            renderer_metadata.get("replay_verified", False)
            if isinstance(renderer_metadata, dict)
            else False
        )
        if not replay_verified:
            return False
        obligations = receipt.get("verifier_obligations", [])
        results = receipt.get("verification_results", [])
        results_by_obligation: dict[str, list[dict[str, Any]]] = {}
        for result in results:
            results_by_obligation.setdefault(
                str(result.get("obligation_id", "")), []
            ).append(result)
        for obligation in obligations:
            if not obligation.get("required", True):
                continue
            obligation_results = results_by_obligation.get(
                str(obligation.get("id", "")), []
            )
            if len(obligation_results) != 1:
                return False
            if obligation_results[0].get("outcome") != "pass":
                return False
        if receipt.get("commit_reason", "").startswith("requires_repair"):
            return False
        operations = receipt.get("proposed_operations", [])
        return any(self._has_explicit_provenance(op) for op in operations)

    def _has_explicit_provenance(self, operation: Any) -> bool:
        if not isinstance(operation, dict):
            return False
        provenance = operation.get("provenance")
        if not isinstance(provenance, dict):
            return False
        source = str(provenance.get("source", "")).strip()
        detail = str(provenance.get("detail", "")).strip()
        return bool(source and detail)

    def _read_jsonl(self, path: Path) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return rows
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
        return rows

    def _write_jsonl(self, path: Path, rows: List[Dict[str, Any]]) -> None:
        payload = "\n".join(json.dumps(row, ensure_ascii=True) for row in rows)
        if payload:
            payload += "\n"
        path.write_text(payload, encoding="utf-8")
