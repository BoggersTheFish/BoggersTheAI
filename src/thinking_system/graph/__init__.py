"""
Universal living graph & wave runner dynamics (`thinking_system.graph`).
"""

# COMPATIBILITY_FACADE: re-exports implementation from legacy top-level packages.


from core.graph.universal_living_graph import UniversalLivingGraph
from core.graph.wave_runner import WaveConfig, WaveCycleRunner

__all__ = ["UniversalLivingGraph", "WaveConfig", "WaveCycleRunner"]
