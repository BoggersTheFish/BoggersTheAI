from __future__ import annotations

_CONVERSIONS: dict = {
    ("km", "miles"): 0.621371,
    ("miles", "km"): 1.60934,
    ("kg", "lbs"): 2.20462,
    ("lbs", "kg"): 0.453592,
    ("c", "f"): lambda v: v * 9 / 5 + 32,
    ("f", "c"): lambda v: (v - 32) * 5 / 9,
    ("m", "ft"): 3.28084,
    ("ft", "m"): 0.3048,
}


class UnitConvertTool:
    """Convert between common units."""

    def execute(self, **kwargs) -> str:
        try:
            value = float(kwargs.get("value", 0))
            from_unit = str(kwargs.get("from", "")).lower()
            to_unit = str(kwargs.get("to", "")).lower()
            key = (from_unit, to_unit)
            if key not in _CONVERSIONS:
                return f"Unknown conversion:" f" {from_unit} -> {to_unit}"
            factor = _CONVERSIONS[key]
            if callable(factor):
                result = factor(value)
            else:
                result = value * factor
            return f"{value} {from_unit}" f" = {result:.4f} {to_unit}"
        except (ValueError, TypeError) as exc:
            return f"Conversion error: {exc}"
