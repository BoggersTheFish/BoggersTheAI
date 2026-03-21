from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger("boggers.tools.file_read")

ALLOWED_EXTENSIONS = {".txt", ".md", ".py", ".json", ".yaml", ".yml", ".csv", ".log"}


class FileReadTool:
    def __init__(self, base_dir: str | None = None) -> None:
        self.base_dir = os.path.realpath(base_dir) if base_dir else os.getcwd()

    def execute(self, **kwargs) -> str:
        raw_path = str(kwargs.get("path", "")).strip()
        if not raw_path:
            return "File path is empty."

        resolved = os.path.realpath(raw_path)
        if not resolved.startswith(self.base_dir):
            return "Error: path escapes base directory"
        _, ext = os.path.splitext(resolved)
        if ext.lower() not in ALLOWED_EXTENSIONS:
            return f"Error: file extension '{ext}' not allowed"

        path = Path(resolved)
        if not path.exists():
            return f"File not found: {path}"
        if path.is_dir():
            return f"Path is a directory, not a file: {path}"
        try:
            return path.read_text(encoding="utf-8")
        except Exception as exc:
            return f"File read failed: {exc}"
