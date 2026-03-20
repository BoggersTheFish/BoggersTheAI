from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass(slots=True)
class ToolCall:
    tool_name: str
    args: dict


class ToolRouter:
    def __init__(self, sufficiency_threshold: float = 0.4) -> None:
        self.sufficiency_threshold = sufficiency_threshold

    def route(
        self, query: str, sufficiency_score: float, topics: List[str] | None = None
    ) -> Optional[ToolCall]:
        raw_query = query.strip()
        q = raw_query.lower()
        topics = topics or []

        if self._is_file_read_query(q):
            path = self._extract_quoted_or_backticked(raw_query)
            if path:
                return ToolCall(tool_name="file_read", args={"path": path})

        if self._is_code_run_query(raw_query):
            code = self._extract_code_block(raw_query)
            if code:
                language = self._detect_language(q)
                return ToolCall(
                    tool_name="code_run", args={"code": code, "language": language}
                )

        if self._is_math_query(q):
            expression = self._extract_math_expression(query)
            if expression:
                return ToolCall(tool_name="calc", args={"expression": expression})

        if "search for" in q or "look up" in q or q.startswith("search "):
            search_query = query.strip()
            return ToolCall(tool_name="search", args={"query": search_query})

        if sufficiency_score < self.sufficiency_threshold:
            fallback = " ".join(topics) if topics else query.strip()
            return ToolCall(tool_name="search", args={"query": fallback})

        return None

    def _is_file_read_query(self, query: str) -> bool:
        return "read file" in query or "open file" in query

    def _is_code_run_query(self, query: str) -> bool:
        lowered = query.lower()
        return "run" in lowered and ("```" in query or "code" in lowered)

    def _is_math_query(self, query: str) -> bool:
        return bool(re.search(r"[\d\)\(]\s*[\+\-\*/]\s*[\d\(]", query))

    def _extract_quoted_or_backticked(self, query: str) -> str | None:
        match = re.search(r"`([^`]+)`|\"([^\"]+)\"|'([^']+)'", query)
        if not match:
            return None
        return next(group for group in match.groups() if group)

    def _extract_code_block(self, query: str) -> str | None:
        match = re.search(r"```(?:\w+)?\n([\s\S]*?)```", query)
        if match:
            return match.group(1).strip()
        return None

    def _detect_language(self, query: str) -> str:
        if "python" in query:
            return "python"
        if "bash" in query or "shell" in query:
            return "shell"
        return "python"

    def _extract_math_expression(self, query: str) -> str | None:
        match = re.search(r"([-+*/().\d\s]{3,})", query)
        if not match:
            return None
        expression = match.group(1).strip()
        if re.fullmatch(r"[-+*/().\d\s]+", expression):
            return expression
        return None
