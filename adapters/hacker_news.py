from __future__ import annotations

import hashlib
import logging
from typing import List
from urllib.parse import quote_plus

from ..core.types import Node
from .http_client import fetch_json

logger = logging.getLogger("boggers.adapters.hacker_news")


class HackerNewsAdapter:
    poll_interval = 900

    def ingest(self, source: str) -> List[Node]:
        query = source.strip() or "technology"
        url = (
            "https://hn.algolia.com/api/v1/search?tags=story&hitsPerPage=20&query="
            f"{quote_plus(query)}"
        )
        try:
            payload = fetch_json(url)
        except Exception as exc:
            logger.warning(
                "HackerNews fetch failed for '%s': %s",
                query,
                exc,
            )
            return []

        nodes: List[Node] = []
        for hit in payload.get("hits", []):
            title = (hit.get("title") or "").strip()
            story_text = (hit.get("story_text") or "").strip()
            url_value = (hit.get("url") or "").strip()
            content = " ".join(
                [segment for segment in [title, story_text] if segment]
            ).strip()
            if not content:
                continue
            digest = hashlib.sha1(
                f"hn:{url_value or title}".encode("utf-8")
            ).hexdigest()[:12]
            nodes.append(
                Node(
                    id=f"hn:{digest}",
                    content=content,
                    topics=["hacker-news", query.lower()],
                    activation=0.18,
                    stability=0.68,
                )
            )
        return nodes
