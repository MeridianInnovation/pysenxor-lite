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
        """Read a frame from the camera with BGR format.

        Returns:
        -------
        tuple[bool, Any]
            A tuple containing a boolean indicating success and the frame data.

        Examples:
        --------
        >>> cam = LiteCamera(0)
        >>> ret, frame = cam.read()
        >>> if ret:
        ...     cv2.imshow("frame", frame)
        ...     cv2.waitKey(1)

        Note:
        ----
        The frame is in BGR format.

        """
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
