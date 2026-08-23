"""Native cognition telemetry for Mega PRIME."""

from __future__ import annotations

from dataclasses import (
    asdict,
    dataclass,
)
import json


@dataclass(frozen=True)
class LayerObservation:
    layer: int

    recurrent_state_norm: float

    read_norm: float

    erase_mean: float

    write_mean: float

    selected_expert: int

    expert_probability: float


@dataclass(frozen=True)
class TSObs:
    sequence: int

    model_id: str

    token_id: int

    token_label: str

    authority: str

    verifier_prediction: int

    verifier_confidence: float

    top_output_tokens: tuple[
        tuple[int, float],
        ...,
    ]

    layers: tuple[
        LayerObservation,
        ...,
    ]

    def to_dict(
        self,
    ) -> dict:
        return asdict(
            self
        )

    def to_json(
        self,
    ) -> str:
        return json.dumps(
            self.to_dict(),
            sort_keys=True,
        )


def append_jsonl(
    path,
    observation: TSObs,
) -> None:
    with open(
        path,
        "a",
        encoding="utf-8",
    ) as handle:
        handle.write(
            observation.to_json()
        )

        handle.write(
            "\n"
        )
