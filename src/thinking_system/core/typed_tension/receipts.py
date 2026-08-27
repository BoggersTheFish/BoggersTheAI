"""Receipt helpers for TS artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from .types import Receipt


def write_receipt(receipt: Receipt, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(receipt.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return target
