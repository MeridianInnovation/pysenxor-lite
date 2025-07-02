from __future__ import annotations

import contextlib
import copy
import queue
import threading
from typing import Any, Callable, Literal

import numpy as np
from structlog import get_logger

from senxor import Senxor
from senxor.cam import LiteCamera

logger = get_logger("senxor.thread")


class _BackgroundReader:
    """Generic background reader with listener pattern.

    Listener functions must be lightweight and non-blocking; otherwise a
    built-in TimeoutError is raised when the frame queue exceeds the specified
    backlog threshold.
    """

    def __init__(
        self,
        reader_func: Callable[[], Any],
        name: str,
        *,
        allow_listener: bool = True,
    ):
        self._reader_func = reader_func
        self._name = name
        self._allow_listener = allow_listener

        self._log = logger.bind(name=name)

        self._is_running = False
        self._reader_thread: threading.Thread | None = None
        self._lock = threading.Lock()

        # consume-on-read
        self._latest_data: Any | None = None

        # listener infra
        if allow_listener:
            self._listeners: dict[str, Callable[[Any], None]] = {}
            self._listener_counter = 0
            self._backlog_threshold = 5
            self._listeners_lock = threading.Lock()
            self._frame_queue = queue.Queue()
            self._queue_cv = threading.Condition()  # Condition for queue operations
            self._notifying = False
            self._notifier_thread: threading.Thread | None = None

    def read(self) -> Any | None:
        """Return the latest data and mark it as consumed.

        Returns
        -------
        Any or None
            The most recent data object, or ``None`` if nothing new is
            available since the last call.

        """
        with self._lock:
            data = self._latest_data
            self._latest_data = None
        return data

    def add_listener(self, fn: Callable[[Any], None], name: str | None = None) -> str:
        """Register a listener callback.

        Parameters
        ----------
        fn
            Callable invoked with the latest data object. **Must be
            lightweight and non-blocking**.
        name
            Optional unique identifier. If omitted, an automatic ``listener_X``
            name is assigned.

        Returns
        -------
        str
            The listener name actually registered.

        Raises
        ------
        RuntimeError
            If the listener pattern is disabled.
        ValueError
            If *name* already exists.

        """
        if not self._allow_listener:
            raise RuntimeError("Listener pattern is disabled for this reader instance")
        with self._listeners_lock:
            if name is None:
                name = f"listener_{self._listener_counter}"
                self._listener_counter += 1
            if name in self._listeners:
                raise ValueError(f"A listener with name '{name}' already exists")
            self._listeners[name] = fn
        self._log.debug("listener added", name=name)
        return name

    def remove_listener(self, name: str) -> None:
        """Unregister a previously registered listener by *name*."""
        if not self._allow_listener:
            raise RuntimeError("Listener pattern is disabled for this reader instance")
        with self._listeners_lock:
            if name not in self._listeners:
                raise KeyError(f"No listener found with name '{name}'")
            del self._listeners[name]
        self._log.debug("listener removed", name=name)

    def start(self) -> None:
        """Start reader and notifier threads (idempotent)."""
        if self._is_running:
            return
        if self._allow_listener:
            self._notifying = True
            self._notifier_thread = threading.Thread(
                target=self._notify_loop,
                name=f"{self._name}Notify",
                daemon=True,
            )
            self._notifier_thread.start()
        self._is_running = True
        self._reader_thread = threading.Thread(
            target=self._run,
            name=f"{self._name}Read",
            daemon=True,
        )
        self._reader_thread.start()

    def stop(self) -> None:
        """Stop reader and notifier threads (idempotent)."""
        if not self._is_running:
            return
        self._is_running = False
        if self._reader_thread:
            self._reader_thread.join()
        if self._allow_listener and self._notifier_thread:
            self._notifying = False
            with self._queue_cv:
                self._queue_cv.notify()  # Wake up the notifier to check _notifying flag
            self._notifier_thread.join()

    def _run(self) -> None:
        try:
            while self._is_running:
                self._read_once()
        except Exception as exc:  # pylint: disable=broad-except
            self._log.error("reader error", exc_info=exc)
            raise exc

    def _read_once(self) -> None:
        data = self._reader_func()
        if data is None:
            return
        with self._lock:
            self._latest_data = data
        if not self._allow_listener:
            return

        self._frame_queue.put(copy.copy(data))
        with self._queue_cv:
            self._queue_cv.notify()

    def _notify_loop(self) -> None:
        while self._notifying:
            with self._queue_cv:
                while self._frame_queue.empty() and self._notifying:
                    self._queue_cv.wait(0.1)

                if not self._notifying:
                    break

                current_queue_size = self._frame_queue.qsize()
                if current_queue_size >= self._backlog_threshold:
                    while not self._frame_queue.empty():
                        self._frame_queue.get_nowait()
                        self._frame_queue.task_done()
                    raise TimeoutError(
                        f"Listener processing backlog exceeded threshold ({self._backlog_threshold} frames).",
                        "Ensure all listener callbacks are lightweight and non-blocking.",
                    )
                else:
                    data = self._frame_queue.get_nowait()

            if data is not None:
                with self._listeners_lock:
                    listeners = tuple(self._listeners.values())

                if not listeners:
                    self._frame_queue.task_done()
                    continue

                try:
                    for fn in listeners:
                        fn(data)
                    self._frame_queue.task_done()
                except Exception as exc:
                    self._log.error("listener callback error", exc_info=exc)
                    self._frame_queue.task_done()
                    raise


