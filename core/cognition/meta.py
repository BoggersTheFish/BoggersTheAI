"""Meta-learning ledger for PRIME M21."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProposalSourceStats:
    attempts: int = 0
    accepted: int = 0
    rejected: int = 0
    cumulative_gain_ppm: int = 0

    @property
    def priority(self) -> int:
        return (
            100
            * self.accepted
            - 120
            * self.rejected
            + (
                self.cumulative_gain_ppm
                // 10_000
            )
        )


class MetaLearningLedger:
    def __init__(self) -> None:
        self.sources: dict[
            str,
            ProposalSourceStats,
        ] = {}

    def record(
        self,
        source: str,
        *,
        accepted: bool,
        gain_ppm: int,
    ) -> None:
        stats = (
            self.sources.setdefault(
                source,
                ProposalSourceStats(),
            )
        )

        stats.attempts += 1

        if accepted:
            stats.accepted += 1
        else:
            stats.rejected += 1

        stats.cumulative_gain_ppm += (
            gain_ppm
        )

    def priority(
        self,
        source: str,
    ) -> int:
        stats = self.sources.get(
            source
        )

        if stats is None:
            return 0

        return stats.priority
