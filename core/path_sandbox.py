from __future__ import annotations

from pathlib import Path


def validate_path(requested: str, base_dir: str) -> Path:
    """Resolve requested path under base_dir. Raise ValueError if traversal detected."""
    base = Path(base_dir).resolve()
    target = (base / requested).resolve()
    if not str(target).startswith(str(base)):
        raise ValueError(f"Path traversal blocked: {requested!r} escapes {base_dir!r}")
    return target
