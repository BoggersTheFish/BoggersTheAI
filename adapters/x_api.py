from __future__ import annotations

from typing import List

from ..core.types import Node


class XApiAdapter:
    poll_interval = 60

    def ingest(self, source: str) -> List[Node]:
        # Auth-backed adapter intentionally deferred (Phase 3 of plan).
        _ = source
        return []
