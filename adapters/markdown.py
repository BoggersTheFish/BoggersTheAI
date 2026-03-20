from __future__ import annotations

import hashlib
from pathlib import Path
from typing import List

from ..core.types import Node


class MarkdownAdapter:
    poll_interval = 0

    def ingest(self, source: str) -> List[Node]:
        path = Path(source)
        if not path.exists():
            return []

        files = [path] if path.is_file() else list(path.rglob("*.md"))
        nodes: List[Node] = []
        for file_path in files:
            try:
                text = file_path.read_text(encoding="utf-8")
            except OSError:
                continue
            nodes.extend(self._nodes_from_markdown(file_path, text))
        return nodes

    def _nodes_from_markdown(self, file_path: Path, text: str) -> List[Node]:
        sections: List[tuple[str, List[str]]] = []
        current_title = file_path.stem
        current_lines: List[str] = []

        for raw_line in text.splitlines():
            line = raw_line.rstrip()
            if line.startswith("#"):
                if current_lines:
                    sections.append((current_title, current_lines))
                current_title = line.lstrip("#").strip() or current_title
                current_lines = []
            else:
                current_lines.append(line)

        if current_lines:
            sections.append((current_title, current_lines))

        nodes: List[Node] = []
        for title, lines in sections:
            content = "\n".join(line for line in lines if line.strip()).strip()
            if not content:
                continue
            digest = hashlib.sha1(
                f"md:{file_path.as_posix()}:{title}:{content[:64]}".encode("utf-8")
            ).hexdigest()[:12]
            nodes.append(
                Node(
                    id=f"md:{digest}",
                    content=content,
                    topics=["markdown", file_path.stem.lower(), title.lower()[:50]],
                    activation=0.12,
                    stability=0.75,
                )
            )
        return nodes
