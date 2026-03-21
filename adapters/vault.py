from __future__ import annotations

import os

from .markdown import MarkdownAdapter


class VaultAdapter:
    # Watches/syncs local markdown vaults on an interval.
    poll_interval = 300

    def __init__(self, config: dict | None = None) -> None:
        cfg = config or {}
        runtime = cfg.get("runtime")
        if not isinstance(runtime, dict):
            runtime = {}
        self._vault_root = str(runtime.get("insight_vault_path", "./vault"))
        self._markdown = MarkdownAdapter(base_dir=self._vault_root)

    def ingest(self, source: str):
        if os.path.isabs(source):
            path = self._vault_root
        else:
            path = os.path.join(self._vault_root, source)
        return self._markdown.ingest(path)
