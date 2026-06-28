from __future__ import annotations

import logging
import threading
import time
from enum import Enum

logger = logging.getLogger("boggers.mode_manager")


class Mode(str, Enum):
    AUTO = "AUTO"
    USER = "USER"


class ModeManager:
    def __init__(self) -> None:
        self._mode = Mode.AUTO
        self._cycle_active = False
        self._user_requested = False
        self._condition = threading.Condition()
        self.last_cycle_completed_time = time.time()
        self._wave_health_ok = True

    def get_mode(self) -> Mode:
        with self._condition:
            return self._mode

    def begin_cycle(self) -> bool:
        with self._condition:
            if self._cycle_active or self._mode != Mode.AUTO:
                return False
            self._cycle_active = True
            return True

    def end_cycle(self) -> None:
        with self._condition:
            self._cycle_active = False
            self.last_cycle_completed_time = time.time()
            if self._user_requested:
                self._mode = Mode.USER
            self._condition.notify_all()

    def request_user_mode(self, timeout: float = 30.0) -> bool:
        with self._condition:
            self._user_requested = True
            end_time = time.monotonic() + timeout
            while self._cycle_active:
                remaining = max(0.0, end_time - time.monotonic())
                if remaining <= 0:
                    logger.warning("request_user_mode timed out after %.2fs. Forcing USER mode takeover.", timeout)
                    self._mode = Mode.USER
                    self._cycle_active = False
                    self._user_requested = False
                    self._condition.notify_all()
                    return False
                if not self._condition.wait(timeout=remaining):
                    logger.warning("request_user_mode wait timed out. Forcing USER mode takeover.")
                    self._mode = Mode.USER
                    self._cycle_active = False
                    self._user_requested = False
                    self._condition.notify_all()
                    return False
            self._mode = Mode.USER
            return True

    def release_to_auto(self) -> None:
        with self._condition:
            self._user_requested = False
            self._mode = Mode.AUTO
            self.last_cycle_completed_time = time.time()
            self._condition.notify_all()

    def check_wave_health(self, interval_seconds: float) -> bool:
        """Returns True if the background wave cycle is running and healthy.
        If in AUTO mode and no cycle has completed in > 2 * interval_seconds, returns False.
        """
        with self._condition:
            if self._mode != Mode.AUTO:
                return True
            elapsed = time.time() - self.last_cycle_completed_time
            limit = max(60.0, 2.0 * interval_seconds)
            self._wave_health_ok = (elapsed <= limit)
            if not self._wave_health_ok:
                logger.warning(
                    "Wave cycle has not completed in %.2fs (limit is %.2fs). Wave health degraded.",
                    elapsed,
                    limit
                )
            return self._wave_health_ok
