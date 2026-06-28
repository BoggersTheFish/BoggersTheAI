from __future__ import annotations

import hashlib
import logging
from typing import List
from urllib.parse import urlencode

from ..core.types import Node
from ..shared.http import fetch_json

logger = logging.getLogger("boggers.adapters.semantic_scholar")


class SemanticScholarAdapter:
    poll_interval = 0  # one-shot

    def ingest(self, source: str) -> List[Node]:
        query = source.strip()
        if not query:
            return []

        params = urlencode(
            {
                "query": query,
                "limit": 5,
                "fields": "title,abstract,authors,url,citationCount",
            }
        )
        url = f"https://api.semanticscholar.org/graph/v1/paper/search?{params}"

        try:
            payload = fetch_json(url)
        except Exception as exc:
            logger.warning("Semantic Scholar fetch failed for '%s': %s", query, exc)
            return []

        data = payload.get("data", [])
        nodes: List[Node] = []

        for paper in data:
            paper_id = paper.get("paperId") or ""
            title = (paper.get("title") or "").strip()
            abstract = (paper.get("abstract") or "").strip()
            citation_count = paper.get("citationCount", 0)

            authors_list = paper.get("authors", [])
            authors = [
                a.get("name")
                for a in authors_list
                if isinstance(a, dict) and a.get("name")
            ]
            authors_str = ", ".join(authors)

            content = f"{title}. Authors: {authors_str}. Citations: {citation_count}. Abstract: {abstract}"
            if not title:
                continue

            digest = hashlib.sha1(
                f"sem:{paper_id or title}".encode("utf-8")
            ).hexdigest()[:12]

            nodes.append(
                Node(
                    id=f"sem:{digest}",
                    content=content,
                    topics=[query.lower(), "semantic_scholar", "academic"],
                    activation=0.2,
                    stability=0.8,
                    attributes={
                        "paper_id": paper_id,
                        "ingest_source": "semantic_scholar",
                        "citations": citation_count,
                        "url": paper.get("url"),
                        "authors": authors,
                    },
                )
            )
        return nodes
