from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

_RESTRICTED_IMPORTS = frozenset(
    {
        "os",
        "sys",
        "subprocess",
        "shutil",
        "socket",
        "http",
        "urllib",
        "requests",
        "ctypes",
        "signal",
        "importlib",
        "pathlib",
        "glob",
        "io",
        "builtins",
        "__builtin__",
        "pickle",
        "shelve",
        "sqlite3",
        "webbrowser",
        "smtplib",
        "ftplib",
        "telnetlib",
    }
)

_SANDBOX_PREAMBLE = """
import builtins as _builtins
_original_import = _builtins.__import__
_BLOCKED = {blocked}
def _safe_import(name, *args, _blocked=_BLOCKED, _orig=_original_import, **kwargs):
    base = name.split(".")[0]
    if base in _blocked:
        raise ImportError(f"Import of '{{name}}' is blocked in sandbox mode")
    return _orig(name, *args, **kwargs)
_builtins.__import__ = _safe_import
del _builtins, _original_import, _safe_import, _BLOCKED
"""


class CodeRunTool:
    def __init__(
        self,
        timeout_seconds: int = 5,
        sandbox: bool = True,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.sandbox = sandbox

    def execute(self, **kwargs) -> str:
        code = str(kwargs.get("code", "")).strip()
        language = str(kwargs.get("language", "python")).strip().lower()
        if not code:
            return "No code provided."
        if language != "python":
            return f"Unsupported language: {language}. Only python is enabled."

        if self.sandbox:
            for line in code.splitlines():
                stripped = line.strip()
                if stripped.startswith("import ") or stripped.startswith("from "):
                    parts = (
                        stripped.replace("import ", " ").replace("from ", " ").split()
                    )
                    for part in parts:
                        base = part.split(".")[0]
                        if base in _RESTRICTED_IMPORTS:
                            return (
                                f"Blocked: import of '{base}'"
                                " is not allowed in sandbox mode."
                            )
            try:
                import ast

                tree = ast.parse(code)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        func = node.func
                        name = ""
                        if isinstance(func, ast.Name):
                            name = func.id
                        elif isinstance(func, ast.Attribute):
                            name = func.attr
                        if name == "__import__" and node.args:
                            arg = node.args[0]
                            if isinstance(arg, ast.Constant) and isinstance(
                                arg.value, str
                            ):
                                base = arg.value.split(".")[0]
                                if base in _RESTRICTED_IMPORTS:
                                    return (
                                        f"Blocked: __import__('{base}')"
                                        " is not allowed in sandbox mode."
                                    )
                        if name in ("exec", "eval") and node.args:
                            arg = node.args[0]
                            if isinstance(arg, ast.Constant) and isinstance(
                                arg.value, str
                            ):
                                for restricted in _RESTRICTED_IMPORTS:
                                    if f"import {restricted}" in arg.value:
                                        return (
                                            f"Blocked: dynamic import of"
                                            f" '{restricted}' via {name}()"
                                            " is not allowed in sandbox mode."
                                        )
            except SyntaxError:
                pass

        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = Path(temp_dir) / "snippet.py"
            if self.sandbox:
                preamble = _SANDBOX_PREAMBLE.format(blocked=repr(_RESTRICTED_IMPORTS))
                script_path.write_text(preamble + "\n" + code, encoding="utf-8")
            else:
                script_path.write_text(code, encoding="utf-8")
            try:
                completed = subprocess.run(
                    [sys.executable, str(script_path)],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                    check=False,
                    cwd=temp_dir,
                )
            except subprocess.TimeoutExpired:
                return f"Code execution timed out after {self.timeout_seconds}s."
            except Exception as exc:
                return f"Code execution failed: {exc}"

            stdout = completed.stdout.strip()
            stderr = completed.stderr.strip()
            output = []
            output.append(f"exit_code={completed.returncode}")
            if stdout:
                output.append(f"stdout:\n{stdout}")
            if stderr:
                output.append(f"stderr:\n{stderr}")
            return "\n".join(output)
