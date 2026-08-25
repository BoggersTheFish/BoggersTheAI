from core.cortex.counterfactual_verifier import (
    PAIR_CHANNELS,
    build_counterfactual_pair,
)

from core.cortex.verifier_prompt import (
    format_verifier_prompt,
)


def test_counterfactual_pairs_are_canonical():
    for offset, channel in enumerate(
        PAIR_CHANNELS
    ):
        pair = build_counterfactual_pair(
            channel,
            910000 + offset,
            split="test",
        )

        assert len(pair) == 2

        accept, reject = pair

        assert (
            accept["verifier_label"]
            == "ACCEPT"
        )

        assert (
            reject["verifier_label"]
            == "REJECT"
        )

        assert (
            accept["verifier_result"][
                "outcome"
            ]
            == "pass"
        )

        assert (
            reject["verifier_result"][
                "outcome"
            ]
            == "fail"
        )

        assert (
            accept["pair_id"]
            == reject["pair_id"]
        )

        assert (
            accept["pair_hash"]
            == reject["pair_hash"]
        )

        assert (
            accept["verifier_type"]
            == reject["verifier_type"]
            == channel
        )

        assert (
            accept["authority"]
            == "NONE"
        )

        assert (
            reject["authority"]
            == "NONE"
        )


def test_counterfactual_prompts_differ_only_by_available_fact():
    for offset, channel in enumerate(
        PAIR_CHANNELS
    ):
        pair = build_counterfactual_pair(
            channel,
            920000 + offset,
            split="test",
        )

        accept_prompt = (
            format_verifier_prompt(
                pair[0]
            )
        )

        reject_prompt = (
            format_verifier_prompt(
                pair[1]
            )
        )

        assert (
            accept_prompt
            != reject_prompt
        )

        assert (
            pair[0]["obligation"]
            == pair[1]["obligation"]
            or channel == "arithmetic"
        )


def test_pair_counterfactual_metadata_changes():
    for offset, channel in enumerate(
        PAIR_CHANNELS
    ):
        accept, reject = (
            build_counterfactual_pair(
                channel,
                930000 + offset,
                split="test",
            )
        )

        assert (
            accept[
                "counterfactual_field"
            ]
            == reject[
                "counterfactual_field"
            ]
        )

        assert (
            accept[
                "counterfactual_value"
            ]
            != reject[
                "counterfactual_value"
            ]
        )
