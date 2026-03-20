from __future__ import annotations

from .markdown import MarkdownAdapter


class VaultAdapter:
    # Watches/syncs local markdown vaults on an interval.
    poll_interval = 300

    def __init__(self) -> None:
        self._markdown = MarkdownAdapter()

    def ingest(self, source: str):
        return self._markdown.ingest(source)
