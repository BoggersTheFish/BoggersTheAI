from __future__ import annotations

import hashlib
import logging
import xml.etree.ElementTree as ET
from typing import List
from urllib.request import urlopen

from ..core.types import Node

logger = logging.getLogger("boggers.adapters.rss")


class RSSAdapter:
    poll_interval = 3600

    def ingest(self, source: str) -> List[Node]:
        feed_url = source.strip()
        if not feed_url:
            return []

        try:
            with urlopen(feed_url, timeout=10) as response:
                raw_xml = response.read()
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
            content = " ".join([segment for segment in [title, summary] if segment]).strip()
            if not content:
                continue
            digest = hashlib.sha1(f"rss:{link or title}".encode("utf-8")).hexdigest()[:12]
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
            content = " ".join([segment for segment in [title, summary] if segment]).strip()
            if not content:
                continue
            digest = hashlib.sha1(f"atom:{title}:{summary}".encode("utf-8")).hexdigest()[:12]
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
