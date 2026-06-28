"""TensionForge — OpenCL runtime for tension-field neural execution.

Upstream: https://github.com/BoggersTheFish/TensionForge
Integrated into the BoggersTheAI monorepo inference layer with .bogpk artifact emission.
"""

from .bogpk_runtime import TensionForgeRuntime as BogpkTensionForgeRuntime
from .bogpk_runtime import is_opencl_available

try:
    from .device import DeviceInfo, find_opencl_device
    from .runtime import TensionForgeRuntime
    from .tensor import DeviceTensor
except ImportError:
    DeviceInfo = None  # type: ignore[misc, assignment]
    DeviceTensor = None  # type: ignore[misc, assignment]
    TensionForgeRuntime = BogpkTensionForgeRuntime  # type: ignore[misc, assignment]

    def find_opencl_device(*_args, **_kwargs):  # type: ignore[misc]
        return None


__all__ = [
    "BogpkTensionForgeRuntime",
    "DeviceInfo",
    "DeviceTensor",
    "TensionForgeRuntime",
    "find_opencl_device",
    "is_opencl_available",
]

__version__ = "0.2.0a0"
