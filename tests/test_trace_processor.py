from __future__ import annotations

import tempfile
from pathlib import Path

from BoggersTheAI.core.trace_processor import TraceProcessor


def test_build_dataset_with_no_traces():
    with tempfile.TemporaryDirectory() as tmpdir:
        traces = Path(tmpdir) / "traces"
        traces.mkdir()
        dataset = Path(tmpdir) / "dataset"

        class FakeConfig:
            inference = {
                "self_improvement": {
                    "traces_dir": str(traces),
                    "dataset_build": {
                        "min_confidence": 0.5,
                        "max_samples": 100,
                        "output_dir": str(dataset),
                        "split_ratio": 0.8,
                    },
                }
            }

        processor = TraceProcessor(config=FakeConfig())
        result = processor.build_dataset()
        assert result["samples_built"] == 0
