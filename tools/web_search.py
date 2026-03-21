from __future__ import annotations

import json
import logging
from urllib.error import URLError
from urllib.request import urlopen

logger = logging.getLogger("boggers.tools.web_search")


class WebSearchTool:
    """Search DuckDuckGo instant answers (no key)."""

    def execute(self, **kwargs) -> str:
        query = str(kwargs.get("query", "")).strip()
        if not query:
            return "No query provided."
        try:
            url = "https://api.duckduckgo.com/" f"?q={query}&format=json&no_html=1"
            with urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read())
            abstract = data.get("AbstractText", "")
            if abstract:
                return abstract
            related = data.get("RelatedTopics", [])
            if related and isinstance(related[0], dict):
                return related[0].get("Text", "No results found.")
            return "No results found."
        except (
            URLError,
            OSError,
            json.JSONDecodeError,
        ) as exc:
            logger.warning("Web search failed: %s", exc)
            return f"Search failed: {exc}"
