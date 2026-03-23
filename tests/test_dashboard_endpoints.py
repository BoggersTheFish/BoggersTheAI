from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

try:
    from fastapi.testclient import TestClient

    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False


@pytest.mark.skipif(not HAS_FASTAPI, reason="fastapi not installed")
class TestDashboardEndpoints:
    @pytest.fixture(autouse=True)
    def setup_client(self):
        mock_rt = MagicMock()
        mock_rt.get_status.return_value = {
            "cycle_count": 5,
            "thread_alive": True,
            "nodes": 10,
            "edges": 5,
            "tension": 0.3,
            "last_cycle": "running",
            "cycles_this_hour": 5,
            "backend": "json",
        }
        mock_rt.graph.nodes = {}
        mock_rt.graph.edges = []
        mock_rt.graph.get_metrics.return_value = {
            "total_nodes": 0,
            "active_nodes": 0,
            "collapsed_nodes": 0,
            "edges": 0,
            "avg_activation": 0.0,
            "avg_stability": 0.0,
            "topics": {},
            "edge_density": 0.0,
            "embedded_nodes": 0,
        }
        mock_rt.graph.graph_path = Path("test.json")
        mock_rt.graph.folded_wave_nodes = MagicMock(return_value=[])
        mock_ft = MagicMock()
        mock_ft.config.adapter_save_path = str(Path("/tmp/boggers_adapter_mock"))
        mock_rt.fine_tuner = mock_ft
        with patch("BoggersTheAI.dashboard.app.get_runtime", return_value=mock_rt):
            from BoggersTheAI.dashboard.app import app

            self.client = TestClient(app)
            yield

    def test_status_endpoint(self):
        response = self.client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "graph" in data

    def test_wave_endpoint(self):
        response = self.client.get("/wave")
        assert response.status_code == 200
        assert "Chart.js" in response.text or "waveChart" in response.text

    def test_graph_viz_endpoint(self):
        response = self.client.get("/graph/viz")
        assert response.status_code == 200
        assert "cytoscape" in response.text.lower()
        assert "setinterval" in response.text.lower()

    def test_metrics_endpoint(self):
        response = self.client.get("/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "graph" in data
        assert "wave" in data
        assert "cpu_distillora" in data
        assert "folded_wave_nodes" in data
        assert data["folded_wave_count"] == 0

    def test_traces_endpoint(self):
        response = self.client.get("/traces")
        assert response.status_code == 200
        data = response.json()
        assert "traces" in data


@pytest.mark.skipif(not HAS_FASTAPI, reason="fastapi not installed")
class TestDashboardAuth:
    def test_auth_required_when_token_set(self):
        with patch.dict(os.environ, {"BOGGERS_DASHBOARD_TOKEN": "secret123"}):
            import importlib

            import BoggersTheAI.dashboard.app as dash_module

            importlib.reload(dash_module)
            client = TestClient(dash_module.app)
            response = client.get("/status")
            assert response.status_code == 401
