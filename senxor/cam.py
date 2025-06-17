"""Wrapper for the lite-camera library. Provide a lightweight camera read and display interface."""

from typing import Any

import numpy as np

try:
    import litecam

    _litecam_imported = True
except ImportError:
    _litecam_imported = False

_litecam_imp_msg = "Install `lite-camera` to use LiteCamera related features."


class LiteCamera:
    """A wrapper for the litcam.PyCamera class."""

    def __init__(self, index: int):
        """Initialize a LiteCamera object."""
        if not _litecam_imported:
            raise ImportError(_litecam_imp_msg)

        self.camera: Any = litecam.PyCamera()  # type: ignore[attr-defined]
        self.index = index
        self._is_open = False

        # Keep a reference to the original functions to avoid type checker errors
        self._original_open = self.camera.open
        self._original_release = self.camera.release
        self._original_captureFrame = self.camera.captureFrame
        self._original_getWidth = self.camera.getWidth
        self._original_getHeight = self.camera.getHeight
        self._original_setResolution = self.camera.setResolution
        self._original_listMediaTypes = self.camera.listMediaTypes

        if not self.open():
            raise RuntimeError("Failed to open camera")

    def read(self) -> tuple[bool, Any]:
        resp = self._original_captureFrame()
        if resp is None:
            return False, None
        width, height, size, data = resp

        if size != width * height * 3:
            print(f"Warning: Unexpected data size. Expected {width * height * 3}, got {size}")
            return False, None

        data = np.frombuffer(data, dtype=np.uint8)
        data = data.reshape(height, width, 3)

        if width > 0 and height > 0:
            return True, data
        else:
            return False, None

    def isOpened(self) -> bool:
        """Same API as cv2.VideoCapture.isOpened."""
        return self._is_open

    @property
    def width(self) -> int:
        return self._original_getWidth()

    @property
    def height(self) -> int:
        return self._original_getHeight()

    @property
    def is_open(self) -> bool:
        return self._is_open

    def open(self) -> bool:
        """Open the camera."""
        is_open = self._original_open(self.index)
        self._is_open = bool(is_open)
        return self._is_open

    def set(self, propId: int, value: Any) -> bool:
        raise NotImplementedError("Use `setResolution` instead.")

    def get(self, propId: int) -> Any:
        """Same API as cv2.VideoCapture.get."""
        if propId == 3:  # CAP_PROP_FRAME_WIDTH
            return self._original_getWidth()
        elif propId == 4:  # CAP_PROP_FRAME_HEIGHT
            return self._original_getHeight()
        else:
            raise ValueError(f"Unsupported property: {propId}")

    def release(self) -> None:
        """Release the camera."""
        self._original_release()
        self._is_open = False

    def listMediaTypes(self) -> list:
        """List the media types supported by the camera."""
        return self._original_listMediaTypes()

    def setResolution(self, width: int, height: int) -> bool:
        """Set the resolution of the camera."""
        ret = self._original_setResolution(width, height)
        if not ret:
            raise RuntimeError("Failed to set resolution")
        return bool(ret)


class LiteWindow:
    """A wrapper for the litcam.PyWindow class with an OpenCV-like API."""

    def __init__(self, title: str, width: int, height: int):
        """Initialize a LiteWindow object.

        Parameters
        ----------
        title : str
            The title of the window.
        width : int
            The width of the window.
        height : int
            The height of the window.

        """
        if not _litecam_imported:
            raise ImportError(_litecam_imp_msg)

        # The C++ constructor expects (width, height, title)
        self.window = litecam.PyWindow(width, height, title)  # type: ignore[attr-defined]

        # Keep a reference to the original functions for clarity and potential direct use
        self._original_showFrame = self.window.showFrame
        self._original_waitKey = self.window.waitKey
        self._original_drawContour = self.window.drawContour
        self._original_drawText = self.window.drawText

    def show(self, data: np.ndarray) -> None:
        """Displays an image in the window. Similar to cv2.imshow.

        Parameters
        ----------
        data : np.ndarray
            The image to be shown. Should be a NumPy array with shape (height, width, 3)
            and dtype=np.uint8.

        """
        if not isinstance(data, np.ndarray):
            raise TypeError("Image data must be a NumPy array.")

        if data.ndim != 3 or data.shape[2] != 3:
            raise ValueError("Input array must be a 3-channel (RGB) image.")

        height, width, _ = data.shape
        # The C++ backend expects raw bytes
        data_bytes = data.astype(np.uint8).tobytes()
        self._original_showFrame(width, height, data_bytes)

    def showFrame(self, width: int, height: int, data: bytes) -> None:
        self._original_showFrame(width, height, data)

    def waitKey(self, exit_key: str = "q") -> bool:
        """Waits for a specific key to be pressed or the window to be closed.

        This method is designed for use in a loop. It differs from OpenCV's waitKey.
        It blocks indefinitely until the specified `exit_key` is pressed or the
        window is closed.

        Parameters
        ----------
        exit_key : str, optional
            A single character that, when pressed, will cause the function to
            return False. Defaults to "q".

        Returns
        -------
        bool
            - `True` if the loop should continue (no exit event occurred).
            - `False` if the `exit_key` was pressed or the window was closed.

        Example
        -------
        >>> window = LiteWindow("Test", 640, 480)
        >>> while window.waitKey("q"):
        ...     # Update and show frame
        ...     pass  # The loop breaks when 'q' is pressed or window is closed.

        """
        if not isinstance(exit_key, str) or len(exit_key) != 1:
            raise ValueError("exit_key must be a single character string.")
        return self._original_waitKey(exit_key)

    def drawContour(self, points: list[tuple[int, int]]) -> None:
        """Draws a contour on the current frame.

        Parameters
        ----------
        points : list[tuple[int, int]]
            A list of (x, y) coordinates representing the contour points.

        """
        self._original_drawContour(points)

    def drawText(
        self,
        text: str,
        org: tuple[int, int],
        fontScale: int,
        color: tuple[int, int, int],
    ) -> None:
        """Draws text on the current frame. API is similar to cv2.putText.

        Parameters
        ----------
        text : str
            The text string to be drawn.
        org : tuple[int, int]
            Tuple of (x, y) coordinates of the top-left corner of the text string.
        fontScale : int
            Font size.
        color : tuple[int, int, int]
            Tuple of (R, G, B) color of the text. Values are 0-255.

        """
        x, y = org
        self._original_drawText(text, x, y, fontScale, color)


def list_camera() -> list[str]:
    """List all cameras available.

    Returns
    -------
    list[str]
        A list of camera names.

    Examples
    --------
    >>> list_camera()
    ['Camera 0', 'Camera 1', 'Camera 2']

    You can use `LiteCamera(index)` to open a camera.
    >>> cam = LiteCamera(0)

    """
    if not _litecam_imported:
        raise ImportError(_litecam_imp_msg)

    return litecam.getDeviceList()  # type: ignore  # noqa: PGH003
