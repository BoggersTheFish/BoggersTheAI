# Lazy imports to reduce tension in module dependency graph (TS theory: eager loading creates high tension on circular/relative imports; relax by on-demand)
def __getattr__(name):
    if name == 'UniversalLivingGraph':
        from .graph.universal_living_graph import UniversalLivingGraph
        return UniversalLivingGraph
    if name == 'QueryProcessor':
        from .query_processor import QueryProcessor
        return QueryProcessor
    # Add more as needed for Wave 0 unification
    if name == 'VerifierOS':
        from .verifier.verifier_os import VerifierOS
        return VerifierOS
    if name == 'TSLCCompiler':
        from .language.tslc import TSLCCompiler
        return TSLCCompiler
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "Edge",
    "EventBus",
    "GraphProtocol",
    "HealthChecker",
    "ImageInProtocol",
    "InferenceProtocol",
    "IngestProtocol",
    "MetricsCollector",
    "Mode",
    "ModeManager",
    "Node",
    "PluginRegistry",
    "QueryAdapters",
    "QueryProcessor",
    "QueryRouter",
    "QueryResponse",
    "RegistryIngestAdapter",
    "RouterConfig",
    "Tension",
    "ToolProtocol",
    "UniversalLivingGraph",
    "VoiceInProtocol",
    "VoiceOutProtocol",
    "WaveResult",
    "adapter_plugins",
    "apply_yaml_to_config",
    "break_weakest",
    "bus",
    "evolve",
    "find_config",
    "get_logger",
    "health_checker",
    "load_and_apply",
    "load_yaml",
    "resolve_nested",
    "metrics",
    "process_query",
    "propagate",
    "relax",
    "run_wave",
    "validate_config",
    "setup_logging",
    "tool_plugins",
]
