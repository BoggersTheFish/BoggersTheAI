from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List

logger = logging.getLogger("boggers.insight")


@dataclass(slots=True)
class InsightResult:
    path: str
    hypotheses: List[str]


class InsightEngine:
    def write_insight(
        self,
        content: str,
        topics: List[str],
        source_nodes: List[str],
        vault_path: str,
    ) -> str:
        base = Path(vault_path)
        base.mkdir(parents=True, exist_ok=True)
        slug = self._slugify(" ".join(topics[:4]) or "insight")
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        filename = f"{timestamp}-{slug}.md"
        file_path = base / filename

        created = datetime.now(timezone.utc).isoformat()
        frontmatter = [
            "---",
            f"topics: {topics}",
            f"source_nodes: {source_nodes}",
            f"created: {created}",
            "---",
            "",
        ]
        body = content.strip() or "No content."
        file_path.write_text("\n".join(frontmatter) + body + "\n", encoding="utf-8")
        return str(file_path)

    def extract_hypotheses(
        self, content: str, topics: Iterable[str], limit: int = 5
    ) -> List[str]:
        seeds = list(
            dict.fromkeys([topic.strip().lower() for topic in topics if topic])
        )
        tokens = [tok.strip(".,:;!?()[]{}").lower() for tok in content.split()]
        candidates = [tok for tok in tokens if len(tok) > 5 and tok.isascii()]

        hypotheses: List[str] = []
        for seed in seeds:
            if seed:
                hypotheses.append(f"explore:{seed}")
            if len(hypotheses) >= limit:
                return hypotheses[:limit]

        for token in candidates:
            if token not in seeds and f"explore:{token}" not in hypotheses:
                hypotheses.append(f"explore:{token}")
            if len(hypotheses) >= limit:
                break
        return hypotheses[:limit]

    def write_and_extract(
        self,
        content: str,
        topics: List[str],
        source_nodes: List[str],
        vault_path: str,
    ) -> InsightResult:
        path = self.write_insight(
            content=content,
            topics=topics,
            source_nodes=source_nodes,
            vault_path=vault_path,
        )
        hypotheses = self.extract_hypotheses(content=content, topics=topics)
        return InsightResult(path=path, hypotheses=hypotheses)

    def _slugify(self, text: str) -> str:
        lowered = text.lower().strip()
        chars = []
        for char in lowered:
            if char.isalnum():
                chars.append(char)
            elif char in {" ", "-", "_"}:
                chars.append("-")
        slug = "".join(chars)
        while "--" in slug:
            slug = slug.replace("--", "-")
        slug = slug.strip("-")
        return slug[:60] or "insight"