class SenxorThread:
    """A threaded wrapper for Senxor for non-blocking reads with a listener pattern.

    This class continuously reads data from a Senxor device in a background thread.
    It implements a "consume-on-read" pattern for its `read()` method and provides
    a listener interface for push-based notifications.
    """

    def __init__(
        self,
        senxor: Senxor,
        *,
        frame_unit: Literal["C", "dK"] = "C",
        allow_listener: bool = True,
    ) -> None:
        """Initialize the SenxorThread.

        Parameters
        ----------
        senxor : Senxor
            A Senxor instance.
        frame_unit : {"C", "dK"}, default "C"
            The unit of the frame data. "C" for Celsius (float32), "dK" for
            deci-Kelvin (uint16).
        allow_listener : bool, optional
            Whether to enable the listener pattern. Defaults to True.

        Notes
        -----
            Listener functions **must** be extremely lightweight and non-blocking.
            If a listener function takes too long to execute, the `BackgroundReader`
            will raise a `TimeoutError` in the reading thread when the
            next frame arrives. This strict policy ensures that listener notifications
            do not fall behind the sensor's frame rate.

        """
        self._started = False
        self._senxor = senxor
        self._celsius = frame_unit == "C"
        self._reader = _BackgroundReader(self._read_senxor, self._senxor.address, allow_listener=allow_listener)
        self._log = logger.bind(address=self._senxor.address)

    def read(self) -> tuple[np.ndarray, np.ndarray] | tuple[None, None]:
        """Return the newest *(header, frame)* pair and consume it.

        Raises
        ------
        RuntimeError
            If the thread has not been started.

        """
        if not self._started:
            raise RuntimeError("Thread not started. Call start() before reading data.")

        data = self._reader.read()
        # The Senxor expects (None, None) if no data is available.
        if data is None:
            return (None, None)
        else:
            return data

    def add_listener(
        self,
        fn: Callable[[np.ndarray, np.ndarray], None],
        name: str | None = None,
    ) -> str:
        """Register a listener called with ``(header, frame)`` tuple.

        The supplied *fn* must accept two positional arguments *(header,
        frame)*. Internally the call is adapted to the generic listener
        signature.

        Parameters
        ----------
        fn
            Callable invoked with the latest data object. **Must be
            lightweight and non-blocking**.
        name
            Optional unique identifier. If omitted, an automatic ``listener_X``
            name is assigned.

        Notes
        -----
            Listener functions **must** be extremely lightweight and non-blocking.
            If a listener function takes too long to execute, the `BackgroundReader`
            will raise a `TimeoutError` in the reading thread when the
            next frame arrives. This strict policy ensures that listener notifications
            do not fall behind the sensor's frame rate.

        """

        def adapter(data):
            return fn(*data) if data is not None else None

        return self._reader.add_listener(adapter, name)

    def remove_listener(self, name: str) -> None:
        """Remove a previously registered listener by *name*."""
        self._reader.remove_listener(name)

    def start(self) -> None:
        """Connect to device and start background processing (idempotent)."""
        if self._started:
            return
        try:
            self._senxor.open()
            self._senxor.start_stream()
            self._reader.start()
            self._started = True
            self._log.info("senxor thread started", addr=self._senxor.address)
        except Exception:
            with contextlib.suppress(Exception):
                self._senxor.close()
            raise

    def stop(self) -> None:
        """Stop background processing and close device (idempotent)."""
        if not self._started:
            return
        with contextlib.suppress(Exception):
            self._reader.stop()
        with contextlib.suppress(Exception):
            self._senxor.close()
        self._started = False
        self._log.info("senxor thread stopped")

    def _read_senxor(self) -> tuple[np.ndarray, np.ndarray] | None:
        header, frame = self._senxor.read(block=True, celsius=self._celsius)
        # The reader is expected to return None if no data is available.
        if header is None or frame is None:
            return None
        else:
            return (header, frame)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.stop()

    def __del__(self):
        self.stop()

    def __repr__(self) -> str:
        return f"SenxorThread(addr={self._senxor.address!r})"


