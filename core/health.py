from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, List

logger = logging.getLogger("boggers.health")

HealthCheck = Callable[[], Dict[str, Any]]


class HealthChecker:
    def __init__(self) -> None:
        self._checks: Dict[str, HealthCheck] = {}

    def register(self, name: str, check: HealthCheck) -> None:
        self._checks[name] = check

    def run_all(self) -> Dict[str, Any]:
        results: Dict[str, Any] = {}
        for name, check in self._checks.items():
            start = time.time()
            try:
                result = check()
                result["duration_ms"] = round((time.time() - start) * 1000, 1)
                result["healthy"] = True
                results[name] = result
            except Exception as exc:
                results[name] = {
                    "healthy": False,
                    "error": str(exc),
                    "duration_ms": round((time.time() - start) * 1000, 1),
                }
        all_healthy = all(r.get("healthy", False) for r in results.values())
        return {"overall": "healthy" if all_healthy else "degraded", "checks": results}

    def names(self) -> List[str]:
        return list(self._checks.keys())


health_checker = HealthChecker()
