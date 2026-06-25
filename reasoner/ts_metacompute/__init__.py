"""TS-Metacompute deterministic substrate readers.

Substrates in this package may expose tension, coherence, and repair signals.
They do not accept truth. Typed verifier layers remain the proof authority.
"""

from .scheduler import MetacomputeScheduler, SchedulerTask

__all__ = ["MetacomputeScheduler", "SchedulerTask"]
