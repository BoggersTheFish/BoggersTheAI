from __future__ import annotations

import hashlib
import logging
import xml.etree.ElementTree as ET
from typing import List

from ..core.types import Node
from .http_client import fetch_url

try:
    from defusedxml import ElementTree as SafeET
except ImportError:
    SafeET = None  # type: ignore[misc, assignment]

logger = logging.getLogger("boggers.adapters.rss")

_RSS_XML_MAX_BYTES = 5_000_000


class RSSAdapter:
    poll_interval = 3600

    def ingest(self, source: str) -> List[Node]:
        feed_url = source.strip()
        if not feed_url:
            return []
        if not feed_url.startswith("https://"):
            logger.warning("Rejecting non-HTTPS RSS URL: %s", feed_url[:80])
            return []

        try:
            raw_xml = fetch_url(feed_url)
            if len(raw_xml) > _RSS_XML_MAX_BYTES:
                logger.warning(
                    "RSS XML exceeds max size (%d bytes), rejecting feed",
                    len(raw_xml),
                )
                return []
            if SafeET is not None:
                root = SafeET.fromstring(raw_xml)
            else:
                root = ET.fromstring(raw_xml)
        except Exception as exc:
            logger.warning("RSS fetch failed for '%s': %s", feed_url, exc)
            return []

        nodes: List[Node] = []
        # RSS 2.0
        for item in root.findall(".//item"):
            title = (item.findtext("title") or "").strip()
            summary = (item.findtext("description") or "").strip()
            link = (item.findtext("link") or "").strip()
            content = " ".join(
                [segment for segment in [title, summary] if segment]
            ).strip()
            if not content:
                continue
            digest = hashlib.sha1(f"rss:{link or title}".encode("utf-8")).hexdigest()[
                :12
            ]
            nodes.append(
                Node(
                    id=f"rss:{digest}",
                    content=content,
                    topics=["rss", title.lower()[:40]],
                    activation=0.15,
                    stability=0.65,
                )
            )

        # Atom fallback
        atom_entries = root.findall(".//{http://www.w3.org/2005/Atom}entry")
        for entry in atom_entries:
            title = (entry.findtext("{http://www.w3.org/2005/Atom}title") or "").strip()
            summary = (
                entry.findtext("{http://www.w3.org/2005/Atom}summary") or ""
            ).strip()
            content = " ".join(
                [segment for segment in [title, summary] if segment]
            ).strip()
            if not content:
                continue
            digest = hashlib.sha1(
                f"atom:{title}:{summary}".encode("utf-8")
            ).hexdigest()[:12]
            nodes.append(
                Node(
                    id=f"rss:{digest}",
                    content=content,
                    topics=["rss", "atom", title.lower()[:40]],
                    activation=0.15,
                    stability=0.65,
                )
            )

        return nodes
