# Lazy imports to reduce tension in module dependency graph (TS theory: eager loading creates high tension on circular/relative imports; relax by on-demand)
def __getattr__(name):
    if name == 'UniversalLivingGraph':
        from .graph.universal_living_graph import UniversalLivingGraph
        return UniversalLivingGraph
    if name == 'QueryProcessor':
        from .query_processor import QueryProcessor
        return QueryProcessor
    if name == 'VerifierOS':
        from .verifier.verifier_os import VerifierOS
        return VerifierOS
    if name == 'TSLCCompiler':
        from .language.tslc import TSLCCompiler
        return TSLCCompiler
    if name == 'ModeManager':
        from .mode_manager import ModeManager
        return ModeManager
    if name == 'QueryAdapters':
        from .query_processor import QueryAdapters
        return QueryAdapters
    if name == 'QueryRouter':
        from .router import QueryRouter
        return QueryRouter
    if name == 'RouterConfig':
        from .router import RouterConfig
        return RouterConfig
    if name == 'RegistryIngestAdapter':
        from .router import RegistryIngestAdapter
        return RegistryIngestAdapter
    if name == 'Edge':
        from .types import Edge
        return Edge
    if name == 'Node':
        from .types import Node
        return Node
    if name == 'EventBus':
        from .events import EventBus
        return EventBus
    if name == 'bus':
        from .events import bus
        return bus
    if name == 'health_checker':
        from .health import health_checker
        return health_checker
    if name == 'metrics':
        from .metrics import metrics
        return metrics
    if name == 'adapter_plugins':
        from .plugins import adapter_plugins
        return adapter_plugins
    if name == 'tool_plugins':
        from .plugins import tool_plugins
        return tool_plugins
    if name == 'Mode':
        from .mode_manager import Mode
        return Mode
    if name == 'QueryResponse':
        from .query_processor import QueryResponse
        return QueryResponse
    if name == 'Tension':
        from .types import Tension
        return Tension
    if name == 'WaveResult':
        from .wave import WaveResult
        return WaveResult
    if name == 'PluginRegistry':
        from .plugins import PluginRegistry
        return PluginRegistry
    if name == 'HealthChecker':
        from .health import HealthChecker
        return HealthChecker
    # Add more lazy as needed to support imports without tension
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
