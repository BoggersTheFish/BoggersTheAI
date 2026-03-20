from __future__ import annotations

import json
from urllib.parse import quote_plus
from urllib.request import urlopen


class SearchTool:
    def execute(self, **kwargs) -> str:
        query = str(kwargs.get("query", "")).strip()
        if not query:
            return "Search query is empty."

        url = (
            "https://hn.algolia.com/api/v1/search?tags=story&hitsPerPage=5&query="
            f"{quote_plus(query)}"
        )
        try:
            with urlopen(url, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # pragma: no cover - network dependent
            return f"Search failed: {exc}"

        hits = payload.get("hits", [])
        if not hits:
            return "No search results."
        lines = []
        for index, hit in enumerate(hits, start=1):
            title = (hit.get("title") or "untitled").strip()
            link = (hit.get("url") or "").strip()
            lines.append(f"{index}. {title} {link}".strip())
        return "\n".join(lines)
