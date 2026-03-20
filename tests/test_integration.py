from __future__ import annotations

from BoggersTheAI.interface.runtime import BoggersRuntime, RuntimeConfig


def test_full_ask_cycle():
    cfg = RuntimeConfig()
    cfg.wave = {"enabled": False}
    cfg.os_loop = {"enabled": False}
    cfg.tui = {"enabled": False}
    cfg.inference = {
        "ollama": {"enabled": False},
        "synthesis": {"use_graph_subgraph": True, "top_k_nodes": 3},
        "self_improvement": {
            "trace_logging_enabled": False,
            "traces_dir": "traces",
            "dataset_build": {"output_dir": "dataset"},
            "fine_tuning": {"enabled": False, "safety_dry_run": True},
        },
    }
    rt = BoggersRuntime(config=cfg)
    response = rt.ask("What is TS-OS?")
    assert response.answer
    assert isinstance(response.topics, list)
    status = rt.get_status()
    assert "nodes" in status
    rt.shutdown()
