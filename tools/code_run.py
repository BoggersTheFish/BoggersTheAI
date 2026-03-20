from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


class CodeRunTool:
    def __init__(self, timeout_seconds: int = 5) -> None:
        self.timeout_seconds = timeout_seconds

    def execute(self, **kwargs) -> str:
        code = str(kwargs.get("code", "")).strip()
        language = str(kwargs.get("language", "python")).strip().lower()
        if not code:
            return "No code provided."
        if language != "python":
            return f"Unsupported language: {language}. Only python is enabled."

        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = Path(temp_dir) / "snippet.py"
            script_path.write_text(code, encoding="utf-8")
            try:
                completed = subprocess.run(
                    ["python", str(script_path)],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                    check=False,
                )
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
