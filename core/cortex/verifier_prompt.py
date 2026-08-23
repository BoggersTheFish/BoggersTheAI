"""Canonical neural prompt for predicting PRIME verifier behaviour."""

from __future__ import annotations


def format_verifier_prompt(
    record: dict,
) -> str:
    verifier_type = str(
        record.get(
            "verifier_type",
            "unknown",
        )
    )

    premises = "\n".join(
        str(value)
        for value
        in record.get(
            "premises",
            [],
        )
    )

    obligation = str(
        record.get(
            "obligation",
            "",
        )
    )

    return (
        "PRIME VERIFIER PREDICTION\n"
        f"CHANNEL: {verifier_type}\n"
        "PREMISES:\n"
        f"{premises}\n"
        "OBLIGATION:\n"
        f"{obligation}\n"
        "VERDICT:\n"
    )
