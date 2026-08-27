from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Edge(BaseModel):
    """A weighted relation or constraint between two CIG nodes."""

    model_config = ConfigDict(extra="allow")

    source: str
    target: str
    relation: str
    weight: float = Field(default=1.0, ge=0.0)
    polarity: float = Field(default=1.0, ge=-1.0, le=1.0)
    expected_ratio: float = 1.0
    metadata: dict = Field(default_factory=dict)
