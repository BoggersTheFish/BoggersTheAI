"""TensionForge — OpenCL runtime for tension-field neural execution."""

from .runtime import TensionForgeRuntime, is_opencl_available

__all__ = ["TensionForgeRuntime", "is_opencl_available"]