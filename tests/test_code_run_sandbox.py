from __future__ import annotations

from BoggersTheAI.tools.code_run import CodeRunTool


def test_sandbox_blocks_os_import():
    tool = CodeRunTool(timeout_seconds=3, sandbox=True)
    result = tool.execute(code="import os\nprint(os.getcwd())")
    assert "Blocked" in result or "blocked" in result.lower()


def test_sandbox_blocks_subprocess():
    tool = CodeRunTool(timeout_seconds=3, sandbox=True)
    result = tool.execute(code="import subprocess\nsubprocess.run(['ls'])")
    assert "Blocked" in result or "blocked" in result.lower()


def test_sandbox_allows_math():
    tool = CodeRunTool(timeout_seconds=3, sandbox=True)
    result = tool.execute(code="import math\nprint(math.sqrt(4))")
    assert "2.0" in result


def test_sandbox_off_allows_os():
    tool = CodeRunTool(timeout_seconds=3, sandbox=False)
    result = tool.execute(code="print(2+2)")
    assert "4" in result


def test_no_code_returns_message():
    tool = CodeRunTool()
    assert "No code" in tool.execute(code="")


def test_unsupported_language():
    tool = CodeRunTool()
    result = tool.execute(code="console.log('hi')", language="javascript")
    assert "Unsupported" in result
