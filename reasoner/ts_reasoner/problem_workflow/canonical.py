"""Fail-closed canonicalization for the bounded problem workflow.

PRIME deliberately rejects native floats.  Constraint-field code still uses
Python floats internally, so this boundary converts each finite value to its
exact hexadecimal representation before any value reaches PRIME.
"""

from __future__ import annotations

import math
import unicodedata
from collections.abc import Mapping, Sequence
from enum import Enum
from hashlib import sha256
from typing import Any


FLOAT_HEX_TAG = "$ts_float_hex"
_RESERVED_SOURCE_KEYS = frozenset({FLOAT_HEX_TAG})


class WorkflowCanonicalizationError(ValueError):
    """A source value cannot be represented without ambiguity."""


def _nfc_text(value: str) -> str:
    if value != unicodedata.normalize("NFC", value):
        raise WorkflowCanonicalizationError("strings must already be NFC-normalized")
    if "\x00" in value:
        raise WorkflowCanonicalizationError("NUL bytes are forbidden")
    return value


def canonicalize_source(value: Any) -> Any:
    """Return a detached PRIME-safe value.

    Reserved numeric-tag keys are rejected at the source boundary.  They can
    only be emitted by this function while converting an actual finite float.
    """

    if isinstance(value, Enum):
        return canonicalize_source(value.value)
    if value is None or isinstance(value, bool) or isinstance(value, int):
        return value
    if isinstance(value, str):
        return _nfc_text(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise WorkflowCanonicalizationError("non-finite floats are forbidden")
        return {FLOAT_HEX_TAG: value.hex()}
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise WorkflowCanonicalizationError("object keys must be strings")
            canonical_key = _nfc_text(key)
            if canonical_key in _RESERVED_SOURCE_KEYS:
                raise WorkflowCanonicalizationError(
                    f"reserved canonical key is forbidden in source data: {canonical_key}"
                )
            if canonical_key in result:
                raise WorkflowCanonicalizationError("duplicate canonical object key")
            result[canonical_key] = canonicalize_source(item)
        return result
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [canonicalize_source(item) for item in value]
    raise WorkflowCanonicalizationError(
        f"unsupported source value: {type(value).__name__}"
    )


def canonical_tree_is_valid(value: Any) -> bool:
    """Pure recursive verifier for an already converted canonical tree."""

    if value is None or isinstance(value, bool) or isinstance(value, int):
        return True
    if isinstance(value, str):
        return value == unicodedata.normalize("NFC", value) and "\x00" not in value
    if isinstance(value, float):
        return False
    if isinstance(value, list):
        return all(canonical_tree_is_valid(item) for item in value)
    if not isinstance(value, dict):
        return False
    if any(not isinstance(key, str) for key in value):
        return False
    if any(key != unicodedata.normalize("NFC", key) or "\x00" in key for key in value):
        return False
    if FLOAT_HEX_TAG in value:
        if set(value) != {FLOAT_HEX_TAG}:
            return False
        encoded = value[FLOAT_HEX_TAG]
        if not isinstance(encoded, str):
            return False
        try:
            decoded = float.fromhex(encoded)
        except ValueError:
            return False
        return math.isfinite(decoded) and decoded.hex() == encoded
    return all(canonical_tree_is_valid(item) for item in value.values())


def contains_native_float(value: Any) -> bool:
    """Return whether a nested value still contains any native float."""

    if isinstance(value, float):
        return True
    if isinstance(value, dict):
        return any(contains_native_float(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(contains_native_float(item) for item in value)
    return False


def restore_source_floats(value: Any) -> Any:
    """Decode only well-formed workflow float tags into detached native values."""

    if isinstance(value, list):
        return [restore_source_floats(item) for item in value]
    if not isinstance(value, dict):
        return value
    if set(value) == {FLOAT_HEX_TAG} and canonical_tree_is_valid(value):
        return float.fromhex(value[FLOAT_HEX_TAG])
    return {key: restore_source_floats(item) for key, item in value.items()}


def _json_string(value: str) -> str:
    pieces = ['"']
    escapes = {
        '"': '\\"',
        "\\": "\\\\",
        "\b": "\\b",
        "\f": "\\f",
        "\n": "\\n",
        "\r": "\\r",
        "\t": "\\t",
    }
    for character in value:
        escaped = escapes.get(character)
        if escaped is not None:
            pieces.append(escaped)
        elif ord(character) < 0x20:
            pieces.append(f"\\u{ord(character):04x}")
        else:
            pieces.append(character)
    pieces.append('"')
    return "".join(pieces)


def canonical_tree_text(value: Any) -> str:
    """Encode a verified tree with PRIME's exact canonical JSON rules."""

    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return _json_string(value)
    if isinstance(value, list):
        return "[" + ",".join(canonical_tree_text(item) for item in value) + "]"
    if isinstance(value, dict):
        return (
            "{"
            + ",".join(
                _json_string(key) + ":" + canonical_tree_text(value[key])
                for key in sorted(value)
            )
            + "}"
        )
    raise WorkflowCanonicalizationError("value is not a canonical workflow tree")


def workflow_stable_hash(value: Any) -> str:
    """Hash a canonical tree without a dynamic JSON encoder dependency."""

    if not canonical_tree_is_valid(value):
        raise WorkflowCanonicalizationError("cannot hash an invalid canonical tree")
    return sha256(canonical_tree_text(value).encode("utf-8")).hexdigest()
