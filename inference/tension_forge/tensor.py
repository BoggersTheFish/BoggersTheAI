from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
import pyopencl as cl

if TYPE_CHECKING:
    from tensionforge.runtime import TensionForgeRuntime


@dataclass
class DeviceTensor:
    runtime: TensionForgeRuntime
    shape: tuple[int, ...]
    dtype: np.dtype
    buffer: cl.Buffer

    @classmethod
    def from_numpy(
        cls,
        runtime: TensionForgeRuntime,
        array: np.ndarray,
        *,
        access: str = "read_write",
    ) -> DeviceTensor:
        host_array = np.ascontiguousarray(array)

        if host_array.size == 0:
            raise ValueError(
                "DeviceTensor cannot contain zero elements"
            )

        buffer = runtime.buffer_from_host(
            host_array,
            access=access,
        )

        return cls(
            runtime=runtime,
            shape=tuple(host_array.shape),
            dtype=host_array.dtype,
            buffer=buffer,
        )

    @classmethod
    def empty(
        cls,
        runtime: TensionForgeRuntime,
        shape: tuple[int, ...],
        *,
        dtype: np.dtype | type = np.float32,
        access: str = "read_write",
    ) -> DeviceTensor:
        if not shape:
            raise ValueError(
                "DeviceTensor shape cannot be empty"
            )

        if any(dimension <= 0 for dimension in shape):
            raise ValueError(
                "Every DeviceTensor dimension must be positive"
            )

        resolved_dtype = np.dtype(dtype)

        element_count = int(
            np.prod(
                shape,
                dtype=np.int64,
            )
        )

        nbytes = element_count * resolved_dtype.itemsize

        buffer = runtime.empty_buffer(
            nbytes,
            access=access,
        )

        return cls(
            runtime=runtime,
            shape=tuple(shape),
            dtype=resolved_dtype,
            buffer=buffer,
        )

    @property
    def ndim(self) -> int:
        return len(self.shape)

    @property
    def size(self) -> int:
        return int(
            np.prod(
                self.shape,
                dtype=np.int64,
            )
        )

    @property
    def nbytes(self) -> int:
        return self.size * self.dtype.itemsize

    def to_numpy(self) -> np.ndarray:
        destination = np.empty(
            self.shape,
            dtype=self.dtype,
        )

        self.runtime.read_buffer(
            destination,
            self.buffer,
        )

        return destination

    def copy_from(
        self,
        array: np.ndarray,
    ) -> None:
        source = np.ascontiguousarray(array)

        if tuple(source.shape) != self.shape:
            raise ValueError(
                "Source shape does not match DeviceTensor. "
                f"Expected {self.shape}, received "
                f"{tuple(source.shape)}"
            )

        if source.dtype != self.dtype:
            raise ValueError(
                "Source dtype does not match DeviceTensor. "
                f"Expected {self.dtype}, received "
                f"{source.dtype}"
            )

        self.runtime.write_buffer(
            self.buffer,
            source,
        )
