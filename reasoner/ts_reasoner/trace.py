"""Trace export helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .types import ReasonerOutput, to_jsonable


def write_json(output: ReasonerOutput, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def write_jsonl(outputs: Iterable[ReasonerOutput], path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        for output in outputs:
            handle.write(json.dumps(to_jsonable(output), sort_keys=True) + "\n")
    return target

