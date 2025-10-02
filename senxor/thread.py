# Copyright (c) 2025 Meridian Innovation. All rights reserved.

"""Thread utilities for Senxor devices."""

from __future__ import annotations

import contextlib
import copy
import queue
import threading
from collections import deque
from typing import TYPE_CHECKING, Any, Callable, Literal, cast

from senxor.log import get_logger

if TYPE_CHECKING:
    import numpy as np
    from cv2 import VideoCapture

    from senxor import Senxor


class CVCamThread:
    def __init__(
        self,
        video_capture: VideoCapture,
        on_data: Callable[[np.ndarray], None] | None = None,
        *,
        raise_on_backlog: bool = False,
        backlog_threshold: int = 5,
    ):
        """Thread for reading frames from a video capture.

        Parameters
        ----------
        video_capture : VideoCapture
            The video capture to read frames from.
        on_data : Callable, optional
            The callback function to call when a frame is read.
        raise_on_backlog : bool, optional
            Whether to raise an error if the frame buffer backlog exceeds the threshold.
        backlog_threshold : int, optional
            The threshold for the frame buffer backlog.

        """
        self.video_capture = video_capture
        self.on_data = on_data
        self.notify_on_data = on_data is not None
        self.raise_on_backlog = raise_on_backlog
        self.backlog_threshold = backlog_threshold
        self.last_data: np.ndarray | None = None

        self._buffer = queue.Queue(maxsize=self.backlog_threshold)
        self._stop_event = threading.Event()
        self._stop_event.set()
        self._reader_thread: threading.Thread | None = None
        self._notifier_thread: threading.Thread | None = None

    def start(self) -> None:
        self._stop_event.clear()
        self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._reader_thread.start()
        if self.notify_on_data:
            self._notifier_thread = threading.Thread(target=self._notify_loop, daemon=True)
            self._notifier_thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._reader_thread:
            self._reader_thread.join()
        if self._notifier_thread:
            self._notifier_thread.join()

    def read(self) -> np.ndarray | None:
        """Read the frame from the video capture.

        Returns
        -------
        np.ndarray | None
            The frame from the video capture.

        Raises
        ------
        RuntimeError
            If the thread is not started.

        """
        if self._stop_event.is_set():
            raise RuntimeError("Thread not started. Call `start()` before reading data.")
        if self.last_data is None:
            frame = None
        else:
            frame = self.last_data
            self.last_data = None
        return frame

    def _read_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                success, frame = self.video_capture.read()
            except Exception:
                self._stop_event.set()
                raise
            if not success:
                continue
            if self.notify_on_data:
                self._put_data(frame)
            self.last_data = frame

    def _put_data(self, frame: np.ndarray) -> None:
        try:
            self._buffer.put_nowait(frame)
        except queue.Full:
            if self.raise_on_backlog:
                self._stop_event.set()
                raise TimeoutError(
                    "Frame buffer backlog exceeded. "
                    "The callback function may be too slow or blocking. "
                    "Consider optimizing the callback to handle frames more efficiently.",
                ) from None
            else:
                self._buffer.get_nowait()
                self._buffer.put_nowait(frame)

    def _notify_loop(self) -> None:
        while not self._stop_event.is_set():
            frame = None
            try:
                frame = self._buffer.get(timeout=0.1)
            except queue.Empty:
                continue
            if frame is not None:
                on_data = cast("Callable", self.on_data)
                try:
                    on_data(frame)
                except Exception:
                    self._stop_event.set()
                    raise


class SenxorThread:
    def __init__(
        self,
        senxor: Senxor,
        on_data: Callable[[np.ndarray | None, np.ndarray], None] | None = None,
        *,
        raise_on_backlog: bool = False,
        backlog_threshold: int = 5,
    ):
        """Thread for reading data from a Senxor device.

        Parameters
        ----------
        senxor : Senxor
            The Senxor device to read data from.
        on_data : Callable, optional
            The callback function to call when a frame is read.
        raise_on_backlog : bool, optional
            Whether to raise an error if the data buffer backlog exceeds the threshold.
        backlog_threshold : int, optional
            The threshold for the data buffer backlog.

        """
        self.senxor = senxor
        self.on_data = on_data
        self.notify_on_data = on_data is not None
        self.raise_on_backlog = raise_on_backlog
        self.backlog_threshold = backlog_threshold
        self.last_data: tuple[np.ndarray | None, np.ndarray | None] = (None, None)

        self._buffer = queue.Queue(maxsize=self.backlog_threshold)
        self._stop_event = threading.Event()
        self._stop_event.set()
        self._reader_thread: threading.Thread | None = None
        self._notifier_thread: threading.Thread | None = None

    def start(self) -> None:
        self._stop_event.clear()
        if not self.senxor.is_streaming:
            self.senxor.start_stream()
        self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._reader_thread.start()
        if self.notify_on_data:
            self._notifier_thread = threading.Thread(target=self._notify_loop, daemon=True)
            self._notifier_thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._reader_thread:
            self._reader_thread.join()
        if self._notifier_thread:
            self._notifier_thread.join()

    def read(self) -> tuple[np.ndarray | None, np.ndarray | None]:
        """Read the data from the Senxor device.

        It's equivalent to `senxor.read(block=False)`, if you don't need the `on_data` callback,
        it's not necessary to use `SenxorThread`.

        Returns
        -------
        tuple[np.ndarray | None, np.ndarray | None]
            The (header, data) from the Senxor device.

        Raises
        ------
        RuntimeError
            If the thread is not started.

        """
        if self._stop_event.is_set():
            raise RuntimeError("Thread not started. Call `start()` before reading data.")
        if self.last_data[1] is None:
            result = (None, None)
        else:
            result = self.last_data
            self.last_data = (None, None)
        return result

    def _read_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                header, data = self.senxor.read()
            except Exception:
                self._stop_event.set()
                raise
            if data is None:
                continue
            if self.notify_on_data:
                self._put_data(header, data)
            self.last_data = (header, data)

    def _put_data(self, header: np.ndarray | None, data: np.ndarray) -> None:
        try:
            self._buffer.put_nowait((header, data))
        except queue.Full:
            if self.raise_on_backlog:
                self._stop_event.set()
                raise TimeoutError(
                    "Data buffer backlog exceeded. "
                    "The callback function may be too slow or blocking. "
                    "Consider optimizing the callback to handle data more efficiently.",
                ) from None
            else:
                self._buffer.get_nowait()
                self._buffer.put_nowait((header, data))

    def _notify_loop(self) -> None:
        while not self._stop_event.is_set():
            header = None
            data = None
            try:
                header, data = self._buffer.get(timeout=0.1)
            except queue.Empty:
                continue
            if data is not None:
                on_data = cast("Callable", self.on_data)
                try:
                    on_data(header, data)
                except Exception:
                    self._stop_event.set()
                    raise
