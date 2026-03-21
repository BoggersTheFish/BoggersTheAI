from __future__ import annotations

import hashlib
import logging
from typing import List
from urllib.parse import urlencode

from ..core.types import Node
from .http_client import fetch_json

logger = logging.getLogger("boggers.adapters.wikipedia")


class WikipediaAdapter:
    poll_interval = 0  # one-shot

    def ingest(self, source: str) -> List[Node]:
        topic = source.strip()
        if not topic:
            return []
        params = urlencode(
            {
                "action": "query",
                "prop": "extracts",
                "explaintext": "1",
                "format": "json",
                "titles": topic,
            }
        )
        url = f"https://en.wikipedia.org/w/api.php?{params}"

        try:
            payload = fetch_json(url)
        except Exception as exc:
            logger.warning(
                "Wikipedia fetch failed for '%s': %s",
                topic,
                exc,
            )
            return []

        pages = payload.get("query", {}).get("pages", {})
        nodes: List[Node] = []
        for page in pages.values():
            title = page.get("title", topic)
            extract = (page.get("extract") or "").strip()
            if not extract:
                continue
            digest = hashlib.sha1(f"wikipedia:{title}".encode("utf-8")).hexdigest()[:12]
            nodes.append(
                Node(
                    id=f"wiki:{digest}",
                    content=extract,
                    topics=[topic.lower(), title.lower()],
                    activation=0.2,
                    stability=0.7,
                )
            )
        return nodes
