from __future__ import annotations

from dataclasses import dataclass

from ...entities.synthesis_engine import BoggersSynthesisConfig, BoggersSynthesisEngine


@dataclass(slots=True)
class GraphOnlySynthesizer:
    """Graph-grounded extractive synthesis (NodeSynthesizer); LLM is optional."""

    engine: BoggersSynthesisEngine | None = None

    def __post_init__(self) -> None:
        if self.engine is None:
            self.engine = BoggersSynthesisEngine()

    def synthesize(self, context: str, query: str) -> str:
        return self.engine.synthesize(context, query)

    @classmethod
    def with_config(
        cls, config: BoggersSynthesisConfig | None
    ) -> GraphOnlySynthesizer:
        cfg = config or BoggersSynthesisConfig()
        return cls(engine=BoggersSynthesisEngine(config=cfg))
