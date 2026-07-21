#!/usr/bin/env python3
"""
Thinking System Architecture Dependency Direction Checker.

Enforces a practical subset of dependency rules on the *current* layout:

1. Kernel/verifier authority layers (core/kernel, thinking_system.kernel,
   verifiers) must NOT import application modules (apps, dashboard, chat UI,
   thinking_system.apps).
2. Those authority layers must NOT import heavy LLM stacks (ollama,
   transformers, torch).
3. Relative imports are resolved against the file's package path so they are
   not silently skipped.
4. Absent package directories do not cause a free pass — only real .py files
   under configured search roots are scanned.

This is intentionally narrower than a full layer DAG / cycle prover. Do not
document it as proving complete monorepo package boundaries.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent

# Path prefixes (posix-style relative to repo root) → authority layer.
# Lower numbers = more foundational. Only layers <= 3 get denylist checks.
LAYER_MAP: dict[str, int] = {
    "src/thinking_system/core": 0,
    "src/thinking_system/ir": 1,
    "src/thinking_system/artifacts": 1,
    "src/thinking_system/verifiers": 2,
    "core/verifier": 2,
    "src/thinking_system/kernel": 3,
    "core/kernel": 3,
    "src/thinking_system/graph": 4,
    "core/graph": 4,
    "src/thinking_system/reasoner": 4,
    "reasoner": 4,
    "src/thinking_system/language": 5,
    "src/thinking_system/runtime": 5,
    "src/thinking_system/apps": 6,
    "apps": 6,
    "dashboard": 6,
    "interface": 6,
}

PROHIBITED_IMPORTS_IN_KERNEL = (
    "interface.chat",
    "dashboard",
    "apps.chat",
    "apps.dashboard",
    "apps.lab",
    "thinking_system.apps",
    "ollama",
    "transformers",
    "torch",
)

SEARCH_DIRS = (
    "src",
    "apps",
    "core",
    "interface",
    "dashboard",
    "packages",
    "engines",
)


def _posix_rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def file_layer(rel_str: str) -> int | None:
    """Return layer for a repo-relative posix path, or None if unmapped."""
    best: tuple[int, int] | None = None  # (prefix_len, layer)
    for prefix, layer in LAYER_MAP.items():
        if rel_str == prefix or rel_str.startswith(prefix + "/"):
            plen = len(prefix)
            if best is None or plen > best[0]:
                best = (plen, layer)
    return best[1] if best else None


def _package_parts_for_file(file_rel: str) -> list[str]:
    """Map a repo-relative file path to dotted package parts (excluding module)."""
    parts = list(Path(file_rel).with_suffix("").parts)
    if not parts:
        return []
    # Strip src/ layout prefix so src/thinking_system/kernel/x.py → thinking_system.kernel
    if parts[0] == "src" and len(parts) > 1:
        parts = parts[1:]
    # Drop module file name
    return parts[:-1]


def resolve_import_module(
    node: ast.ImportFrom | ast.Import,
    file_rel: str,
) -> list[str]:
    """Return fully-qualified module names referenced by an import node."""
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names if alias.name]

    if not isinstance(node, ast.ImportFrom):
        return []

    # Absolute: from x.y import z  → module x.y
    if node.level == 0:
        return [node.module] if node.module else []

    # Relative: resolve against containing package of the file.
    # file: core/kernel/kernel.py → package parts core.kernel
    pkg_parts = _package_parts_for_file(file_rel)
    # level=1 → current package; level=2 → parent, etc.
    up = node.level - 1
    if up > len(pkg_parts):
        base: list[str] = []
    elif up:
        base = pkg_parts[: len(pkg_parts) - up]
    else:
        base = pkg_parts

    if node.module:
        resolved = ".".join([*base, *node.module.split(".")]) if base else node.module
    else:
        resolved = ".".join(base) if base else ""
    return [resolved] if resolved else []


def is_prohibited(imported_mod: str) -> str | None:
    for prohibited in PROHIBITED_IMPORTS_IN_KERNEL:
        if imported_mod == prohibited or imported_mod.startswith(prohibited + "."):
            return prohibited
    return None


def check_file(file_path: Path, root_dir: Path | None = None) -> list[str]:
    """Return architecture violation strings for a single Python file."""
    base_dir = root_dir or ROOT_DIR
    rel_str = _posix_rel(file_path, base_dir)
    layer = file_layer(rel_str)
    violations: list[str] = []

    try:
        source = file_path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(source, filename=rel_str)
    except SyntaxError:
        return []
    except OSError:
        return []

    if layer is None or layer > 3:
        # Only authority layers are denylisted today.
        return []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        for imported_mod in resolve_import_module(node, rel_str):
            hit = is_prohibited(imported_mod)
            if hit:
                violations.append(
                    f"[AUTHORITY VIOLATION] {rel_str}: layer {layer} "
                    f"imports prohibited module '{imported_mod}' (matched '{hit}')"
                )
    return violations


def collect_python_files(root_dir: Path | None = None) -> list[Path]:
    base = root_dir or ROOT_DIR
    files: list[Path] = []
    for name in SEARCH_DIRS:
        sdir = base / name
        if not sdir.is_dir():
            continue
        for pth in sdir.rglob("*.py"):
            if "__pycache__" in pth.parts:
                continue
            files.append(pth)
    return files


def main() -> int:
    print("Checking Thinking System dependency direction rules...")
    print("(Authority denylist for kernel/verifier layers; not a full package DAG.)")
    all_violations: list[str] = []
    for pth in collect_python_files():
        all_violations.extend(check_file(pth))

    if all_violations:
        print(
            f"FAILED: Found {len(all_violations)} architecture dependency violations:"
        )
        for v in all_violations:
            print(" -", v)
        return 1

    print("SUCCESS: Architecture authority rules verified cleanly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
