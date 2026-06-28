from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from fastapi.testclient import TestClient

from BoggersTheAI.dashboard.app import app
from scripts.seed_graph import crawl_wikidata


class TestPhase3Features:
    @patch("scripts.seed_graph.fetch_entity")
    def test_wikidata_crawl(self, mock_fetch):
        # Mock fetch_entity response
        mock_fetch.return_value = {
            "labels": {"en": {"value": "Cognitive Physics"}},
            "descriptions": {"en": {"value": "Study of cognitive mechanics"}},
            "aliases": {"en": [{"value": "CogPhys"}]},
            "claims": {
                "P279": [
                    {
                        "mainsnak": {
                            "datavalue": {
                                "value": {"entity-type": "item", "id": "Q_TARGET"}
                            }
                        }
                    }
                ]
            },
        }

        nodes, edges = crawl_wikidata(["Q_SEED"], max_nodes=1)
        assert len(nodes) == 1
        assert "Q_SEED" in nodes
        assert nodes["Q_SEED"]["label"] == "Cognitive Physics"
        assert len(edges) == 1
        assert edges[0] == ("Q_SEED", "Q_TARGET", "P279", 0.8)

    @patch("BoggersTheAI.dashboard.app._AUTH_TOKEN", "")
    def test_api_metrics_wave_endpoint(self):
        client = TestClient(app)
        response = client.get("/api/metrics/wave")
        assert response.status_code == 200
        # It returns a list of metrics
        data = response.json()
        assert isinstance(data, list)
