# Copyright (c) 2025-2026 Meridian Innovation. All rights reserved.

"""Thread utilities for Senxor devices."""

from __future__ import annotations

import queue
import threading
from typing import TYPE_CHECKING, Callable, cast

if TYPE_CHECKING:
    import numpy as np
    from cv2 import VideoCapture
    from cv2_enumerate_cameras.camera_info import CameraInfo


def list_camera_info(
    backend: int = 0,
) -> list[CameraInfo]:
    """List available camera information.

    Parameters
    ----------
    backend : int, optional
        The backend to use for camera enumeration. If 0, all supported backends are used.

    Returns
    -------
    list of CameraInfo
        List of camera information objects. Use `cv2.VideoCapture(camera.index, camera.backend)` to open a camera.

    Examples
    --------
    1. Print all cameras information available.
    >>> for camera in list_camera_info():
    ...     print(camera.index, camera.name, camera.backend)
    ...     print(camera.path, camera.vid, camera.pid)

    2. Connect to a specific camera.
    >>> camera_info = list_camera_info()[0]
    >>> cap = cv2.VideoCapture(camera_info.index, camera_info.backend)

    """
    try:
        from cv2_enumerate_cameras import enumerate_cameras as _enumerate_cameras  # noqa: PLC0415
    except ImportError:
        raise ImportError(
            "Required dependency is not installed. Please install it with `pip install cv2-enumerate-cameras`.",
        ) from None
    # 3.1.0: remove the exclude_same_index parameter and related logic
    cameras = _enumerate_cameras(backend)
    return cameras


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
