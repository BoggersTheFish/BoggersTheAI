"""NebulaGraph / Redis / Spark hooks for GOAT-TS constraint resolution.

These hooks expose the graph substrate to external stores while keeping
verifier-gated acceptance as the proof boundary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class GraphStoreConfig:
    """Configuration for reasoner graph-store hooks."""

    nebula_host: str = "127.0.0.1"
    nebula_port: int = 9669
    nebula_space: str = "ts_os"
    redis_url: str = "redis://127.0.0.1:6379/0"
    spark_master: str = "local[*]"
    artifacts_dir: Path = field(default_factory=lambda: Path("artifacts/reasoner"))


class NebulaGraphHook:
    """NebulaGraph connector for constraint-graph persistence."""

    def __init__(self, config: GraphStoreConfig) -> None:
        self.config = config

    def connect(self) -> Any:
        try:
            from nebula3.Config import Config
            from nebula3.gclient.net import ConnectionPool

            cfg = Config()
            pool = ConnectionPool()
            ok = pool.init([(self.config.nebula_host, self.config.nebula_port)], cfg)
            if not ok:
                raise ConnectionError("NebulaGraph connection pool init failed")
            return pool
        except ImportError as exc:
            raise ImportError(
                "nebula3-python required for NebulaGraph hooks: pip install nebula3-python"
            ) from exc

    def ensure_space(self, pool: Any) -> None:
        session = pool.get_session("root", "nebula")
        session.execute(f"CREATE SPACE IF NOT EXISTS {self.config.nebula_space}")
        session.release()


class RedisHook:
    """Redis cache for hot constraint-graph activations and receipt indices."""

    def __init__(self, config: GraphStoreConfig) -> None:
        self.config = config

    def connect(self) -> Any:
        try:
            import redis

            return redis.from_url(self.config.redis_url)
        except ImportError as exc:
            raise ImportError("redis package required: pip install redis") from exc

    def cache_receipt_key(self, receipt_id: str) -> str:
        return f"ts-os:receipt:{receipt_id}"


class SparkHook:
    """Spark batch hook for large-scale graph ingestion and metacompute."""

    def __init__(self, config: GraphStoreConfig) -> None:
        self.config = config

    def session(self) -> Any:
        try:
            from pyspark.sql import SparkSession

            return (
                SparkSession.builder.master(self.config.spark_master)
                .appName("TS-OS-Reasoner")
                .getOrCreate()
            )
        except ImportError as exc:
            raise ImportError(
                "pyspark required for Spark hooks: pip install pyspark"
            ) from exc
