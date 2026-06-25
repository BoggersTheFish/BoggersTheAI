from __future__ import annotations

from typing import Any

from ts_reasoner.candidate_bridge import run_tensionlm_candidate_bridge

from .features import extract_candidate_features
from .model import TinyCandidateModel


def score_case(model: TinyCandidateModel, case: dict[str, Any]) -> dict[str, Any]:
    scored = []
    for candidate in case["candidates"]:
        features = extract_candidate_features(case, candidate)
        prediction = model.predict(features)
        scored.append({**candidate, "features": features, "prediction": prediction})
    scored.sort(key=lambda item: item["prediction"]["ranking_score"], reverse=True)
    return {**case, "scored_candidates": scored}


def verify_scored_case(model: TinyCandidateModel, case: dict[str, Any]) -> dict[str, Any]:
    scored_case = score_case(model, case)
    payload = run_tensionlm_candidate_bridge(
        case["input_text"],
        case.get("premises"),
        mode="external",
        external_hook=lambda _text, _premises: [
            {
                "candidate_id": candidate["candidate_id"],
                "claim": candidate["claim"],
                "source": "learned_candidate_model",
                "confidence": candidate["prediction"]["model_confidence"],
                "raw_output": candidate["claim"],
                "metadata": {
                    "model_prediction": candidate["prediction"],
                    "input_candidate_confidence": candidate.get("confidence"),
                    "boundary": "learned model proposes/ranks; TS-Reasoner typed channels verify",
                },
            }
            for candidate in scored_case["scored_candidates"]
        ],
    )
    return {**scored_case, "verification": payload["verification"], "trace_receipt": payload["trace_receipt"]}
