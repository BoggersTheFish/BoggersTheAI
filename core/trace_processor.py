from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


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
        confidence_values: List[float] = []

        if self.traces_dir.exists():
            for trace_file in sorted(self.traces_dir.glob("*.jsonl")):
                for raw in self._read_jsonl(trace_file):
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
        self._write_jsonl(train_path, train_rows)
        self._write_jsonl(val_path, val_rows)

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
        }

    def _resolve_config(self, config: object | None) -> TraceProcessorConfig:
        if config is None:
            return TraceProcessorConfig()

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
