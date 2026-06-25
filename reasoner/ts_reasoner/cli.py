"""Console entry point for TS-Reasoner-v0."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .milestone import print_milestone_receipt
from .firewall_receipt import print_firewall_receipt
from .pipeline import run_reasoner
from .tension_agents import TensionCoordinator
from .trace import write_json
from .ts_chat import run_chat


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the TS-Reasoner-v0 toy pipeline.")
    parser.add_argument(
        "command",
        nargs="?",
        choices=["milestone", "firewall", "chat", "v7", "compile-session", "generate-curriculum", "run-curriculum", "branch-worlds", "repair-planner", "pack-library", "trust-pressure", "proof-search", "self-audit", "v8", "v10", "repair-kernel", "research-os", "v32-v40", "cognitive-physics"],
        help="Optional command. Use milestone/firewall/chat/v7/compile-session/generate-curriculum/run-curriculum/branch-worlds/repair-planner/pack-library/trust-pressure/proof-search/self-audit/v8/v10/repair-kernel/research-os/v32-v40/cognitive-physics.",
    )
    parser.add_argument("--question", required=False, help="Question to reason about.")
    parser.add_argument(
        "--premise",
        action="append",
        default=None,
        help="Optional explicit premise. Can be passed more than once.",
    )
    parser.add_argument(
        "--trace",
        default="artifacts/latest_trace.json",
        help="Path for JSON trace output.",
    )
    parser.add_argument(
        "--coupling-matrix",
        default=None,
        help="Optional learned coupling matrix JSON artifact.",
    )
    parser.add_argument(
        "--session",
        default="artifacts/ts_chat_v0_2_latest_session.json",
        help="TS-Chat receipt JSON to compile with compile-session.",
    )
    parser.add_argument(
        "--out-dir",
        default="artifacts/compiled_sessions/latest",
        help="Output directory for compile-session artifacts.",
    )
    parser.add_argument(
        "--label",
        default="latest_session",
        help="Artifact label for compile-session outputs.",
    )
    parser.add_argument(
        "--compiled",
        default="artifacts/compiled_sessions/v7_1_demo/v7_1_demo_compiler_receipt.json",
        help="Compiler receipt path for generate-curriculum.",
    )
    parser.add_argument(
        "--curriculum",
        default="artifacts/self_curriculum/v7_2_demo/v7_2_demo_self_curriculum.jsonl",
        help="Self-curriculum JSONL path for run-curriculum.",
    )
    parser.add_argument(
        "--runtime-session",
        default="data/v10_0/runtime_os_session.json",
        help="Runtime session JSON path for v10.",
    )
    parser.add_argument(
        "--mission",
        default="prepare the next safe TS-Reasoner release candidate",
        help="Mission text for the v40 research OS.",
    )
    parser.add_argument(
        "--repo",
        default=".",
        help="Repository path for repair-kernel/research-os inspection.",
    )
    args = parser.parse_args()

    if args.command == "milestone":
        print(print_milestone_receipt())
        return 0

    if args.command == "firewall":
        print(print_firewall_receipt())
        return 0

    if args.command == "chat":
        return run_chat()

    if args.command == "v7":
        receipt_path = Path("artifacts/ts_reasoner_v7_0_self_improving_chat_receipt.json")
        if receipt_path.exists():
            print(receipt_path.read_text(encoding="utf-8").strip())
            return 0

        from ts_chat.v7_milestone import evaluate_v7_milestone

        report = evaluate_v7_milestone("artifacts/ts_reasoner_v7_milestone_cli", stress_cycles=40)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0

    if args.command == "compile-session":
        from .session_compiler import compile_session_file

        receipt = compile_session_file(args.session, args.out_dir, label=args.label)
        print(json.dumps(receipt, indent=2, sort_keys=True))
        return 0

    if args.command == "generate-curriculum":
        from .self_curriculum import generate_self_curriculum_from_compiler_receipt

        receipt = generate_self_curriculum_from_compiler_receipt(
            args.compiled,
            args.out_dir,
            label=args.label,
        )
        print(json.dumps(receipt, indent=2, sort_keys=True))
        return 0

    if args.command == "run-curriculum":
        from .self_curriculum import run_self_curriculum

        report = run_self_curriculum(args.curriculum)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0

    if args.command == "branch-worlds":
        from .branching_worlds import run_branching_worlds_demo

        receipt = run_branching_worlds_demo(args.out_dir)
        print(json.dumps(receipt, indent=2, sort_keys=True))
        return 0

    if args.command == "repair-planner":
        from .repair_planner_demo import run_repair_planner_demo

        receipt = run_repair_planner_demo(args.out_dir)
        print(json.dumps(receipt, indent=2, sort_keys=True))
        return 0

    if args.command == "pack-library":
        from .knowledge_pack_library import run_knowledge_pack_library_demo

        receipt = run_knowledge_pack_library_demo(args.out_dir)
        print(json.dumps(receipt, indent=2, sort_keys=True))
        return 0

    if args.command == "trust-pressure":
        from .trust_pressure import run_trust_pressure_demo

        receipt = run_trust_pressure_demo(args.out_dir)
        print(json.dumps(receipt, indent=2, sort_keys=True))
        return 0

    if args.command == "proof-search":
        from .proof_repair_search import run_proof_repair_search_demo

        receipt = run_proof_repair_search_demo(args.out_dir)
        print(json.dumps(receipt, indent=2, sort_keys=True))
        return 0

    if args.command == "self-audit":
        from .self_audit import run_self_audit_demo

        receipt = run_self_audit_demo(args.out_dir)
        print(json.dumps(receipt, indent=2, sort_keys=True))
        return 0

    if args.command == "v8":
        from .v8_milestone import run_v8_milestone

        receipt = run_v8_milestone(args.out_dir)
        print(json.dumps(receipt, indent=2, sort_keys=True))
        return 0

    if args.command == "v10":
        from .runtime_os_cli import load_json_arg, run_suite_payload

        session = load_json_arg("@" + args.runtime_session)
        exit_code, payload = run_suite_payload(session)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return exit_code

    if args.command == "repair-kernel":
        from .research_os import SelfRepairingReasoningKernel

        payload = SelfRepairingReasoningKernel().audit(args.repo)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    if args.command == "research-os":
        from .research_os import SelfHostingResearchOS

        payload = SelfHostingResearchOS().run(args.mission, args.repo)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload["all_gates_passed"] else 1

    if args.command == "v32-v40":
        from .research_os import write_v32_v40_receipts

        payload = write_v32_v40_receipts(args.out_dir, args.mission, args.repo)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload["all_gates_passed"] else 1

    if args.command == "cognitive-physics":
        from .cognitive_physics_engine import evaluate_cognitive_physics_engine

        payload = evaluate_cognitive_physics_engine(args.question or "Does A resolve to C?")
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload["all_gates_passed"] else 1

    if not args.question:
        parser.error("--question is required unless using the milestone/firewall/chat command")

    coordinator = TensionCoordinator.from_json(args.coupling_matrix) if args.coupling_matrix else None
    output = run_reasoner(args.question, args.premise, tension_coordinator=coordinator)
    trace_path = write_json(output, Path(args.trace))

    print("TS-Reasoner-v0")
    print(f"Question: {output.question}")
    if output.premises:
        print("Premises:")
        for premise in output.premises:
            print(f"  - {premise}")
    print(f"Answer: {output.final_answer}")
    print(f"Selected chain: {output.selected_chain.chain_id}")
    print(f"Global tension: {output.tension_score.global_tension:.4f}")
    if output.tension_score.issues:
        print("Issues:")
        for issue in output.tension_score.issues:
            print(f"  - {issue.kind} at {issue.step_id}: {issue.message}")
    if output.repairs:
        print("Repairs:")
        for repair in output.repairs:
            print(f"  - {repair.issue_kind}: {repair.proposed_text}")
    print(f"Trace: {trace_path}")
    return 0


__all__ = ["main"]


if __name__ == "__main__":
    raise SystemExit(main())
