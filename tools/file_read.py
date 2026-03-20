from __future__ import annotations

from pathlib import Path


class FileReadTool:
    def execute(self, **kwargs) -> str:
        raw_path = str(kwargs.get("path", "")).strip()
        if not raw_path:
            return "File path is empty."
        path = Path(raw_path)
        if not path.exists():
            return f"File not found: {path}"
        if path.is_dir():
            return f"Path is a directory, not a file: {path}"
        try:
            return path.read_text(encoding="utf-8")
        except Exception as exc:
            return f"File read failed: {exc}"
