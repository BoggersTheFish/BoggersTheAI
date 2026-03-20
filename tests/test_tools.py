from __future__ import annotations

from BoggersTheAI.tools.calc import CalcTool
from BoggersTheAI.tools.file_read import FileReadTool
from BoggersTheAI.tools.search import SearchTool


def test_calc_basic_math():
    tool = CalcTool()
    result = tool.execute(expression="2 + 3")
    assert "5" in result


def test_calc_rejects_invalid():
    tool = CalcTool()
    result = tool.execute(expression="__import__('os')")
    assert "failed" in result.lower() or "unsupported" in result.lower()


def test_file_read_rejects_bad_extension():
    tool = FileReadTool()
    result = tool.execute(path="secret.exe")
    assert "not allowed" in result.lower() or "error" in result.lower()


def test_search_tool_has_configurable_url():
    tool = SearchTool(base_url="https://example.com/search")
    assert tool.base_url == "https://example.com/search"
