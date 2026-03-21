from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger("boggers.tools.router")


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
                logger.info("Routing to file_read: path=%s", path)
                return ToolCall(tool_name="file_read", args={"path": path})

        if self._is_code_run_query(raw_query):
            code = self._extract_code_block(raw_query)
            if code:
                language = self._detect_language(q)
                logger.info("Routing to code_run: language=%s", language)
                return ToolCall(
                    tool_name="code_run", args={"code": code, "language": language}
                )

        if self._is_math_query(q):
            expression = self._extract_math_expression(query)
            if expression:
                logger.info("Routing to calc: expression=%s", expression)
                return ToolCall(tool_name="calc", args={"expression": expression})

        if self._is_web_search_query(q):
            logger.info(
                "Routing to web_search: query=%s",
                raw_query[:80],
            )
            return ToolCall(
                tool_name="web_search",
                args={"query": raw_query},
            )

        if self._is_datetime_query(q):
            logger.info("Routing to datetime")
            return ToolCall(
                tool_name="datetime",
                args={"action": "now"},
            )

        if self._is_unit_convert_query(q):
            logger.info("Routing to unit_convert")
            return ToolCall(
                tool_name="unit_convert",
                args=self._extract_convert_args(q),
            )

        if "search for" in q or "look up" in q or q.startswith("search "):
            search_query = query.strip()
            logger.info(
                "Routing to search (explicit): query=%s",
                search_query[:80],
            )
            return ToolCall(
                tool_name="search",
                args={"query": search_query},
            )

        if sufficiency_score < self.sufficiency_threshold:
            fallback = " ".join(topics) if topics else query.strip()
            logger.info(
                "Routing to search (fallback, score=%.2f): query=%s",
                sufficiency_score,
                fallback[:80],
            )
            return ToolCall(tool_name="search", args={"query": fallback})

        logger.info("No tool routed (sufficiency=%.2f)", sufficiency_score)
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
        return "python"

    def _extract_math_expression(self, query: str) -> str | None:
        match = re.search(r"([-+*/().\d\s]{3,})", query)
        if not match:
            return None
        expression = match.group(1).strip()
        if re.fullmatch(r"[-+*/().\d\s]+", expression):
            return expression
        return None

    def _is_web_search_query(self, q: str) -> bool:
        triggers = [
            "search the web",
            "look up online",
            "duckduckgo",
        ]
        return any(t in q for t in triggers)

    def _is_datetime_query(self, q: str) -> bool:
        triggers = [
            "what time",
            "current date",
            "parse date",
        ]
        return any(t in q for t in triggers)

    _UNIT_KEYWORDS = [
        "km",
        "miles",
        "kg",
        "lbs",
        "celsius",
        "fahrenheit",
        "meters",
        "feet",
    ]

    def _is_unit_convert_query(self, q: str) -> bool:
        has_trigger = "convert" in q or "how many" in q
        has_unit = any(u in q for u in self._UNIT_KEYWORDS)
        return has_trigger and has_unit

    def _extract_convert_args(self, q: str) -> dict:
        nums = re.findall(r"[\d.]+", q)
        value = float(nums[0]) if nums else 0.0
        from_u = ""
        to_u = ""
        for kw in self._UNIT_KEYWORDS:
            if kw in q:
                if not from_u:
                    from_u = kw
                else:
                    to_u = kw
                    break
        return {
            "value": value,
            "from": from_u,
            "to": to_u,
        }
