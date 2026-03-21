from __future__ import annotations

import logging
import threading
from typing import Any, Dict

from .runtime import BoggersRuntime

logger = logging.getLogger("boggers.api")

_shared_runtime: BoggersRuntime | None = None
_runtime_lock = threading.Lock()


def get_runtime() -> BoggersRuntime:
    global _shared_runtime
    if _shared_runtime is not None:
        return _shared_runtime
    with _runtime_lock:
        if _shared_runtime is None:
            _shared_runtime = BoggersRuntime()
        return _shared_runtime


def handle_query(
    payload: Dict[str, Any], runtime: BoggersRuntime | None = None
) -> Dict[str, Any]:
    rt = runtime or get_runtime()
    query = str(payload.get("query", "")).strip()
    if not query:
        return {"ok": False, "error": "query is required"}
    try:
        response = rt.ask(query)
    except Exception as exc:
        logger.error("Query failed: %s", exc)
        return {"ok": False, "error": str(exc)}
    return {
        "ok": True,
        "query": response.query,
        "answer": response.answer,
        "topics": response.topics,
        "sufficiency_score": response.sufficiency_score,
        "used_research": response.used_research,
        "used_tool": response.used_tool,
        "tool_name": response.tool_name,
        "consolidated_merges": response.consolidated_merges,
        "insight_path": response.insight_path,
        "hypotheses": response.hypotheses,
        "confidence": response.confidence,
        "reasoning_trace": response.reasoning_trace,
    }