class CVCamThread:
    """A threaded wrapper for OpenCV's VideoCapture for non-blocking reads with a listener pattern.

    This class continuously reads frames from a camera in a background thread.
    It implements a "consume-on-read" pattern for its `read()` method and provides
    a listener interface for push-based notifications.
    """

    def __init__(
        self,
        capture,
        *,
        allow_listener: bool = True,
    ) -> None:
        """Initialize the CVCamThread.

        Parameters
        ----------
        capture : cv2.VideoCapture
            A pre-configured OpenCV VideoCapture instance.
        allow_listener : bool, default True
            Whether to enable the listener pattern.

        Notes
        -----
        Listener functions **must** be extremely lightweight and non-blocking.
        If a listener function takes too long to execute, the `_BackgroundReader`
        will raise a `TimeoutError` in the reading thread when the
        next frame arrives. This strict policy ensures that listener notifications
        do not fall behind the camera's frame rate.

        """
        self._started = False
        self.cam = capture
        self.camera_index = getattr(capture, "index", 0)
        self._reader = _BackgroundReader(
            self._read_camera,
            f"CVCamera{self.camera_index}",
            allow_listener=allow_listener,
        )
        self._log = logger.bind(camera_index=self.camera_index)

    def read(self) -> tuple[bool, np.ndarray | None]:
        """Return the newest frame and consume it.

        Returns
        -------
        tuple[bool, np.ndarray] or tuple[False, None]
            A tuple containing a boolean indicating success and the frame data,
            or (False, None) if no new frame is available.

        Raises
        ------
        RuntimeError
            If the thread has not been started.

        """
        if not self._started:
            raise RuntimeError("Thread not started. Call start() before reading data.")

        data = self._reader.read()
        if data is None:
            return False, None
        else:
            return data

    def add_listener(
        self,
        fn: Callable[[bool, np.ndarray], None],
        name: str | None = None,
    ) -> str:
        """Register a listener called with ``(success, frame)`` tuple.

        Parameters
        ----------
        fn
            Callable invoked with the latest frame. **Must be
            lightweight and non-blocking**.
        name
            Optional unique identifier. If omitted, an automatic ``listener_X``
            name is assigned.

        Returns
        -------
        str
            The listener name actually registered.

        Notes
        -----
        Listener functions **must** be extremely lightweight and non-blocking.
        If a listener function takes too long to execute, the `_BackgroundReader`
        will raise a `TimeoutError` in the reading thread when the
        next frame arrives. This strict policy ensures that listener notifications
        do not fall behind the camera's frame rate.

        """

        def adapter(data):
            return fn(*data) if data is not None else None

        return self._reader.add_listener(adapter, name)

    def remove_listener(self, name: str) -> None:
        """Remove a previously registered listener by *name*."""
        self._reader.remove_listener(name)

    def start(self) -> None:
        """Start background processing (idempotent)."""
        if self._started:
            return

        try:
            if not self.cam.isOpened():
                raise RuntimeError("Camera is not open")

            self._reader.start()
            self._started = True
            self._log.info("OpenCV camera thread started")
        except Exception as exc:
            self._log.error("OpenCV camera thread start failed", exc_info=exc)
            raise

    def stop(self) -> None:
        """Stop background processing (idempotent)."""
        if not self._started:
            return
        with contextlib.suppress(Exception):
            self._reader.stop()
        self._started = False
        self._log.info("OpenCV camera thread stopped")

    def _read_camera(self) -> tuple[bool, np.ndarray] | None:
        if not self.cam.isOpened():
            return None

        success, frame = self.cam.read()
        if not success or frame is None:
            return None

        return success, frame

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.stop()

    def __del__(self):
        self.stop()

    def __repr__(self) -> str:
        return f"CVCamThread(camera_index={self.camera_index!r})"
