from __future__ import annotations

import hashlib
import json
from typing import List
from urllib.parse import urlencode
from urllib.request import urlopen

from ..core.types import Node


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

        with urlopen(url, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))

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
