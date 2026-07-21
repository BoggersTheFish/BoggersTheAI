from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Node(BaseModel):
    """A concept, claim, memory, symbol, or state in a CIG graph."""

    model_config = ConfigDict(extra="allow", validate_assignment=True)

    id: str
    label: str
    activation: float = 0.0
    stability: float = Field(default=1.0, gt=0.0)
    metadata: dict = Field(default_factory=dict)

    @field_validator("activation")
    @classmethod
    def clamp_activation(cls, value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    @property
    def display_label(self) -> str:
        return self.label
