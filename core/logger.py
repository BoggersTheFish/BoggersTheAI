from __future__ import annotations

import logging
import sys


def get_logger(name: str = "boggers") -> logging.Logger:
    return logging.getLogger(name)


def setup_logging(level: int = logging.INFO, fmt: str | None = None) -> None:
    root = logging.getLogger("boggers")
    if root.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt or "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root.addHandler(handler)
    root.setLevel(level)


setup_logging()
