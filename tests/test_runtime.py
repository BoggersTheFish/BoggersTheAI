from __future__ import annotations

from BoggersTheAI.interface.runtime import BoggersRuntime, RuntimeConfig


def test_runtime_creates_and_shuts_down():
    cfg = RuntimeConfig()
    cfg.wave = {"enabled": False}
    cfg.os_loop = {"enabled": False}
    cfg.tui = {"enabled": False}
    rt = BoggersRuntime(config=cfg)
    status = rt.get_status()
    assert "nodes" in status
    assert "edges" in status
    rt.shutdown()


def test_trigger_self_improvement():
    cfg = RuntimeConfig()
    cfg.wave = {"enabled": False}
    cfg.os_loop = {"enabled": False}
    cfg.tui = {"enabled": False}
    rt = BoggersRuntime(config=cfg)
    result = rt.trigger_self_improvement()
    assert isinstance(result, dict)
    rt.shutdown()
