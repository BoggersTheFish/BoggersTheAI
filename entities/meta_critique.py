from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class MetaCritiqueNode:
    """
    Append-only JSONL + unified wave log for TS meta-critique.
    High-confidence traces for wave cycles, external TS wave markdown, and bootstrap.
    """

    traces_dir: Path = field(default_factory=lambda: Path("traces/meta_critique"))
    wave_log_name: str = "waves.jsonl"

    def ingest(
        self,
        prompt: str,
        traces: list[dict[str, Any]] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> Path:
        self.traces_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
        path = self.traces_dir / f"meta_critique_{ts}.jsonl"
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "prompt": prompt,
            "traces": traces or [],
            "extra": extra or {},
            "confidence": 0.85,
            "kind": "ingest",
        }
        self._write_jsonl(path, payload)
        return path

    def ingest_wave_cycle_event(self, event: dict[str, Any]) -> Path:
        """Record every graph wave cycle from EventBus (high confidence)."""
        self.traces_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
        path = self.traces_dir / f"wave_cycle_{ts}.jsonl"
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "kind": "wave_cycle",
            "confidence": 0.95,
            "event": dict(event),
        }
        self._write_jsonl(path, payload)
        self._append_wave_log(payload)
        return path

    def ingest_ts_wave_document(
        self,
        wave_number: str,
        slug: str,
        body: str,
        *,
        confidence: float = 0.95,
        extra: dict[str, Any] | None = None,
    ) -> Path:
        """Ingest a full external TS wave markdown (e.g. Cursor/Grok output)."""
        self.traces_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
        safe = re.sub(r"[^a-zA-Z0-9_-]+", "-", slug)[:48].strip("-") or "wave"
        path = self.traces_dir / f"ts_wave_{wave_number}_{safe}_{ts}.jsonl"
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "kind": "ts_wave_document",
            "wave_number": wave_number,
            "slug": slug,
            "body": body,
            "confidence": max(0.0, min(float(confidence), 1.0)),
            "extra": extra or {},
        }
        self._write_jsonl(path, payload)
        self._append_wave_log(payload)
        return path

    def _append_wave_log(self, payload: dict[str, Any]) -> None:
        log_path = self.traces_dir / self.wave_log_name
        line = json.dumps(payload, ensure_ascii=False) + "\n"
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(line)

    def _write_jsonl(self, path: Path, payload: dict[str, Any]) -> None:
        path.write_text(
            json.dumps(payload, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
