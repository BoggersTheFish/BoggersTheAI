from __future__ import annotations

from BoggersTheAI.core.fine_tuner import FineTuningConfig, UnslothFineTuner


def test_fine_tuner_disabled():
    FineTuningConfig(enabled=False)

    class FakeConfig:
        inference = {"self_improvement": {"fine_tuning": {"enabled": False}}}

    tuner = UnslothFineTuner(config=FakeConfig())
    result = tuner.fine_tune()
    assert result["success"] is False
    assert result.get("reason") == "fine_tuning_disabled"


def test_fine_tuner_cpu_distillora_track():
    class FakeConfig:
        inference = {
            "self_improvement": {
                "fine_tuning": {"enabled": True, "track": "cpu_distillora"},
            }
        }

    tuner = UnslothFineTuner(config=FakeConfig())
    result = tuner.fine_tune()
    assert result.get("track") == "cpu_distillora"
    assert result.get("reason") == "cpu_distillora_completed"
    assert result.get("success") is True


def test_fine_tuner_missing_dataset():
    FineTuningConfig(enabled=True, safety_dry_run=False, train_path="nonexistent.jsonl")

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
