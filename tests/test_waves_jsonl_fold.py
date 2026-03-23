from __future__ import annotations

import json
from pathlib import Path

from BoggersTheAI.core.graph.universal_living_graph import UniversalLivingGraph


def test_ingest_waves_jsonl_creates_nodes(tmp_path: Path) -> None:
    trace_dir = tmp_path / "meta"
    trace_dir.mkdir()
    log = trace_dir / "waves.jsonl"
    log.write_text(
        json.dumps(
            {"kind": "wave_cycle", "timestamp": "t1", "event": {"cycle": 1}}
        )
        + "\n"
        + json.dumps({"kind": "next_grok_prompt", "prompt_text": "x"})
        + "\n",
        encoding="utf-8",
    )

    graph = UniversalLivingGraph(auto_load=False)
    r = graph.ingest_waves_jsonl(log)
    assert r.get("skipped") is False
    assert int(r.get("ingested", 0)) >= 1
    assert any(n.startswith("meta:") for n in graph.nodes)
