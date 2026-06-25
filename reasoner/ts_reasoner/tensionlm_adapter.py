"""Adapter for exported TensionLM-style candidate outputs.

This module does not load model weights. It accepts JSONL rows that look like
real or exported model outputs, normalizes them into the v1.1 candidate bridge
contract, and delegates verification to TS-Reasoner typed channels.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .candidate_bridge import run_tensionlm_candidate_bridge
from .candidates import CandidateClaim
from .generator import RELATION_RE, ParsedRelation


@dataclass(frozen=True)
class TensionLMExportRow:
    row_id: str
    input_text: str
    model: str
    candidates: list[CandidateClaim]
    premises: list[str] | None = None
    raw: dict[str, Any] | None = None


def load_tensionlm_export_jsonl(path: str | Path) -> list[TensionLMExportRow]:
    rows = []
    for index, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        rows.append(parse_tensionlm_export_row(json.loads(line), index))
    return rows


def parse_tensionlm_export_row(row: dict[str, Any], index: int = 1) -> TensionLMExportRow:
    input_text = str(row["input_text"])
    model = str(row.get("model", "unknown_model"))
    row_id = str(row.get("case_id", row.get("row_id", f"export_row_{index}")))
    candidates = [
        normalize_export_candidate(candidate, candidate_index, model, row_id)
        for candidate_index, candidate in enumerate(row.get("candidates", []), start=1)
    ]
    premises = row.get("premises")
    return TensionLMExportRow(
        row_id=row_id,
        input_text=input_text,
        model=model,
        candidates=candidates,
        premises=[str(premise).strip() for premise in premises if str(premise).strip()] if premises else None,
        raw=dict(row),
    )


def normalize_export_candidate(
    candidate: dict[str, Any],
    index: int,
    model: str,
    row_id: str,
) -> CandidateClaim:
    provenance = candidate.get("provenance", "")
    source = str(provenance) if provenance is not None else ""
    raw_text = candidate.get("raw_text", candidate.get("raw_output"))
    source_claim = str(candidate.get("claim", raw_text or ""))
    normalized_claim, normalization_status = normalize_candidate_claim_text(source_claim)
    confidence, confidence_status = coerce_candidate_confidence(candidate.get("confidence", 0.5))
    return CandidateClaim(
        candidate_id=str(candidate.get("candidate_id", f"{row_id}_candidate_{index}")),
        claim=normalized_claim,
        source=source,
        confidence=confidence,
        raw_output=str(raw_text) if raw_text is not None else None,
        metadata={
            "model": model,
            "adapter": "real_tensionlm_export_jsonl",
            "row_id": row_id,
            "source_claim": source_claim,
            "normalization_status": normalization_status,
            "confidence_status": confidence_status,
            "raw_candidate": dict(candidate),
        },
    )


def coerce_candidate_confidence(value: Any) -> tuple[float, str]:
    if value is None:
        return 0.5, "missing_defaulted"
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.5, "invalid_defaulted"
    return max(0.0, min(1.0, confidence)), "provided"


def normalize_candidate_claim_text(text: str) -> tuple[str, str]:
    normalized_space = " ".join(text.replace("\n", " ").split())
    matches: list[tuple[int, ParsedRelation, str]] = []
    for match in RELATION_RE.finditer(normalized_space):
        matches.append(
            (
                match.start(),
                ParsedRelation(
                    quantifier=match.group("quantifier").lower(),
                    subject=match.group("subject"),
                    predicate=match.group("predicate"),
                    text=match.group(0),
                ),
                "canonical_relation",
            )
        )
    paraphrase_patterns = [
        (
            "all",
            re.compile(
                r"\b(?:every|each)\s+(?P<subject>[A-Za-z][A-Za-z0-9_-]*)\s+"
                r"(?:is|are|becomes|become|counts\s+as|count\s+as|belongs\s+to|belong\s+to|"
                r"falls\s+under|fall\s+under|is\s+a\s+kind\s+of|are\s+kinds\s+of|is\s+an?|are)\s+"
                r"(?P<predicate>[A-Za-z][A-Za-z0-9_-]*)\b",
                re.IGNORECASE,
            ),
        ),
        (
            "all",
            re.compile(
                r"\ball\s+(?P<subject>[A-Za-z][A-Za-z0-9_-]*)\s+"
                r"(?:become|are|count\s+as|belong\s+to|fall\s+under|are\s+kinds\s+of)\s+"
                r"(?P<predicate>[A-Za-z][A-Za-z0-9_-]*)\b",
                re.IGNORECASE,
            ),
        ),
        (
            "some",
            re.compile(
                r"\b(?:some|at\s+least\s+one)\s+(?P<subject>[A-Za-z][A-Za-z0-9_-]*)\s+"
                r"(?:is|are|belongs\s+to|belong\s+to|falls\s+under|fall\s+under)\s+"
                r"(?P<predicate>[A-Za-z][A-Za-z0-9_-]*)\b",
                re.IGNORECASE,
            ),
        ),
        (
            "no",
            re.compile(
                r"\b(?:none\s+of\s+the|no)\s+(?P<subject>[A-Za-z][A-Za-z0-9_-]*)\s+"
                r"(?:is|are|belongs\s+to|belong\s+to|falls\s+under|fall\s+under)\s+"
                r"(?P<predicate>[A-Za-z][A-Za-z0-9_-]*)\b",
                re.IGNORECASE,
            ),
        ),
    ]
    for quantifier, pattern in paraphrase_patterns:
        for match in pattern.finditer(normalized_space):
            matches.append(
                (
                    match.start(),
                    ParsedRelation(
                        quantifier=quantifier,
                        subject=match.group("subject"),
                        predicate=match.group("predicate"),
                        text=match.group(0),
                    ),
                    "messy_paraphrase",
                )
            )
    if not matches:
        return text, "unparsed"
    _start, relation, status = sorted(matches, key=lambda item: item[0])[-1]
    return _claim_text(relation), status


def _claim_text(relation: ParsedRelation) -> str:
    return f"{relation.quantifier.capitalize()} {relation.subject} are {relation.predicate}"


def run_tensionlm_export_row(row: TensionLMExportRow) -> dict[str, Any]:
    payload = run_tensionlm_candidate_bridge(
        row.input_text,
        row.premises,
        mode="external",
        external_hook=lambda _text, _premises: row.candidates,
    )
    payload["adapter"] = {
        "name": "real_tensionlm_export_jsonl",
        "row_id": row.row_id,
        "model": row.model,
        "candidate_count": len(row.candidates),
        "input_format": "jsonl",
    }
    return payload


def run_tensionlm_export_rows(rows: Iterable[TensionLMExportRow]) -> list[dict[str, Any]]:
    return [run_tensionlm_export_row(row) for row in rows]


def run_tensionlm_export_jsonl(path: str | Path) -> list[dict[str, Any]]:
    return run_tensionlm_export_rows(load_tensionlm_export_jsonl(path))
