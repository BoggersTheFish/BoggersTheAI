from __future__ import annotations

from BoggersTheAI.core.fine_tuner import UnslothFineTuner, FineTuningConfig


def test_fine_tuner_disabled():
    cfg = FineTuningConfig(enabled=False)

    class FakeConfig:
        inference = {"self_improvement": {"fine_tuning": {"enabled": False}}}

    tuner = UnslothFineTuner(config=FakeConfig())
    result = tuner.fine_tune()
    assert result["success"] is False
    assert result.get("reason") == "fine_tuning_disabled"


def test_fine_tuner_missing_dataset():
    cfg = FineTuningConfig(enabled=True, safety_dry_run=False, train_path="nonexistent.jsonl")

    class FakeConfig:
        inference = {
            "self_improvement": {
                "fine_tuning": {"enabled": True, "safety_dry_run": False},
                "dataset_build": {"output_dir": "nonexistent_dir_xyz"},
            }
        }

    tuner = UnslothFineTuner(config=FakeConfig())
    result = tuner.fine_tune()
    assert result["success"] is False
