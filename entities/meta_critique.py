from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class MetaCritiqueNode:
    """Append-only JSONL store for meta prompts + traces (CPU / graph path)."""

    traces_dir: Path = field(default_factory=lambda: Path("traces/meta_critique"))

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
        }
        text = json.dumps(payload, ensure_ascii=False) + "\n"
        path.write_text(text, encoding="utf-8")
        return path
