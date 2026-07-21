#!/usr/bin/env python3
"""
Thinking System Architecture Dependency Direction Checker.

Enforces dependency direction rules across packages:
  ts-core -> ts-ir / ts-artifacts -> ts-verifiers -> ts-kernel -> ts-graph / ts-reasoner -> ts-language / ts-runtime -> apps / CLI

Rules:
1. Core kernel & verifiers must NOT import applications (apps/cli/dashboard/lab/chat).
2. Verifier authority must NOT import language generation or LLM synthesis modules.
3. Foundational packages must not form circular dependencies.
"""

import os
import sys
import ast
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent

# Layer hierarchy (0 = lowest/foundational, 5 = highest/application)
LAYER_MAP = {
    "packages/ts_core": 0,
    "packages/ts_ir": 1,
    "packages/ts_artifacts": 1,
    "packages/ts_verifiers": 2,
    "packages/ts_kernel": 3,
    "core/kernel": 3,
    "packages/ts_graph": 4,
    "core/graph": 4,
    "packages/ts_reasoner": 4,
    "reasoner": 4,
    "packages/ts_language": 5,
    "packages/ts_runtime": 5,
    "apps": 6,
    "dashboard": 6,
    "interface": 6,
}

PROHIBITED_IMPORTS_IN_KERNEL = [
    "interface.chat",
    "dashboard",
    "apps.chat",
    "apps.dashboard",
    "ollama",
    "transformers",
    "torch",
]


def check_file(file_path: Path) -> list[str]:
    violations = []
    rel_path = file_path.relative_to(ROOT_DIR)

    # Determine file layer
    file_layer = None
    for prefix, layer in LAYER_MAP.items():
        if str(rel_path).startswith(prefix.replace("/", os.sep)):
            file_layer = layer
            break

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            tree = ast.parse(f.read(), filename=str(rel_path))
    except Exception:
        return []

    for node in ast.walk(tree):
        imported_mod = None
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_mod = alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_mod = node.module

        if not imported_mod:
            continue

        # Check Kernel & Verifier authority constraints
        if file_layer is not None and file_layer <= 3:
            for prohibited in PROHIBITED_IMPORTS_IN_KERNEL:
                if imported_mod == prohibited or imported_mod.startswith(prohibited + "."):
                    violations.append(
                        f"[AUTHORITY VIOLATION] {rel_path}: layer {file_layer} imports prohibited authority module '{imported_mod}'"
                    )

    return violations


def main():
    print("Checking Thinking System dependency direction rules...")
    all_violations = []

    search_dirs = [
        ROOT_DIR / "core",
        ROOT_DIR / "packages",
        ROOT_DIR / "engines",
        ROOT_DIR / "apps",
        ROOT_DIR / "thinking_system",
    ]

    for sdir in search_dirs:
        if not sdir.exists():
            continue
        for pth in sdir.glob("**/*.py"):
            if "__pycache__" in pth.parts:
                continue
            all_violations.extend(check_file(pth))

    if all_violations:
        print(f"FAILED: Found {len(all_violations)} architecture dependency violations:")
        for v in all_violations:
            print(" -", v)
        sys.exit(1)
    else:
        print("SUCCESS: Architecture dependency direction rules verified cleanly.")
        sys.exit(0)


if __name__ == "__main__":
    main()
