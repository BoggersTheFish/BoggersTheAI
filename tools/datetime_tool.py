from __future__ import annotations

from datetime import datetime, timezone


class DateTimeTool:
    """Parse and format dates, get current time."""

    def execute(self, **kwargs) -> str:
        action = str(kwargs.get("action", "now")).strip()
        if action == "now":
            return datetime.now(timezone.utc).isoformat()
        fmt = str(kwargs.get("format", "%Y-%m-%d %H:%M:%S"))
        try:
            if action == "parse":
                text = str(kwargs.get("text", ""))
                dt = datetime.fromisoformat(text)
                return dt.strftime(fmt)
            elif action == "format":
                return datetime.now(timezone.utc).strftime(fmt)
        except (ValueError, TypeError) as exc:
            return f"Date/time error: {exc}"
        return datetime.now(timezone.utc).isoformat()
