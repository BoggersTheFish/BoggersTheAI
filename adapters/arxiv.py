from __future__ import annotations

import hashlib
import logging
import xml.etree.ElementTree as ET
from typing import List
from urllib.parse import urlencode

from ..core.types import Node
from ..shared.http import fetch_url

logger = logging.getLogger("boggers.adapters.arxiv")

_ARXIV_MAX_BYTES = 5_000_000


class ArXivAdapter:
    poll_interval = 0  # one-shot

    def ingest(self, source: str) -> List[Node]:
        query = source.strip()
        if not query:
            return []

        params = urlencode(
            {
                "search_query": f"all:{query}",
                "max_results": 5,
            }
        )
        url = f"https://export.arxiv.org/api/query?{params}"

        try:
            raw_xml = fetch_url(url)
            if len(raw_xml) > _ARXIV_MAX_BYTES:
                logger.warning("ArXiv payload size exceeds limit, rejecting.")
                return []
            root = ET.fromstring(raw_xml)
        except Exception as exc:
            logger.warning("ArXiv fetch failed for '%s': %s", query, exc)
            return []

        # XML namespace for Atom
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        nodes: List[Node] = []

        for entry in root.findall(".//atom:entry", ns):
            title = (
                (entry.findtext("atom:title", namespaces=ns) or "")
                .strip()
                .replace("\n", " ")
            )
            summary = (
                (entry.findtext("atom:summary", namespaces=ns) or "")
                .strip()
                .replace("\n", " ")
            )
            arxiv_id = (entry.findtext("atom:id", namespaces=ns) or "").strip()

            authors = [
                author.findtext("atom:name", namespaces=ns)
                for author in entry.findall("atom:author", ns)
                if author.findtext("atom:name", namespaces=ns)
            ]
            authors_str = ", ".join(authors)

            content = f"{title}. Authors: {authors_str}. Abstract: {summary}"
            if not content:
                continue

            digest = hashlib.sha1(
                f"arxiv:{arxiv_id or title}".encode("utf-8")
            ).hexdigest()[:12]

            nodes.append(
                Node(
                    id=f"arxiv:{digest}",
                    content=content,
                    topics=[query.lower(), "arxiv", "academic"],
                    activation=0.2,
                    stability=0.8,
                    attributes={
                        "arxiv_id": arxiv_id,
                        "ingest_source": "arxiv",
                        "authors": authors,
                    },
                )
            )
        return nodes
