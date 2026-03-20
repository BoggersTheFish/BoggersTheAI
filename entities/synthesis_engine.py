from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class BoggersSynthesisConfig:
    max_context_chars: int = 8000
    max_sentences: int = 4


class BoggersSynthesisEngine:
    """
    Single-purpose synthesis engine.

    Contract:
        synthesize(context: str, query: str) -> str
    """

    def __init__(self, config: BoggersSynthesisConfig | None = None) -> None:
        self.config = config or BoggersSynthesisConfig()

    def synthesize(self, context: str, query: str) -> str:
        normalized_context = (context or "").strip()
        if not normalized_context:
            return (
                "I do not have enough retrieved context to answer this yet. "
                "Please ingest more data for this topic."
            )

        clipped_context = normalized_context[: self.config.max_context_chars]
        lines = [line.strip() for line in clipped_context.splitlines() if line.strip()]
        if not lines:
            return (
                "I do not have enough retrieved context to answer this yet. "
                "Please ingest more data for this topic."
            )

        # Extractive synthesis keeps answers grounded in supplied context.
        selected = lines[: self.config.max_sentences]
        joined = " ".join(selected)
        return (
            f"Grounded synthesis for '{query}': {joined}\n"
            "Source: retrieved graph context only."
        )
