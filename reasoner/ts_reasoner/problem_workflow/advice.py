"""Proposal-only sealed-v18 advice normalization."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .canonical import (
    canonical_tree_is_valid,
    canonicalize_source,
    workflow_stable_hash,
)
from .model import AdviceProtocol


_V18_ARCHIVE_SHA256 = "e8fed342857776a90ec75f1e86bec216374a08be0d9c9eb25d83958088498005"
_V18_MANIFEST_SHA256 = (
    "aa0b131b9b961805937d9c2686d721511e3f74612907daa3cc9ef512a95774cd"
)
_V18_SEALED_SHA256 = "268ca140d5ff26f4c1da4177d422d59c93d7caa184af4d869911cea966da4ae8"
_V18_FREEZE_SHA256 = "7d4531ab3664c0bb20270e5927a6b53f47a70603b45431facfe9ec9aba0b1e3d"
_V18_PARENT_FIELD_SHA256 = (
    "d3a72d0fd5c11e9a50e19e45aff1535e4e9064de6200cb6200408a7626bcb2ea"
)
_V18_MODEL_SHA256 = "c6e6daf0b26ea873c7561020f36bb05f26c3adcc6e3106dcab10d17524604845"
_V18_NUMPY_ARCHIVE_SHA256 = (
    "8cd72ef4d3ab7f152bb477f7d0a00d3989e3cfc577f10db1ed23acc277228889"
)
_V18_TENSOR_SHA256 = "b6eaad261abbb644c4f1113153d6b9657875fe37d89168cba1f76ff3a07bc99f"


def _mapping_from_result(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    method = getattr(value, "to_dict", None)
    if not callable(method):
        raise ValueError("advice result does not expose a mapping")
    mapped = method()
    if not isinstance(mapped, Mapping):
        raise ValueError("advice to_dict result is not a mapping")
    return dict(mapped)


def _sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _real_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def expected_v18_worker_request_hash(text: str, top_k: int) -> str:
    return workflow_stable_hash(
        {
            "schema": "prime-v19-v18-worker-request-v1",
            "archive_sha256": _V18_ARCHIVE_SHA256,
            "operation": "structural_proposals",
            "payload": {"text": text, "top_k": top_k},
        }
    )


def _archive_receipt_is_valid(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value)
        == {
            "schema",
            "status",
            "archive_name",
            "archive_sha256",
            "archive_bytes",
            "archive_root",
            "manifest_sha256",
            "manifest_files",
            "zip_entries",
            "expanded_bytes",
            "sealed_release_sha256",
            "scientific_freeze_sha256",
            "public_version",
            "semantic_authority",
        }
        and value["schema"] == "prime-v19-v18-archive-receipt-v1"
        and value["status"] == "VERIFIED_EXACT_SEALED_PARENT"
        and value["archive_name"] == "prime-v18-v1.0.0.zip"
        and value["archive_sha256"] == _V18_ARCHIVE_SHA256
        and _real_int(value["archive_bytes"])
        and value["archive_bytes"] == 17_394_063
        and value["archive_root"] == "prime-v18-v1.0.0"
        and value["manifest_sha256"] == _V18_MANIFEST_SHA256
        and _real_int(value["manifest_files"])
        and value["manifest_files"] == 148
        and _real_int(value["zip_entries"])
        and value["zip_entries"] == 149
        and _real_int(value["expanded_bytes"])
        and value["expanded_bytes"] == 34_158_295
        and value["sealed_release_sha256"] == _V18_SEALED_SHA256
        and value["scientific_freeze_sha256"] == _V18_FREEZE_SHA256
        and value["public_version"] == "1.0.0"
        and value["semantic_authority"] == "NONE"
    )


def _mount_receipt_is_valid(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value)
        == {"schema", "status", "archive", "cache_hit", "semantic_authority"}
        and value["schema"] == "prime-v19-v18-mount-receipt-v1"
        and value["status"] == "MOUNTED_EXACT_READ_ONLY"
        and isinstance(value["cache_hit"], bool)
        and value["semantic_authority"] == "NONE"
        and _archive_receipt_is_valid(value["archive"])
    )


def advice_record_is_valid(record: Any) -> bool:
    if not isinstance(record, dict) or set(record) != {
        "schema",
        "mode",
        "semantic_authority",
        "semantic_promotions",
        "top_k",
        "failure_code",
        "description",
        "proposal_batch",
    }:
        return False
    if (
        record["schema"] != "boggers-sealed-v18-advice-v1"
        or record["semantic_authority"] != "NONE"
        or not _real_int(record["semantic_promotions"])
        or record["semantic_promotions"] != 0
        or not _real_int(record["top_k"])
        or not 1 <= record["top_k"] <= 32
        or not canonical_tree_is_valid(record)
    ):
        return False
    mode = record["mode"]
    if mode == "ABLATED":
        return (
            record["failure_code"] is None
            and record["description"] is None
            and record["proposal_batch"] is None
        )
    if mode == "UNAVAILABLE":
        return (
            record["failure_code"] == "ADVICE_UNAVAILABLE"
            and record["description"] is None
            and record["proposal_batch"] is None
        )
    if mode != "PRESENT" or record["failure_code"] is not None:
        return False
    description = record["description"]
    batch = record["proposal_batch"]
    if not _mount_receipt_is_valid(description) or not isinstance(batch, dict):
        return False
    expected_batch_keys = {
        "schema",
        "status",
        "semantic_authority",
        "semantic_promotions",
        "request_hash",
        "result_hash",
        "source",
        "runtime",
        "observed_features",
        "proposals",
    }
    if set(batch) != expected_batch_keys:
        return False
    body = {key: value for key, value in batch.items() if key != "result_hash"}
    if (
        batch.get("schema") != "prime-v19-v18-structural-proposals-v1"
        or batch.get("status") != "PROVISIONAL_NON_AUTHORITATIVE"
        or batch.get("semantic_authority") != "NONE"
        or not _real_int(batch.get("semantic_promotions"))
        or batch.get("semantic_promotions") != 0
        or not _sha256(batch.get("request_hash"))
        or not _sha256(batch.get("result_hash"))
        or batch["result_hash"] != workflow_stable_hash(body)
    ):
        return False
    source = batch["source"]
    runtime = batch["runtime"]
    observed = batch["observed_features"]
    if (
        not isinstance(source, dict)
        or set(source)
        != {
            "archive_sha256",
            "manifest_sha256",
            "model_sha256",
            "numpy_archive_sha256",
            "parent_field_archive_sha256",
            "tensor_sha256",
        }
        or source["archive_sha256"] != _V18_ARCHIVE_SHA256
        or source["manifest_sha256"] != _V18_MANIFEST_SHA256
        or source["model_sha256"] != _V18_MODEL_SHA256
        or source["numpy_archive_sha256"] != _V18_NUMPY_ARCHIVE_SHA256
        or source["parent_field_archive_sha256"] != _V18_PARENT_FIELD_SHA256
        or source["tensor_sha256"] != _V18_TENSOR_SHA256
        or not isinstance(runtime, dict)
        or set(runtime) != {"numpy_version", "python_version"}
        or not all(
            isinstance(runtime[key], str) and bool(runtime[key])
            for key in ("numpy_version", "python_version")
        )
        or not isinstance(observed, list)
        or any(not isinstance(feature, str) for feature in observed)
        or observed != sorted(set(observed))
    ):
        return False
    proposals = batch.get("proposals")
    if not isinstance(proposals, list) or len(proposals) != record["top_k"]:
        return False
    seen: set[str] = set()
    for rank, proposal in enumerate(proposals, start=1):
        if not isinstance(proposal, dict) or set(proposal) != {
            "feature",
            "rank",
            "status",
        }:
            return False
        if (
            not isinstance(proposal["feature"], str)
            or proposal["feature"] in seen
            or not _real_int(proposal["rank"])
            or proposal["rank"] != rank
            or proposal["status"] != "PROVISIONAL_NON_AUTHORITATIVE"
        ):
            return False
        seen.add(proposal["feature"])
    return True


def _empty_record(mode: str, failure_code: str | None, top_k: int) -> dict[str, Any]:
    return {
        "schema": "boggers-sealed-v18-advice-v1",
        "mode": mode,
        "semantic_authority": "NONE",
        "semantic_promotions": 0,
        "top_k": top_k,
        "failure_code": failure_code,
        "description": None,
        "proposal_batch": None,
    }


def collect_advice(
    advice: AdviceProtocol | None, text: str, *, top_k: int
) -> dict[str, Any]:
    if not _real_int(top_k) or not 1 <= top_k <= 32:
        raise ValueError("advice top_k must be an integer from 1 through 32")
    if advice is None:
        return _empty_record("ABLATED", None, top_k)
    try:
        description = canonicalize_source(_mapping_from_result(advice.describe()))
        batch = canonicalize_source(
            _mapping_from_result(advice.propose_structural_features(text, top_k=top_k))
        )
        record = {
            "schema": "boggers-sealed-v18-advice-v1",
            "mode": "PRESENT",
            "semantic_authority": "NONE",
            "semantic_promotions": 0,
            "top_k": top_k,
            "failure_code": None,
            "description": description,
            "proposal_batch": batch,
        }
        if not advice_record_is_valid(record):
            raise ValueError("sealed-v18 advice crossed the proposal-only boundary")
        if batch["request_hash"] != expected_v18_worker_request_hash(text, top_k):
            raise ValueError("sealed-v18 advice is bound to a different worker request")
        return record
    except Exception:
        return _empty_record("UNAVAILABLE", "ADVICE_UNAVAILABLE", top_k)
