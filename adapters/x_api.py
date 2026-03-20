from __future__ import annotations

import json
import logging
import os
import urllib.parse
import urllib.request
from typing import List

from ..core.types import Node

logger = logging.getLogger("boggers.adapters.x_api")


class XApiAdapter:
    poll_interval = 60

    def __init__(self, bearer_token: str | None = None) -> None:
        self.bearer_token = bearer_token or os.environ.get("X_BEARER_TOKEN", "")

    def ingest(self, source: str) -> List[Node]:
        topic = source.strip()
        if not self.bearer_token:
            logger.info("X API bearer token not configured; skipping")
            return []
        url = (
            "https://api.x.com/2/tweets/search/recent"
            f"?query={urllib.parse.quote(topic)}&max_results=10"
        )
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {self.bearer_token}"},
        )
        try:
            response = urllib.request.urlopen(req, timeout=10)
            data = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            logger.warning("X API fetch failed for '%s': %s", topic, exc)
            return []
        nodes: List[Node] = []
        for tweet in data.get("data", []):
            text = tweet.get("text", "").strip()
            if not text:
                continue
            nodes.append(
                Node(
                    id=f"x:{tweet.get('id', '')}",
                    content=text,
                    topics=[topic, "x_api"],
                    activation=0.2,
                    stability=0.6,
                )
            )
        return nodes
