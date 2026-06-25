from __future__ import annotations

import hashlib
from collections.abc import Sequence

import numpy as np
import pyopencl as cl

from .device import (
    DeviceInfo,
    describe_device,
    find_opencl_device,
)


class TensionForgeRuntime:
    def __init__(
        self,
        *,
        platform_contains: str = "rusticl",
        device_contains: str = "radeon",
        profiling: bool = True,
    ) -> None:
        self.platform, self.device = find_opencl_device(
            platform_contains=platform_contains,
            device_contains=device_contains,
            require_gpu=True,
        )

        self.info: DeviceInfo = describe_device(
            self.platform,
            self.device,
        )

        self.context = cl.Context([self.device])

        queue_properties = 0

        if profiling:
            queue_properties |= (
                cl.command_queue_properties.PROFILING_ENABLE
            )

        self.profiling = profiling

        self.queue = cl.CommandQueue(
            self.context,
            properties=queue_properties,
        )

        self._program_cache: dict[
            tuple[str, tuple[str, ...]],
            cl.Program,
        ] = {}

        self._kernel_cache: dict[
            tuple[str, tuple[str, ...], str],
            cl.Kernel,
        ] = {}

        self.kernel_launch_count = 0
        self.host_to_device_bytes = 0
        self.device_to_host_bytes = 0

    @property
    def program_cache_size(self) -> int:
        return len(self._program_cache)

    @property
    def kernel_cache_size(self) -> int:
        return len(self._kernel_cache)

    @staticmethod
    def source_hash(source: str) -> str:
        return hashlib.sha256(
            source.encode("utf-8")
        ).hexdigest()

    @staticmethod
    def round_up(
        value: int,
        multiple: int,
    ) -> int:
        if multiple <= 0:
            raise ValueError(
                "multiple must be greater than zero"
            )

        return (
            (value + multiple - 1)
            // multiple
            * multiple
        )

    def compile_program(
        self,
        source: str,
        *,
        options: Sequence[str] = (),
    ) -> cl.Program:
        options_tuple = tuple(options)
        source_digest = self.source_hash(source)

        cache_key = (
            source_digest,
            options_tuple,
        )

        cached = self._program_cache.get(
            cache_key
        )

        if cached is not None:
            return cached

        try:
            program = cl.Program(
                self.context,
                source,
            ).build(
                options=list(options_tuple),
            )
        except Exception as exc:
            raise RuntimeError(
                "OpenCL program compilation failed.\n"
                f"Device: {self.info.device_name}\n"
                f"Source SHA-256: {source_digest}\n"
                f"Build options: {options_tuple}"
            ) from exc

        self._program_cache[cache_key] = program
        return program

    def kernel(
        self,
        source: str,
        kernel_name: str,
        *,
        options: Sequence[str] = (),
    ) -> cl.Kernel:
        options_tuple = tuple(options)
        source_digest = self.source_hash(source)

        cache_key = (
            source_digest,
            options_tuple,
            kernel_name,
        )

        cached = self._kernel_cache.get(
            cache_key
        )

        if cached is not None:
            return cached

        program = self.compile_program(
            source,
            options=options_tuple,
        )

        try:
            kernel = cl.Kernel(
                program,
                kernel_name,
            )
        except Exception as exc:
            raise RuntimeError(
                "Could not load OpenCL kernel "
                f"{kernel_name!r}."
            ) from exc

        self._kernel_cache[cache_key] = kernel
        return kernel

    def buffer_from_host(
        self,
        array: np.ndarray,
        *,
        access: str = "read_only",
    ) -> cl.Buffer:
        contiguous = np.ascontiguousarray(array)

        access_flags = {
            "read_only": cl.mem_flags.READ_ONLY,
            "write_only": cl.mem_flags.WRITE_ONLY,
            "read_write": cl.mem_flags.READ_WRITE,
        }

        if access not in access_flags:
            raise ValueError(
                "access must be read_only, "
                "write_only, or read_write"
            )

        if contiguous.nbytes > (
            self.info.max_allocation_bytes
        ):
            raise MemoryError(
                "Requested OpenCL allocation exceeds "
                "the device's maximum single-buffer "
                "allocation.\n"
                f"Requested: {contiguous.nbytes} bytes\n"
                "Maximum:   "
                f"{self.info.max_allocation_bytes} bytes"
            )

        buffer = cl.Buffer(
            self.context,
            access_flags[access]
            | cl.mem_flags.COPY_HOST_PTR,
            hostbuf=contiguous,
        )
        self.host_to_device_bytes += contiguous.nbytes
        return buffer

    def empty_buffer(
        self,
        nbytes: int,
        *,
        access: str = "read_write",
    ) -> cl.Buffer:
        if nbytes <= 0:
            raise ValueError(
                "Buffer size must be positive"
            )

        if nbytes > self.info.max_allocation_bytes:
            raise MemoryError(
                "Requested OpenCL allocation exceeds "
                "the device's maximum single-buffer "
                "allocation.\n"
                f"Requested: {nbytes} bytes\n"
                "Maximum:   "
                f"{self.info.max_allocation_bytes} bytes"
            )

        access_flags = {
            "read_only": cl.mem_flags.READ_ONLY,
            "write_only": cl.mem_flags.WRITE_ONLY,
            "read_write": cl.mem_flags.READ_WRITE,
        }

        if access not in access_flags:
            raise ValueError(
                "access must be read_only, "
                "write_only, or read_write"
            )

        return cl.Buffer(
            self.context,
            access_flags[access],
            size=nbytes,
        )

    def read_buffer(
        self,
        destination: np.ndarray,
        source: cl.Buffer,
    ) -> np.ndarray:
        cl.enqueue_copy(
            self.queue,
            destination,
            source,
        ).wait()

        self.device_to_host_bytes += destination.nbytes

        return destination

    def write_buffer(
        self,
        destination: cl.Buffer,
        source: np.ndarray,
    ) -> None:
        contiguous = np.ascontiguousarray(source)

        cl.enqueue_copy(
            self.queue,
            destination,
            contiguous,
        ).wait()
        self.host_to_device_bytes += contiguous.nbytes

    def run_kernel(
        self,
        kernel: cl.Kernel,
        *,
        global_size: tuple[int, ...],
        local_size: tuple[int, ...] | None,
        arguments: Sequence[object],
    ) -> float | None:
        kernel.set_args(*arguments)

        event = cl.enqueue_nd_range_kernel(
            self.queue,
            kernel,
            global_size,
            local_size,
        )

        self.kernel_launch_count += 1

        event.wait()

        if not self.profiling:
            return None

        elapsed_nanoseconds = (
            event.profile.end
            - event.profile.start
        )

        return elapsed_nanoseconds * 1e-6

    def finish(self) -> None:
        self.queue.finish()

    def counters(self) -> dict[str, int]:
        return {
            "kernel_launches": self.kernel_launch_count,
            "host_to_device_bytes": self.host_to_device_bytes,
            "device_to_host_bytes": self.device_to_host_bytes,
        }

    def reset_counters(self) -> None:
        self.kernel_launch_count = 0
        self.host_to_device_bytes = 0
        self.device_to_host_bytes = 0
