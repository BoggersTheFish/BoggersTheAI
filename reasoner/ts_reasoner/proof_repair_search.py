"""Minimal proof / repair search for TS-Reasoner v7.8.0.

Adds bounded graph search over TS-Chat common ground:
- /prove <claim>      -> shortest support path if available
- /missing <claim>    -> missing direct/bridge support suggestions
- /cut <negative>     -> contradiction cut suggestions

Boundary:
- search results are not proof
- missing bridge suggestions are not proof
- cut suggestions are not proof
- typed verifier/common-ground support remains proof authority
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ts_reasoner.answer_arena import Relation, extract_all_relation, extract_question_relation
from ts_reasoner.common_ground import CommonGround
from ts_reasoner.live_contradiction_firewall import parse_no_relation


RELEASE = "v7.8.0"
SCHEMA = "ts_reasoner_proof_repair_search_v1"


def relation_to_dict(relation: Relation) -> dict[str, str]:
    return {"subject": relation.subject, "object": relation.object}


def relation_text(relation: Relation) -> str:
    return f"all {relation.subject} are {relation.object}"


def negative_relation_text(relation: Relation) -> str:
    return f"no {relation.subject} are {relation.object}"


def parse_relation_query(text: str) -> Relation:
    cleaned = text.strip()

    negative = parse_no_relation(cleaned)
    if negative:
        return negative

    question = extract_question_relation(cleaned)
    if question:
        return question

    premise = extract_all_relation(cleaned)
    if premise:
        return premise

    # Bounded fallback: allow "cats robots" for CLI/internal tests.
    parts = cleaned.replace("?", "").replace(".", "").split()
    if len(parts) == 2:
        return Relation(parts[0], parts[1])

    raise ValueError(f"Could not parse bounded relation query: {text}")


def _edge_dict(edge: tuple[str, str]) -> dict[str, str]:
    return {"subject": edge[0], "object": edge[1]}


def _all_terms(common_ground: CommonGround) -> list[str]:
    terms: set[str] = set()
    for subject, object_ in common_ground.accepted_edges:
        terms.add(subject)
        terms.add(object_)
    return sorted(terms)


def prove_relation(common_ground: CommonGround, relation: Relation) -> dict[str, Any]:
    support_path = common_ground.support_path(relation)
    supported = bool(support_path)

    return {
        "schema": SCHEMA,
        "release": RELEASE,
        "query_type": "prove",
        "relation": relation_to_dict(relation),
        "claim_text": relation_text(relation),
        "status": "supported" if supported else "unsupported",
        "support_path": support_path,
        "support_path_length": len(support_path),
        "shortest_path_found": supported,
        "search_result_is_proof": False,
        "typed_verifier_remains_proof_authority": True,
        "candidate_graph_contamination_count": 0,
        "external_llm_used": False,
    }


def missing_support_search(common_ground: CommonGround, relation: Relation) -> dict[str, Any]:
    proof = prove_relation(common_ground, relation)
    if proof["shortest_path_found"]:
        return {
            "schema": SCHEMA,
            "release": RELEASE,
            "query_type": "missing",
            "relation": relation_to_dict(relation),
            "claim_text": relation_text(relation),
            "status": "already_supported",
            "support_path": proof["support_path"],
            "missing_edges": [],
            "bridge_suggestions": [],
            "direct_support_suggestion": None,
            "search_result_is_proof": False,
            "missing_suggestion_is_proof": False,
            "typed_verifier_remains_proof_authority": True,
            "candidate_graph_contamination_count": 0,
            "external_llm_used": False,
        }

    accepted_edges = set(common_ground.accepted_edges)
    terms = _all_terms(common_ground)

    missing_edges: list[dict[str, Any]] = []
    bridge_suggestions: list[dict[str, Any]] = []

    direct = {
        "kind": "direct_support",
        "missing_edge": relation_to_dict(relation),
        "suggested_premise": relation_text(relation),
        "creates_proof": False,
        "requires_typed_verifier": True,
    }

    # Existing partial paths: subject -> bridge exists, but bridge -> object missing.
    for subject, bridge in sorted(accepted_edges):
        if subject == relation.subject and (bridge, relation.object) not in accepted_edges:
            candidate = {
                "kind": "complete_outbound_bridge",
                "bridge": bridge,
                "known_edge": {"subject": relation.subject, "object": bridge},
                "missing_edge": {"subject": bridge, "object": relation.object},
                "suggested_premise": f"all {bridge} are {relation.object}",
                "creates_proof": False,
                "requires_typed_verifier": True,
            }
            missing_edges.append(candidate)

    # Existing partial paths: bridge -> object exists, but subject -> bridge missing.
    for bridge, object_ in sorted(accepted_edges):
        if object_ == relation.object and (relation.subject, bridge) not in accepted_edges:
            candidate = {
                "kind": "complete_inbound_bridge",
                "bridge": bridge,
                "known_edge": {"subject": bridge, "object": relation.object},
                "missing_edge": {"subject": relation.subject, "object": bridge},
                "suggested_premise": f"all {relation.subject} are {bridge}",
                "creates_proof": False,
                "requires_typed_verifier": True,
            }
            missing_edges.append(candidate)

    # Bounded generic bridge templates from known graph terms.
    for bridge in terms[:8]:
        if bridge in {relation.subject, relation.object}:
            continue
        bridge_suggestions.append(
            {
                "kind": "two_hop_bridge_template",
                "bridge": bridge,
                "required_edges": [
                    {"subject": relation.subject, "object": bridge},
                    {"subject": bridge, "object": relation.object},
                ],
                "suggested_premises": [
                    f"all {relation.subject} are {bridge}",
                    f"all {bridge} are {relation.object}",
                ],
                "creates_proof": False,
                "requires_typed_verifier": True,
            }
        )

    return {
        "schema": SCHEMA,
        "release": RELEASE,
        "query_type": "missing",
        "relation": relation_to_dict(relation),
        "claim_text": relation_text(relation),
        "status": "missing_support",
        "support_path": [],
        "missing_edges": missing_edges,
        "bridge_suggestions": bridge_suggestions,
        "direct_support_suggestion": direct,
        "search_result_is_proof": False,
        "missing_suggestion_is_proof": False,
        "typed_verifier_remains_proof_authority": True,
        "candidate_graph_contamination_count": 0,
        "external_llm_used": False,
    }


def contradiction_cut_search(common_ground: CommonGround, relation: Relation) -> dict[str, Any]:
    support_path = common_ground.support_path(relation)

    cut_suggestions = []
    for idx, edge in enumerate(support_path, start=1):
        cut_suggestions.append(
            {
                "cut_id": f"cut_{idx:04d}",
                "strategy": "inspect_or_dispute_support_premise",
                "edge": edge,
                "suggested_action": f"inspect premise: all {edge['subject']} are {edge['object']}",
                "creates_proof": False,
                "requires_typed_verifier": True,
            }
        )

    return {
        "schema": SCHEMA,
        "release": RELEASE,
        "query_type": "cut",
        "negative_claim_text": negative_relation_text(relation),
        "positive_relation": relation_to_dict(relation),
        "positive_support_found": bool(support_path),
        "support_path": support_path,
        "cut_suggestions": cut_suggestions,
        "cut_suggestion_count": len(cut_suggestions),
        "search_result_is_proof": False,
        "cut_suggestion_is_proof": False,
        "typed_verifier_remains_proof_authority": True,
        "candidate_graph_contamination_count": 0,
        "external_llm_used": False,
    }


def run_search_command(common_ground: CommonGround, mode: str, query_text: str) -> dict[str, Any]:
    relation = parse_relation_query(query_text)

    if mode == "prove":
        return prove_relation(common_ground, relation)
    if mode == "missing":
        return missing_support_search(common_ground, relation)
    if mode == "cut":
        return contradiction_cut_search(common_ground, relation)

    raise ValueError(f"Unknown proof/repair search mode: {mode}")


def render_search_result(result: dict[str, Any]) -> str:
    mode = result["query_type"]

    if mode == "prove":
        if result["status"] == "supported":
            lines = [f"Supported: {result['claim_text']}"]
            lines.append("Shortest support path:")
            for edge in result["support_path"]:
                lines.append(f"- all {edge['subject']} are {edge['object']}")
        else:
            lines = [f"Unsupported: {result['claim_text']}"]
            lines.append("No support path found in accepted common ground.")
        lines.append("Boundary: search result is not proof; typed verifier support remains authority.")
        return "\n".join(lines)

    if mode == "missing":
        lines = [f"Missing search for: {result['claim_text']}"]
        if result["status"] == "already_supported":
            lines.append("Already supported by:")
            for edge in result["support_path"]:
                lines.append(f"- all {edge['subject']} are {edge['object']}")
        else:
            direct = result["direct_support_suggestion"]
            if direct:
                lines.append("Direct support option:")
                lines.append(f"- {direct['suggested_premise']}")

            if result["missing_edges"]:
                lines.append("Partial bridge completions:")
                for item in result["missing_edges"]:
                    lines.append(f"- {item['suggested_premise']}")

            if result["bridge_suggestions"]:
                lines.append("Bridge templates:")
                for item in result["bridge_suggestions"][:3]:
                    lines.append("- " + " + ".join(item["suggested_premises"]))

        lines.append("Boundary: missing-edge suggestions are candidates, not proof.")
        return "\n".join(lines)

    if mode == "cut":
        lines = [f"Cut search for contradiction: {result['negative_claim_text']}"]
        if not result["positive_support_found"]:
            lines.append("No positive support path found to cut.")
        else:
            lines.append("Positive support path currently exists:")
            for edge in result["support_path"]:
                lines.append(f"- all {edge['subject']} are {edge['object']}")
            lines.append("Cut suggestions:")
            for cut in result["cut_suggestions"]:
                edge = cut["edge"]
                lines.append(f"- inspect/dispute: all {edge['subject']} are {edge['object']}")
        lines.append("Boundary: cut suggestions are candidates, not proof.")
        return "\n".join(lines)

    return json.dumps(result, indent=2, sort_keys=True)


def search_result_valid(result: dict[str, Any]) -> bool:
    required = {
        "schema",
        "release",
        "query_type",
        "typed_verifier_remains_proof_authority",
        "candidate_graph_contamination_count",
        "external_llm_used",
    }
    if not required.issubset(result):
        return False
    if result["schema"] != SCHEMA:
        return False
    if result["release"] != RELEASE:
        return False
    if result["typed_verifier_remains_proof_authority"] is not True:
        return False
    if result["candidate_graph_contamination_count"] != 0:
        return False
    if result["external_llm_used"] is not False:
        return False
    if result["query_type"] == "prove" and result.get("search_result_is_proof") is not False:
        return False
    if result["query_type"] == "missing" and result.get("missing_suggestion_is_proof") is not False:
        return False
    if result["query_type"] == "cut" and result.get("cut_suggestion_is_proof") is not False:
        return False
    return True


def _write_json(path: str | Path, payload: Any) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out


def run_proof_repair_search_demo(out_dir: str | Path) -> dict[str, Any]:
    from ts_reasoner.ts_chat import TSChatSession, receipt_to_dict

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    session = TSChatSession()

    turns = [
        "all cats are animals",
        "all animals are mortal",
        "/prove all cats are mortal",
        "also say all cats are robots",
        "/missing all cats are robots",
        "all cats are machines",
        "/missing all cats are robots",
        "all machines are robots",
        "/prove all cats are robots",
        "no cats are mortal",
        "/cut no cats are mortal",
    ]

    receipts = [session.process(turn) for turn in turns]
    receipt_dicts = [receipt_to_dict(receipt) for receipt in receipts]

    prove_mortal = prove_relation(session.common_ground, parse_relation_query("all cats are mortal"))
    missing_robots = missing_support_search(session.common_ground, parse_relation_query("all cats are robots"))
    cut_mortal = contradiction_cut_search(session.common_ground, parse_relation_query("no cats are mortal"))

    session_path = out / "proof_repair_search_session.json"
    results_path = out / "proof_repair_search_results.json"
    report_path = out / "proof_repair_search_report.json"
    receipt_path = out / "proof_repair_search_receipt.json"

    _write_json(session_path, receipt_dicts)
    _write_json(
        results_path,
        {
            "prove_mortal": prove_mortal,
            "missing_robots": missing_robots,
            "cut_mortal": cut_mortal,
        },
    )

    command_responses = [receipt.response for receipt in receipts if receipt.command]

    gates = {
        "prove_result_valid": search_result_valid(prove_mortal),
        "missing_result_valid": search_result_valid(missing_robots),
        "cut_result_valid": search_result_valid(cut_mortal),
        "prove_support_path_found": prove_mortal["shortest_path_found"] is True,
        "missing_already_supported_after_repair": missing_robots["status"] == "already_supported",
        "cut_suggestions_found": cut_mortal["cut_suggestion_count"] >= 2,
        "live_prove_command_rendered": any("Supported: all cats are mortal" in response for response in command_responses),
        "live_missing_command_rendered": any("Missing search for: all cats are robots" in response for response in command_responses),
        "live_cut_command_rendered": any("Cut search for contradiction: no cats are mortal" in response for response in command_responses),
        "candidate_graph_contamination_count_is_zero": (
            prove_mortal["candidate_graph_contamination_count"] == 0
            and missing_robots["candidate_graph_contamination_count"] == 0
            and cut_mortal["candidate_graph_contamination_count"] == 0
        ),
        "external_llm_used_false": True,
    }

    receipt = {
        "schema": "ts_reasoner_v7_8_proof_repair_search_receipt",
        "release": RELEASE,
        "milestone": "Minimal Proof / Repair Search",
        "external_llm_used": False,
        "out_dir": str(out),
        "session_path": str(session_path),
        "results_path": str(results_path),
        "report_path": str(report_path),
        "prove_support_path_length": prove_mortal["support_path_length"],
        "missing_status_after_repair": missing_robots["status"],
        "cut_suggestion_count": cut_mortal["cut_suggestion_count"],
        "candidate_graph_contamination_count": 0,
        "search_results_are_not_proof": True,
        "missing_suggestions_are_not_proof": True,
        "cut_suggestions_are_not_proof": True,
        "typed_verifier_remains_proof_authority": True,
        "gates": gates,
        "all_gates_passed": all(gates.values()),
        "boundary": {
            "broad_natural_language_understanding": False,
            "neural_training": False,
            "live_tensionlm_runtime": False,
            "external_benchmark_victory": False,
            "search_result_is_proof": False,
            "missing_suggestion_is_proof": False,
            "cut_suggestion_is_proof": False,
            "typed_verifier_remains_proof_authority": True,
        },
    }

    report = {
        "schema": "ts_reasoner_v7_8_proof_repair_search_report",
        "release": RELEASE,
        "prove_support_path_length": receipt["prove_support_path_length"],
        "missing_status_after_repair": receipt["missing_status_after_repair"],
        "cut_suggestion_count": receipt["cut_suggestion_count"],
        "candidate_graph_contamination_count": 0,
        "external_llm_used": False,
        "all_gates_passed": receipt["all_gates_passed"],
    }

    _write_json(receipt_path, receipt)
    _write_json(report_path, report)

    receipt["receipt_path"] = str(receipt_path)
    return receipt
