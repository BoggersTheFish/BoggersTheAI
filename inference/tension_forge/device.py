from __future__ import annotations

from dataclasses import asdict, dataclass

import pyopencl as cl


@dataclass(frozen=True)
class DeviceInfo:
    platform_name: str
    platform_vendor: str
    device_name: str
    device_vendor: str
    driver_version: str
    opencl_version: str
    compute_units: int
    global_memory_bytes: int
    max_allocation_bytes: int
    max_clock_mhz: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def find_opencl_device(
    *,
    platform_contains: str = "rusticl",
    device_contains: str = "radeon",
    require_gpu: bool = True,
) -> tuple[cl.Platform, cl.Device]:
    platform_query = platform_contains.lower()
    device_query = device_contains.lower()

    discovered: list[str] = []

    for platform in cl.get_platforms():
        for device in platform.get_devices():
            discovered.append(
                f"{platform.name}: {device.name}"
            )

            if (
                platform_query
                and platform_query not in platform.name.lower()
            ):
                continue

            if (
                device_query
                and device_query not in device.name.lower()
            ):
                continue

            if require_gpu:
                is_gpu = bool(
                    device.type & cl.device_type.GPU
                )

                if not is_gpu:
                    continue

            return platform, device

    discovered_text = "\n".join(
        f"  - {item}"
        for item in discovered
    )

    raise RuntimeError(
        "No matching OpenCL device was found.\n"
        f"Requested platform containing: {platform_contains!r}\n"
        f"Requested device containing:   {device_contains!r}\n"
        "Discovered devices:\n"
        f"{discovered_text or '  - none'}"
    )


def describe_device(
    platform: cl.Platform,
    device: cl.Device,
) -> DeviceInfo:
    return DeviceInfo(
        platform_name=str(platform.name),
        platform_vendor=str(platform.vendor),
        device_name=str(device.name),
        device_vendor=str(device.vendor),
        driver_version=str(device.driver_version),
        opencl_version=str(device.version),
        compute_units=int(device.max_compute_units),
        global_memory_bytes=int(device.global_mem_size),
        max_allocation_bytes=int(
            device.max_mem_alloc_size
        ),
        max_clock_mhz=int(
            device.max_clock_frequency
        ),
    )
