from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def write_receipt(
    path: str | Path,
    payload: dict[str, Any],
) -> Path:
    destination = Path(path)
    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    receipt = {
        "schema": "tensionforge.receipt.v1",
        "created_at_utc": datetime.now(
            UTC
        ).isoformat(),
        **payload,
    }

    destination.write_text(
        json.dumps(
            receipt,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    return destination
