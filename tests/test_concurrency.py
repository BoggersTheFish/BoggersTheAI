from __future__ import annotations

import sys
import threading
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from BoggersTheAI.core.graph.universal_living_graph import (  # noqa: E402
    UniversalLivingGraph,
)
from BoggersTheAI.core.mode_manager import Mode, ModeManager  # noqa: E402


class TestModeManager:
    def test_initial_mode_is_auto(self):
        mm = ModeManager()
        assert mm.get_mode() == Mode.AUTO

    def test_request_user_mode(self):
        mm = ModeManager()
        result = mm.request_user_mode(timeout=5.0)
        assert result is True
        assert mm.get_mode() == Mode.USER

    def test_release_to_auto(self):
        mm = ModeManager()
        mm.request_user_mode(timeout=5.0)
        mm.release_to_auto()
        assert mm.get_mode() == Mode.AUTO

    def test_begin_end_cycle(self):
        mm = ModeManager()
        assert mm.begin_cycle() is True
        assert mm.begin_cycle() is False
        mm.end_cycle()
        assert mm.begin_cycle() is True
        mm.end_cycle()

    def test_timeout_returns_false(self):
        mm = ModeManager()
        assert mm.begin_cycle() is True

        result_holder = [None]

        def request_with_timeout():
            result_holder[0] = mm.request_user_mode(timeout=0.1)

        t = threading.Thread(target=request_with_timeout)
        t.start()
        t.join(timeout=2.0)
        mm.end_cycle()
        assert result_holder[0] is False


class TestConcurrentGraphAccess:
    def test_concurrent_add_nodes(self):
        graph = UniversalLivingGraph(auto_load=False)
        errors = []

        def add_nodes(prefix, count):
            try:
                for i in range(count):
                    graph.add_node(
                        f"{prefix}_{i}",
                        f"Content {prefix}_{i}",
                        topics=["test"],
                    )
            except Exception as exc:
                errors.append(exc)

        threads = [
            threading.Thread(target=add_nodes, args=(f"t{t}", 20)) for t in range(5)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert len(graph.nodes) == 100

    def test_concurrent_read_write(self):
        graph = UniversalLivingGraph(auto_load=False)
        for i in range(10):
            graph.add_node(f"n{i}", f"Node {i}", topics=["t"], activation=0.5)
        for i in range(9):
            graph.add_edge(f"n{i}", f"n{i+1}", weight=0.5)

        errors = []
        stop = threading.Event()

        def reader():
            try:
                while not stop.is_set():
                    graph.snapshot_read()
                    graph.get_metrics()
                    graph.strongest_node()
            except Exception as exc:
                errors.append(exc)

        def writer():
            try:
                for i in range(20):
                    graph.update_activation(f"n{i % 10}", 0.01)
                    graph.propagate()
            except Exception as exc:
                errors.append(exc)

        readers = [threading.Thread(target=reader) for _ in range(3)]
        writer_thread = threading.Thread(target=writer)
        for r in readers:
            r.start()
        writer_thread.start()
        writer_thread.join()
        stop.set()
        for r in readers:
            r.join(timeout=2.0)

        assert not errors
