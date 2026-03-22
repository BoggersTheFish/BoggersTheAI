from __future__ import annotations

import re
from dataclasses import dataclass

from ...entities.synthesis_engine import BoggersSynthesisConfig, BoggersSynthesisEngine

_HEADER_RE = re.compile(
    r"^\[node:([^\]]+)\]\s*topic=(.+?)\s+activation=([\d.]+)\s+stability=([\d.]+)\s*$"
)
_TOKEN_RE = re.compile(r"[a-z0-9_]{2,}", re.I)


@dataclass(slots=True)
class GraphOnlySynthesizer:
    """
    Pure graph-native synthesis: parses activated subgraph context, ranks nodes by
    query relevance × activation × stability, emits a grounded answer. No LLM/Ollama.
    Optional legacy extractive engine only when ``pure_graph`` is False.
    Implements ``NodeSynthesizer`` structurally (see ``core/synthesis_protocols``).
    """

    pure_graph: bool = True
    max_excerpt_chars: int = 420
    max_bullets: int = 5
    engine: BoggersSynthesisEngine | None = None

    def __post_init__(self) -> None:
        if not self.pure_graph and self.engine is None:
            self.engine = BoggersSynthesisEngine()

    @classmethod
    def with_config(
        cls, config: BoggersSynthesisConfig | None
    ) -> GraphOnlySynthesizer:
        return cls(
            pure_graph=False,
            engine=BoggersSynthesisEngine(config=config or BoggersSynthesisConfig()),
        )

    @classmethod
    def from_synthesis_options(cls, graph_only: dict | None) -> GraphOnlySynthesizer:
        """Build from ``inference.synthesis.graph_only`` mapping."""
        if not isinstance(graph_only, dict):
            return cls()
        pure = bool(graph_only.get("pure_graph", True))
        max_ex = int(graph_only.get("max_excerpt_chars", 420))
        bullets = int(graph_only.get("max_bullets", 5))
        if not pure:
            bc = BoggersSynthesisConfig(
                max_context_chars=int(graph_only.get("max_context_chars", 8000)),
                max_sentences=int(graph_only.get("max_sentences", 4)),
            )
            return cls(
                pure_graph=False,
                max_excerpt_chars=max_ex,
                max_bullets=bullets,
                engine=BoggersSynthesisEngine(config=bc),
            )
        return cls(
            pure_graph=True,
            max_excerpt_chars=max_ex,
            max_bullets=bullets,
        )

    def synthesize(self, context: str, query: str) -> str:
        if not self.pure_graph and self.engine is not None:
            return self.engine.synthesize(context, query)
        return self._synthesize_pure(context, query)

    def _synthesize_pure(self, context: str, query: str) -> str:
        blocks = self._parse_blocks(context)
        if not blocks:
            return (
                "I do not have enough retrieved context to answer this yet. "
                "Please ingest more data for this topic."
            )
        q_tokens = self._tokens(query)
        ranked = sorted(
            blocks,
            key=lambda b: self._score_block(q_tokens, b),
            reverse=True,
        )
        lines: list[str] = [
            "## Graph-native synthesis (TS)",
            f"**Query:** {query.strip()}",
            "",
            "**Grounded in retrieved nodes (no LLM):**",
        ]
        for idx, b in enumerate(ranked[: self.max_bullets], start=1):
            excerpt = b["content"].strip().replace("\n", " ")
            if len(excerpt) > self.max_excerpt_chars:
                excerpt = excerpt[: self.max_excerpt_chars] + "…"
            score = self._score_block(q_tokens, b)
            topics = ",".join(b["topics"][:4])
            lines.append(
                f"{idx}. `[{b['node_id']}]` ({topics}) "
                f"act={b['activation']:.2f} stab={b['stability']:.2f} "
                f"score={score:.2f} — {excerpt}"
            )
        lines.append("")
        lines.append(
            "_Constraint: answer assembled only from graph nodes; "
            "LLM is optional fallback in pipeline._"
        )
        return "\n".join(lines)

    def _parse_blocks(self, context: str) -> list[dict[str, object]]:
        blocks: list[dict[str, object]] = []
        lines = context.splitlines()
        i = 0
        while i < len(lines):
            raw = lines[i].strip()
            m = _HEADER_RE.match(raw)
            if m:
                nid, topics_s, act_s, stab_s = m.groups()
                i += 1
                body: list[str] = []
                while i < len(lines) and not lines[i].strip().startswith("[node:"):
                    body.append(lines[i])
                    i += 1
                content = "\n".join(body).strip()
                topics = [t.strip() for t in topics_s.split(",") if t.strip()]
                blocks.append(
                    {
                        "node_id": nid.strip(),
                        "topics": topics,
                        "activation": float(act_s),
                        "stability": float(stab_s),
                        "content": content,
                    }
                )
                continue
            i += 1
        return blocks

    def _tokens(self, text: str) -> list[str]:
        return [t.lower() for t in _TOKEN_RE.findall(text.lower())]

    def _score_block(self, q_tokens: list[str], block: dict[str, object]) -> float:
        if not q_tokens:
            return (
                float(block["activation"]) * 0.5 + float(block["stability"]) * 0.5
            )
        blob = (
            str(block["content"]).lower()
            + " "
            + " ".join(str(t).lower() for t in block["topics"])
        )
        hits = sum(1 for t in q_tokens if t in blob)
        overlap = hits / max(len(q_tokens), 1)
        return (
            overlap * 0.45
            + float(block["activation"]) * 0.30
            + float(block["stability"]) * 0.25
        )
