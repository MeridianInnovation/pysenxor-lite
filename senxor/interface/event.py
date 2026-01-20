# Copyright (c) 2025-2026 Meridian Innovation. All rights reserved.
from __future__ import annotations

import queue
import threading
from typing import TYPE_CHECKING, Callable, Generic, ParamSpec

if TYPE_CHECKING:
    from senxor.log import SenxorLogger

P = ParamSpec("P")


class Notifier(threading.Thread):
    def __init__(self, logger: SenxorLogger | None = None):
        self.logger = logger
        super().__init__()
        self.task_queue = queue.Queue[tuple[Callable, tuple, dict]]()
        self.daemon = True
        self.running = True
        self.is_started = False

    def run(self):
        while self.running:
            try:
                task = self.task_queue.get(timeout=1)
                self.process_notification(task)
                self.task_queue.task_done()
            except queue.Empty:  # noqa: PERF203
                continue

    def start(self):
        super().start()
        self.is_started = True

    def notify(self, func: Callable, *args, **kwargs):
        if not self.is_started:
            self.start()
        self.task_queue.put((func, args, kwargs))

    def stop(self):
        self.running = False

    def process_notification(self, task):
        func, args, kwargs = task
        try:
            func(*args, **kwargs)
        except Exception as e:
            if self.logger:
                self.logger.exception("emit_event_failed", error=e)


class Event(Generic[P]):
    def __init__(self, notifier: Notifier, logger: SenxorLogger | None = None):
        self.notifier = notifier
        self.listener: Callable[P, None] | None = None
        self.logger = logger

    def on(self, listener: Callable[P, None]) -> Callable[[], None]:
        self.listener = listener
        return self.clear

    def emit(self, *args: P.args, **kwargs: P.kwargs) -> None:
        if self.listener is None:
            return
        self.notifier.notify(self.listener, *args, **kwargs)

    def clear(self):
        self.listener = None


class SenxorInterfaceEvent:
    def __init__(self, logger: SenxorLogger | None = None):
        notifier = Notifier(logger)
        self.open = Event[[]](notifier, logger)
        self.close = Event[[]](notifier, logger)
        self.data = Event[[bytes | None, bytes]](notifier, logger)
        self.error = Event[[Exception]](notifier, logger)
