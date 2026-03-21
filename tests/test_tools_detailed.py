from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from BoggersTheAI.tools.executor import ToolExecutor  # noqa: E402
from BoggersTheAI.tools.router import ToolRouter  # noqa: E402


class TestToolRouter:
    def setup_method(self):
        self.router = ToolRouter()

    def test_routes_file_read(self):
        result = self.router.route("read file `config.yaml`", 0.8)
        assert result is not None
        assert result.tool_name == "file_read"
        assert result.args["path"] == "config.yaml"

    def test_routes_calc(self):
        result = self.router.route("what is 2 + 3", 0.8)
        assert result is not None
        assert result.tool_name == "calc"

    def test_routes_search_explicit(self):
        result = self.router.route("search for python tutorials", 0.8)
        assert result is not None
        assert result.tool_name == "search"

    def test_routes_search_fallback(self):
        result = self.router.route("obscure topic", 0.1, topics=["obscure"])
        assert result is not None
        assert result.tool_name == "search"

    def test_no_tool_when_sufficient(self):
        result = self.router.route("hello world", 0.9)
        assert result is None

    def test_extract_code_block(self):
        query = 'run this:\n```python\nprint("hi")\n```'
        result = self.router._extract_code_block(query)
        assert result == 'print("hi")'

    def test_extract_math(self):
        result = self.router._extract_math_expression("calculate 2 + 3")
        assert result is not None
        assert "+" in result

    def test_detect_language_always_python(self):
        assert self.router._detect_language("bash script") == "python"


class TestToolExecutor:
    def test_with_defaults_creates_tools(self):
        executor = ToolExecutor.with_defaults()
        names = executor.registry.names()
        assert "calc" in names
        assert "search" in names
        assert "code_run" in names
        assert "file_read" in names

    def test_calc_execution(self):
        executor = ToolExecutor.with_defaults()
        result = executor.execute("calc", {"expression": "10 * 5"})
        assert "50" in result
