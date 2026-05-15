# Copyright (c) 2025-2026 Meridian Innovation. All rights reserved.

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Callable, Literal, cast, overload

import numpy as np

from senxor.proc import process_senxor_data

if TYPE_CHECKING:
    from senxor.core import Senxor


class SenxorEvents:
    def __init__(self, senxor: Senxor) -> None:
        self._senxor = senxor
        self._open_listener: Callable[[], None] | None = None
        self._close_listener: Callable[[], None] | None = None
        self._data_listener: Callable[[np.ndarray | None, np.ndarray], None] | None = None
        self._error_listener: Callable[[Exception], None] | None = None
        self._acquisition_thread: threading.Thread | None = None
        self._acquisition_stop = threading.Event()

    @overload
    def on(self, event: Literal["open", "close"], listener: Callable[[], None]) -> Callable[[], None]: ...
    @overload
    def on(self, event: Literal["error"], listener: Callable[[Exception], None]) -> Callable[[], None]: ...
    @overload
    def on(
        self,
        event: Literal["data"],
        listener: Callable[[np.ndarray | None, np.ndarray], None],
    ) -> Callable[[], None]: ...

    def on(self, event: Literal["open", "close", "data", "error"], listener: Callable) -> Callable[[], None]:
        if event == "open":
            self._open_listener = listener
        elif event == "close":
            self._close_listener = listener
        elif event == "error":
            self._error_listener = listener
        elif event == "data":
            self._data_listener = listener
            if self._senxor.is_streaming:
                self._start_acquisition_thread()
        else:
            raise ValueError(f"Invalid event: {event}")

        def clear() -> None:
            if event == "open":
                self._open_listener = None
            elif event == "close":
                self._close_listener = None
            elif event == "error":
                self._error_listener = None
            elif event == "data":
                self._data_listener = None
                self._stop_acquisition_thread()

        return clear

    def notify_opened(self) -> None:
        if self._open_listener is not None:
            self._open_listener()

    def notify_stream_started(self) -> None:
        if self._data_listener is not None:
            self._start_acquisition_thread()

    def notify_stream_stopped(self) -> None:
        self._stop_acquisition_thread()

    def notify_closing(self) -> None:
        self._stop_acquisition_thread()

    def notify_closed(self) -> None:
        if self._close_listener is not None:
            self._close_listener()

    def _start_acquisition_thread(self) -> None:
        if self._data_listener is None:
            return
        if self._acquisition_thread is not None and self._acquisition_thread.is_alive():
            return
        self._acquisition_stop.clear()
        self._acquisition_thread = threading.Thread(
            target=self._acquisition_loop,
            name=f"senxor-acquisition-{self._senxor.name}",
            daemon=True,
        )
        self._acquisition_thread.start()

    def _stop_acquisition_thread(self) -> None:
        self._acquisition_stop.set()
        if self._acquisition_thread is not None:
            self._acquisition_thread.join(timeout=3)
            self._acquisition_thread = None

    def _acquisition_loop(self) -> None:
        while not self._acquisition_stop.is_set():
            listener = self._data_listener
            if listener is None:
                break
            try:
                header_bytes, data_bytes = self._senxor.interface.read(self._senxor.get_read_timeout())
            except Exception as e:
                error_listener = self._error_listener
                if error_listener is not None:
                    error_listener(e)
                break

            header = np.frombuffer(header_bytes, dtype=np.uint16) if header_bytes is not None else None
            is_adc_enabled = self._senxor.fields.ADC_ENABLE.get() == 1
            frame = process_senxor_data(cast("bytes", data_bytes), adc=is_adc_enabled)
            try:
                listener(header, frame)
            except Exception as e:
                error_listener = self._error_listener
                if error_listener is not None:
                    error_listener(e)
                break
