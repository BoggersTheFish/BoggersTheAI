from __future__ import annotations

import sys
import time
from pathlib import Path
from unittest.mock import MagicMock

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from BoggersTheAI.core.graph.wave_runner import (  # noqa: E402
    WaveConfig,
    WaveCycleRunner,
)


def test_wave_config_defaults():
    cfg = WaveConfig()
    assert cfg.mode == "tension"
    assert cfg.interval_seconds == 30.0
    assert cfg.tension_fire_threshold == 0.7
    assert cfg.idle_heartbeat_seconds is None
    assert cfg.log_each_cycle is True
    assert cfg.auto_save is True
    assert cfg.incremental_save_interval == 5


def test_wave_config_custom():
    cfg = WaveConfig(
        interval_seconds=10.0,
        log_each_cycle=False,
    )
    assert cfg.interval_seconds == 10.0
    assert cfg.log_each_cycle is False


def _make_mock_graph():
    graph = MagicMock()
    graph.nodes = {}
    graph.edges = []
    graph._last_tension = 0.0
    graph._cycles_this_hour = 0
    graph._check_guardrails.return_value = None
    graph.elect_strongest.return_value = None
    graph.propagate.return_value = None
    graph.relax.return_value = None
    graph.prune.return_value = 0
    graph._evolve_fn = None
    graph._apply_graph_node_updates.return_value = None
    graph._sync_edges_from_tuples.return_value = None
    graph.save_incremental.return_value = None
    return graph


def test_start_stop():
    graph = _make_mock_graph()
    cfg = WaveConfig(interval_seconds=60.0)
    runner = WaveCycleRunner(graph, cfg)
    runner.start()
    assert runner.is_alive
    runner.stop()
    time.sleep(0.1)
    assert not runner.is_alive


def test_run_single_cycle_returns_dict():
    graph = _make_mock_graph()
    cfg = WaveConfig(auto_save=False)
    runner = WaveCycleRunner(graph, cfg)
    result = runner.run_single_cycle()
    assert isinstance(result, dict)
    assert "cycle" in result
    assert result["cycle"] == 1
    assert "tension" in result


def test_run_single_cycle_skipped_on_guardrail():
    graph = _make_mock_graph()
    graph._check_guardrails.return_value = "too many nodes"
    cfg = WaveConfig(auto_save=False)
    runner = WaveCycleRunner(graph, cfg)
    result = runner.run_single_cycle()
    assert "skipped" in result
