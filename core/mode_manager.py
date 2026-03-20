from __future__ import annotations

import threading
from enum import Enum


class Mode(str, Enum):
    AUTO = "AUTO"
    USER = "USER"


class ModeManager:
    def __init__(self) -> None:
        self._mode = Mode.AUTO
        self._cycle_active = False
        self._user_requested = False
        self._condition = threading.Condition()

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
            if self._user_requested:
                self._mode = Mode.USER
            self._condition.notify_all()

    def request_user_mode(self) -> None:
        with self._condition:
            self._user_requested = True
            while self._cycle_active:
                self._condition.wait()
            self._mode = Mode.USER

    def release_to_auto(self) -> None:
        with self._condition:
            self._user_requested = False
            self._mode = Mode.AUTO
            self._condition.notify_all()
