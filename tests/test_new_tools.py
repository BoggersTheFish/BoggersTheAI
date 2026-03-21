from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from BoggersTheAI.tools.datetime_tool import DateTimeTool
from BoggersTheAI.tools.unit_convert import UnitConvertTool
from BoggersTheAI.tools.web_search import WebSearchTool

# ── WebSearchTool ──────────────────────────────────────


def test_web_search_empty_query():
    tool = WebSearchTool()
    assert tool.execute() == "No query provided."
    assert tool.execute(query="") == "No query provided."


def test_web_search_returns_abstract():
    payload = json.dumps({"AbstractText": "Python is a language."}).encode()
    mock_resp = MagicMock()
    mock_resp.read.return_value = payload
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch(
        "BoggersTheAI.tools.web_search.urlopen",
        return_value=mock_resp,
    ):
        result = WebSearchTool().execute(query="python")
    assert result == "Python is a language."


def test_web_search_returns_related():
    payload = json.dumps(
        {
            "AbstractText": "",
            "RelatedTopics": [{"Text": "Related topic one"}],
        }
    ).encode()
    mock_resp = MagicMock()
    mock_resp.read.return_value = payload
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch(
        "BoggersTheAI.tools.web_search.urlopen",
        return_value=mock_resp,
    ):
        result = WebSearchTool().execute(query="test")
    assert result == "Related topic one"


def test_web_search_no_results():
    payload = json.dumps({"AbstractText": "", "RelatedTopics": []}).encode()
    mock_resp = MagicMock()
    mock_resp.read.return_value = payload
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch(
        "BoggersTheAI.tools.web_search.urlopen",
        return_value=mock_resp,
    ):
        result = WebSearchTool().execute(query="xyz")
    assert result == "No results found."


def test_web_search_handles_network_error():
    with patch(
        "BoggersTheAI.tools.web_search.urlopen",
        side_effect=OSError("timeout"),
    ):
        result = WebSearchTool().execute(query="fail")
    assert "Search failed" in result


# ── DateTimeTool ───────────────────────────────────────


def test_datetime_now():
    tool = DateTimeTool()
    result = tool.execute()
    assert "T" in result
    assert "+" in result or "Z" in result


def test_datetime_now_explicit():
    tool = DateTimeTool()
    result = tool.execute(action="now")
    assert "T" in result


def test_datetime_parse():
    tool = DateTimeTool()
    result = tool.execute(
        action="parse",
        text="2025-06-15T12:00:00",
        format="%Y-%m-%d",
    )
    assert result == "2025-06-15"


def test_datetime_format():
    tool = DateTimeTool()
    result = tool.execute(action="format", format="%Y")
    assert len(result) == 4
    assert result.isdigit()


def test_datetime_parse_invalid():
    tool = DateTimeTool()
    result = tool.execute(action="parse", text="not-a-date")
    assert "error" in result.lower()


# ── UnitConvertTool ────────────────────────────────────


def test_unit_convert_km_to_miles():
    tool = UnitConvertTool()
    result = tool.execute(value=10, **{"from": "km", "to": "miles"})
    assert "6.2137" in result


def test_unit_convert_c_to_f():
    tool = UnitConvertTool()
    result = tool.execute(value=100, **{"from": "c", "to": "f"})
    assert "212.0000" in result


def test_unit_convert_f_to_c():
    tool = UnitConvertTool()
    result = tool.execute(value=32, **{"from": "f", "to": "c"})
    assert "0.0000" in result


def test_unit_convert_unknown():
    tool = UnitConvertTool()
    result = tool.execute(value=1, **{"from": "foo", "to": "bar"})
    assert "Unknown conversion" in result


def test_unit_convert_bad_value():
    tool = UnitConvertTool()
    result = tool.execute(value="abc", **{"from": "km", "to": "miles"})
    assert "error" in result.lower()
