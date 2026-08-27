"""Hash-chained episodic memory for PRIME M21."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path


ZERO_HASH = "0" * 64


def _canonical(
    payload: dict,
) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


@dataclass(frozen=True)
class EpisodeRecord:
    sequence: int
    context_id: str
    context_tokens: tuple[str, ...]
    verified_construction_ids: (
        tuple[str, ...]
    )
    reward_ppm: int
    tensions: tuple[str, ...]
    studies: tuple[str, ...]
    parent_hash: str
    episode_hash: str

    def payload_without_hash(
        self,
    ) -> dict:
        return {
            "sequence": self.sequence,
            "context_id": (
                self.context_id
            ),
            "context_tokens": list(
                self.context_tokens
            ),
            "verified_construction_ids": list(
                self.verified_construction_ids
            ),
            "reward_ppm": (
                self.reward_ppm
            ),
            "tensions": list(
                self.tensions
            ),
            "studies": list(
                self.studies
            ),
            "parent_hash": (
                self.parent_hash
            ),
        }


class EpisodicMemory:
    FORMAT = "prime-m21-episodic-memory-v1"

    def __init__(self) -> None:
        self.records: list[
            EpisodeRecord
        ] = []

    @property
    def head_hash(self) -> str:
        if not self.records:
            return ZERO_HASH

        return self.records[
            -1
        ].episode_hash

    def append(
        self,
        *,
        context_id: str,
        context_tokens: tuple[
            str,
            ...,
        ],
        verified_construction_ids: (
            tuple[str, ...]
        ),
        reward_ppm: int,
        tensions: tuple[
            str,
            ...,
        ] = (),
        studies: tuple[
            str,
            ...,
        ] = (),
    ) -> EpisodeRecord:
        payload = {
            "sequence": len(
                self.records
            ),
            "context_id": (
                context_id
            ),
            "context_tokens": list(
                context_tokens
            ),
            "verified_construction_ids": list(
                verified_construction_ids
            ),
            "reward_ppm": reward_ppm,
            "tensions": list(
                tensions
            ),
            "studies": list(
                studies
            ),
            "parent_hash": (
                self.head_hash
            ),
        }

        episode_hash = (
            hashlib.sha256(
                _canonical(
                    payload
                )
            ).hexdigest()
        )

        record = EpisodeRecord(
            sequence=payload[
                "sequence"
            ],
            context_id=context_id,
            context_tokens=(
                context_tokens
            ),
            verified_construction_ids=(
                verified_construction_ids
            ),
            reward_ppm=reward_ppm,
            tensions=tensions,
            studies=studies,
            parent_hash=payload[
                "parent_hash"
            ],
            episode_hash=(
                episode_hash
            ),
        )

        self.records.append(
            record
        )

        return record

    def verify_chain(self) -> bool:
        parent = ZERO_HASH

        for index, record in (
            enumerate(
                self.records
            )
        ):
            if (
                record.sequence
                != index
            ):
                return False

            if (
                record.parent_hash
                != parent
            ):
                return False

            expected = (
                hashlib.sha256(
                    _canonical(
                        record.payload_without_hash()
                    )
                ).hexdigest()
            )

            if (
                expected
                != record.episode_hash
            ):
                return False

            parent = (
                record.episode_hash
            )

        return True

    def save(
        self,
        path: str | Path,
    ) -> None:
        payload = {
            "format": self.FORMAT,
            "records": [
                {
                    **record.payload_without_hash(),
                    "episode_hash": (
                        record.episode_hash
                    ),
                }
                for record in self.records
            ],
        }

        Path(path).write_text(
            json.dumps(
                payload,
                sort_keys=True,
                indent=2,
            )
            + "\n"
        )
