from __future__ import annotations

from typing import Any, Dict

from .runtime import BoggersRuntime


def handle_query(payload: Dict[str, Any], runtime: BoggersRuntime | None = None) -> Dict[str, Any]:
    rt = runtime or BoggersRuntime()
    query = str(payload.get("query", "")).strip()
    if not query:
        return {"ok": False, "error": "query is required"}
    response = rt.ask(query)
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
