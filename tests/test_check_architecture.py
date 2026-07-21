"""
Unit tests for tools/check_architecture.py.

Covers absolute imports, from-import syntax, relative imports, allowed
app→kernel direction, forbidden kernel→app, and absent-package handling.
"""

from __future__ import annotations

import ast
from pathlib import Path

from tools.check_architecture import (
    build_import_graph,
    check_authority_import_cycles,
    check_file,
    collect_python_files,
    file_layer,
    find_import_cycles,
    resolve_import_module,
)


def test_file_layer_prefers_longest_prefix():
    assert file_layer("core/kernel/kernel.py") == 3
    assert file_layer("src/thinking_system/kernel/kernel.py") == 3
    assert file_layer("apps/cli/main.py") == 6
    assert file_layer("interface/runtime.py") == 6
    assert file_layer("core/query_processor.py") is None  # unmapped mid-core


def test_valid_kernel_imports(tmp_path: Path):
    kernel_file = tmp_path / "src" / "thinking_system" / "kernel" / "valid_module.py"
    kernel_file.parent.mkdir(parents=True, exist_ok=True)
    kernel_file.write_text(
        "import math\nfrom thinking_system.ir import TSIRDocument\n",
        encoding="utf-8",
    )
    violations = check_file(kernel_file, root_dir=tmp_path)
    assert violations == []


def test_forbidden_kernel_import_from_syntax(tmp_path: Path):
    kernel_file = tmp_path / "src" / "thinking_system" / "kernel" / "bad_module.py"
    kernel_file.parent.mkdir(parents=True, exist_ok=True)
    kernel_file.write_text("from apps.chat import main\n", encoding="utf-8")
    violations = check_file(kernel_file, root_dir=tmp_path)
    assert len(violations) == 1
    assert "AUTHORITY VIOLATION" in violations[0]


def test_forbidden_core_to_app_import_statement(tmp_path: Path):
    core_file = tmp_path / "core" / "kernel" / "bad_core.py"
    core_file.parent.mkdir(parents=True, exist_ok=True)
    core_file.write_text("import interface.chat\n", encoding="utf-8")
    violations = check_file(core_file, root_dir=tmp_path)
    assert len(violations) == 1
    assert "interface.chat" in violations[0]


def test_app_to_core_allowed(tmp_path: Path):
    app_file = tmp_path / "apps" / "cli" / "main.py"
    app_file.parent.mkdir(parents=True, exist_ok=True)
    app_file.write_text(
        "from thinking_system.kernel import TSKernel\nfrom core.kernel import TSKernel as K2\n",
        encoding="utf-8",
    )
    violations = check_file(app_file, root_dir=tmp_path)
    assert violations == []


def test_relative_import_resolved_and_flagged(tmp_path: Path):
    """Relative import of a prohibited module must not be skipped."""
    kernel_file = tmp_path / "core" / "kernel" / "rel_bad.py"
    kernel_file.parent.mkdir(parents=True, exist_ok=True)
    # level=2 from core/kernel → parent of core = escape; module dashboard
    # Better: put under core/kernel and use from ...dashboard (invalid) or
    # absolute via relative within tree: from ... no.
    # Simulate file at src/thinking_system/kernel/x.py importing ..apps
    k2 = tmp_path / "src" / "thinking_system" / "kernel" / "rel_bad.py"
    k2.parent.mkdir(parents=True, exist_ok=True)
    k2.write_text("from ..apps import cli\n", encoding="utf-8")
    violations = check_file(k2, root_dir=tmp_path)
    assert len(violations) == 1
    assert "thinking_system.apps" in violations[0] or "apps" in violations[0]


def test_resolve_from_import_y_syntax():
    node = ast.parse("from core.kernel import TSKernel").body[0]
    assert isinstance(node, ast.ImportFrom)
    mods = resolve_import_module(node, "apps/cli/main.py")
    assert mods == ["core.kernel"]


def test_absent_package_dir_does_not_crash(tmp_path: Path):
    """Search roots that do not exist are skipped; no false success from fiction."""
    files = collect_python_files(root_dir=tmp_path)
    assert files == []
    # Create only an empty packages placeholder with no py files
    (tmp_path / "packages" / "ts-core").mkdir(parents=True)
    files = collect_python_files(root_dir=tmp_path)
    assert files == []


def test_real_repo_kernel_has_no_app_imports():
    """Smoke: current repository kernel tree must pass authority check."""
    root = Path(__file__).resolve().parents[1]
    kernel_dir = root / "core" / "kernel"
    violations: list[str] = []
    for pth in kernel_dir.rglob("*.py"):
        violations.extend(check_file(pth, root_dir=root))
    assert violations == []


def test_find_import_cycles_detects_two_node_cycle():
    graph = {
        "pkg.a": {"pkg.b"},
        "pkg.b": {"pkg.a"},
        "pkg.c": set(),
    }
    cycles = find_import_cycles(graph)
    assert len(cycles) == 1
    assert set(cycles[0]) == {"pkg.a", "pkg.b"}


def test_find_import_cycles_detects_self_loop():
    graph = {"pkg.a": {"pkg.a"}, "pkg.b": set()}
    cycles = find_import_cycles(graph)
    assert cycles == [["pkg.a"]]


def test_authority_cycle_is_reported(tmp_path: Path):
    """Synthetic authority-layer A↔B cycle must surface as IMPORT CYCLE."""
    a = tmp_path / "core" / "kernel" / "mod_a.py"
    b = tmp_path / "core" / "kernel" / "mod_b.py"
    a.parent.mkdir(parents=True, exist_ok=True)
    a.write_text("from core.kernel.mod_b import x\n", encoding="utf-8")
    b.write_text("from core.kernel.mod_a import y\n", encoding="utf-8")

    # build_import_graph + find_import_cycles on these two files
    graph = build_import_graph([a, b], root_dir=tmp_path)
    cycles = find_import_cycles(graph)
    assert any(set(c) == {"core.kernel.mod_a", "core.kernel.mod_b"} for c in cycles)

    # Full authority cycle checker path (search roots under tmp)
    violations = check_authority_import_cycles(root_dir=tmp_path)
    assert any("IMPORT CYCLE" in v for v in violations)


def test_authority_cycle_clean_when_acyclic(tmp_path: Path):
    a = tmp_path / "core" / "kernel" / "leaf.py"
    a.parent.mkdir(parents=True, exist_ok=True)
    a.write_text("import math\n", encoding="utf-8")
    violations = check_authority_import_cycles(root_dir=tmp_path)
    assert violations == []
