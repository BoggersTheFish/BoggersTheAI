from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from BoggersTheAI.adapters.base import AdapterRegistry  # noqa: E402
from BoggersTheAI.adapters.hacker_news import HackerNewsAdapter  # noqa: E402
from BoggersTheAI.adapters.markdown import MarkdownAdapter  # noqa: E402
from BoggersTheAI.adapters.rss import RSSAdapter  # noqa: E402
from BoggersTheAI.adapters.wikipedia import WikipediaAdapter  # noqa: E402
from BoggersTheAI.adapters.x_api import XApiAdapter  # noqa: E402


class TestWikipediaAdapter:
    @patch("BoggersTheAI.shared.http.urlopen")
    def test_success(self, mock_urlopen):
        body = json.dumps(
            {
                "query": {
                    "pages": {
                        "12345": {
                            "title": "Python",
                            "extract": "A programming language.",
                        }
                    }
                }
            }
        ).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = body
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        adapter = WikipediaAdapter()
        nodes = adapter.ingest("python")
        assert len(nodes) >= 1
        assert "python" in nodes[0].topics[0].lower() or "wiki" in nodes[0].id

    @patch(
        "BoggersTheAI.shared.http.urlopen",
        side_effect=Exception("timeout"),
    )
    def test_timeout(self, mock_urlopen):
        adapter = WikipediaAdapter()
        nodes = adapter.ingest("python")
        assert nodes == []


class TestRSSAdapter:
    def test_rejects_non_https(self):
        adapter = RSSAdapter()
        nodes = adapter.ingest("http://example.com/feed")
        assert nodes == []

    @patch(
        "BoggersTheAI.shared.http.urlopen",
        side_effect=Exception("net error"),
    )
    def test_network_error(self, mock_urlopen):
        adapter = RSSAdapter()
        nodes = adapter.ingest("https://example.com/feed")
        assert nodes == []


class TestHackerNewsAdapter:
    @patch("BoggersTheAI.shared.http.urlopen")
    def test_success(self, mock_urlopen):
        body = json.dumps(
            {
                "hits": [
                    {
                        "title": "HN Post",
                        "url": "https://hn.com/1",
                        "objectID": "1",
                    }
                ]
            }
        ).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = body
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        adapter = HackerNewsAdapter()
        nodes = adapter.ingest("python")
        assert len(nodes) >= 1


class TestXApiAdapter:
    def test_no_token(self):
        adapter = XApiAdapter()
        nodes = adapter.ingest("python")
        assert nodes == []


class TestMarkdownAdapter:
    def test_ingest_file(self, tmp_path):
        md_file = tmp_path / "test.md"
        md_file.write_text("# Hello\nWorld content", encoding="utf-8")
        adapter = MarkdownAdapter(base_dir=str(tmp_path))
        nodes = adapter.ingest("test.md")
        assert len(nodes) >= 1
        assert (
            "hello" in nodes[0].content.lower() or "world" in nodes[0].content.lower()
        )

    def test_missing_file(self):
        adapter = MarkdownAdapter()
        nodes = adapter.ingest("/nonexistent/path.md")
        assert nodes == []


class TestArXivAdapter:
    @patch("BoggersTheAI.shared.http.urlopen")
    def test_arxiv_success(self, mock_urlopen):
        xml_body = """<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <id>http://arxiv.org/abs/1234.5678v1</id>
            <title>Title of paper</title>
            <summary>Abstract summary of the paper</summary>
            <author><name>Author One</name></author>
            <author><name>Author Two</name></author>
          </entry>
        </feed>
        """
        mock_resp = MagicMock()
        mock_resp.read.return_value = xml_body.encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        from BoggersTheAI.adapters.arxiv import ArXivAdapter

        adapter = ArXivAdapter()
        nodes = adapter.ingest("deep learning")
        assert len(nodes) == 1
        assert "1234.5678v1" in nodes[0].attributes["arxiv_id"]
        assert "Title of paper" in nodes[0].content
        assert "arxiv" in nodes[0].topics

    @patch("BoggersTheAI.shared.http.urlopen", side_effect=Exception("timeout"))
    def test_arxiv_error(self, mock_urlopen):
        from BoggersTheAI.adapters.arxiv import ArXivAdapter

        adapter = ArXivAdapter()
        nodes = adapter.ingest("deep learning")
        assert nodes == []


class TestSemanticScholarAdapter:
    @patch("BoggersTheAI.shared.http.urlopen")
    def test_semantic_scholar_success(self, mock_urlopen):
        json_body = json.dumps(
            {
                "data": [
                    {
                        "paperId": "abcdef123456",
                        "title": "Semantic Paper Title",
                        "abstract": "Abstract of Semantic Paper",
                        "citationCount": 99,
                        "authors": [{"name": "Scholar One"}],
                    }
                ]
            }
        ).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = json_body
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        from BoggersTheAI.adapters.semantic_scholar import SemanticScholarAdapter

        adapter = SemanticScholarAdapter()
        nodes = adapter.ingest("nlp")
        assert len(nodes) == 1
        assert nodes[0].attributes["paper_id"] == "abcdef123456"
        assert "nlp" in nodes[0].topics

    @patch("BoggersTheAI.shared.http.urlopen", side_effect=Exception("timeout"))
    def test_semantic_scholar_error(self, mock_urlopen):
        from BoggersTheAI.adapters.semantic_scholar import SemanticScholarAdapter

        adapter = SemanticScholarAdapter()
        nodes = adapter.ingest("nlp")
        assert nodes == []


class TestAdapterRegistryAdvanced:
    def test_cache_returns_same_on_repeat(self):
        registry = AdapterRegistry()
        mock_adapter = MagicMock()
        mock_adapter.poll_interval = 60
        mock_adapter.ingest.return_value = []
        registry.register("test", mock_adapter)
        registry.ingest("test", "topic1")
        registry.ingest("test", "topic1")
        assert mock_adapter.ingest.call_count == 1

    def test_rate_limit(self):
        registry = AdapterRegistry()
        mock_adapter = MagicMock()
        mock_adapter.poll_interval = 60
        mock_adapter.ingest.return_value = []
        registry.register("flood", mock_adapter)
        for i in range(35):
            registry.ingest("flood", f"topic_{i}")
        assert mock_adapter.ingest.call_count <= 31
