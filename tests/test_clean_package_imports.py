"""
Regression: canonical package imports and runtime symbols must not disappear.

Covers:
  - thinking_system top-level + kernel + CLI module presence
  - package-level CLI re-exports (no RecursionError cold path)
  - runtime construction symbols (explicit imports, not lazy core.__getattr__)
  - legacy BoggersTheAI compatibility surface
"""

from __future__ import annotations

import importlib
import importlib.util
import sys


def test_thinking_system_package_imports():
    import thinking_system
    from thinking_system.artifacts import TSReceipt
    from thinking_system.engines.bogvm import execute_bogvm_assembly
    from thinking_system.graph import UniversalLivingGraph
    from thinking_system.ir import TSIRDocument
    from thinking_system.kernel import TSKernel
    from thinking_system.reasoner import TSEngine
    from thinking_system.verifiers import SafeArithmeticEvaluator

    assert thinking_system.__version__ == "0.5.0-alpha.1"
    assert TSKernel is not None
    assert TSIRDocument is not None
    assert TSReceipt is not None
    assert SafeArithmeticEvaluator is not None
    assert UniversalLivingGraph is not None
    assert TSEngine is not None
    assert execute_bogvm_assembly is not None


def test_canonical_cli_module_exists():
    assert importlib.util.find_spec("thinking_system.apps.cli.main") is not None
    from thinking_system.apps.cli.main import (
        main,
        run_legacy_chat,
        run_legacy_dashboard,
    )

    assert callable(main)
    assert callable(run_legacy_chat)
    assert callable(run_legacy_dashboard)


def _purge_cli_modules() -> None:
    for key in list(sys.modules):
        if key == "thinking_system.apps.cli" or key.startswith(
            "thinking_system.apps.cli."
        ):
            del sys.modules[key]


def test_canonical_cli_package_cold_import_no_recursion():
    """
    Cold import of thinking_system.apps.cli must not RecursionError.

    Historical bug: package __getattr__ used ``from . import main`` which
    re-entered __getattr__ when resolving the name ``main``.
    """
    _purge_cli_modules()

    cli_pkg = importlib.import_module("thinking_system.apps.cli")
    # Package-level helpers re-exported from .main
    assert callable(cli_pkg.run_legacy_chat)
    assert callable(cli_pkg.run_legacy_dashboard)

    # Callable lives on the submodule (standard layout; name ``main`` is the module)
    main_mod = importlib.import_module("thinking_system.apps.cli.main")
    assert callable(main_mod.main)


def test_canonical_cli_from_package_import_helpers():
    """from thinking_system.apps.cli import run_legacy_* must work cold."""
    _purge_cli_modules()
    from thinking_system.apps.cli import run_legacy_chat, run_legacy_dashboard

    assert callable(run_legacy_chat)
    assert callable(run_legacy_dashboard)


def test_canonical_cli_submodule_main_callable():
    """from thinking_system.apps.cli.main import main is the supported callable path."""
    _purge_cli_modules()
    from thinking_system.apps.cli.main import main

    assert callable(main)


def test_runtime_construction_symbols_are_importable():
    """These symbols previously vanished during a partial import rewrite."""
    from core.query_processor import QueryAdapters, QueryProcessor, QueryResponse
    from core.router import QueryRouter, RegistryIngestAdapter, RouterConfig
    from interface.runtime import BoggersRuntime, RuntimeConfig

    assert QueryAdapters is not None
    assert QueryProcessor is not None
    assert QueryResponse is not None
    assert QueryRouter is not None
    assert RegistryIngestAdapter is not None
    assert RouterConfig is not None
    assert BoggersRuntime is not None
    assert RuntimeConfig is not None


def test_legacy_boggerstheai_package_imports():
    import BoggersTheAI
    from BoggersTheAI.core.kernel import TSKernel as LegacyTSKernel
    from core.kernel import TSKernel as CoreTSKernel

    assert BoggersTheAI is not None
    assert LegacyTSKernel is not None
    assert CoreTSKernel is not None
    assert LegacyTSKernel is CoreTSKernel or LegacyTSKernel.__name__ == "TSKernel"
