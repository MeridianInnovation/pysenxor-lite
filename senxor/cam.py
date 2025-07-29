"""RGB camera related utilities."""

import logging
from typing import TYPE_CHECKING

from cv2_enumerate_cameras import enumerate_cameras as _enumerate_cameras
from cv2_enumerate_cameras import supported_backends

if TYPE_CHECKING:
    from cv2_enumerate_cameras.camera_info import CameraInfo

logger = logging.getLogger(__name__)


def list_camera_info(
    backend: int = 0,
    *,
    exclude_same_index: bool = True,
) -> list["CameraInfo"]:
    """List available camera information.

    Parameters
    ----------
    backend : int, optional
        The backend to use for camera enumeration. If 0, all supported backends are used.
    exclude_same_index : bool, optional
        If backend is 0, True means exclude cameras with the same index across backends.
        Some cameras are available on multiple backends. If you are not interested in this, set it to False.

    Returns
    -------
    list of CameraInfo
        List of camera information objects. Use `cv2.VideoCapture(camera.index, camera.backend)` to open a camera.

    Examples
    --------
    1. List all cameras available and exclude duplicate indices.
    >>> for camera in list_camera_info():
    ...     print(camera.index, camera.name, camera.backend)
    0 GENERAL - VIDEO 700
    1 Integrated Camera 700

    2. List all cameras available and include duplicate indices.
    >>> for camera in list_camera_info(exclude_same_index=False):
    ...     print(camera.index, camera.name, camera.backend)
    0 GENERAL - VIDEO 700
    1 Integrated Camera 700
    0 GENERAL - VIDEO 1400
    1 Integrated Camera 1400

    3. Connect to a specific camera.
    >>> camera = list_camera_info()[0]
    >>> cap = cv2.VideoCapture(camera.index, camera.backend)

    4. View the camera information.
    >>> cam_info = list_camera_info()[0]
    >>> print(cam_info.index)
    0
    >>> print(cam_info.name)
    GENERAL - VIDEO
    >>> print(cam_info.backend)
    700
    >>> print(cam_info.vid)
    1234
    >>> print(cam_info.pid)
    5678
    >>> print(cam_info.path)
    /dev/video0

    """
    if backend == 0:
        cameras = []
        if exclude_same_index:
            seen_indices = set()
            for b in sorted(supported_backends):
                for cam in _enumerate_cameras(b):
                    if cam.index not in seen_indices:
                        cameras.append(cam)
                        seen_indices.add(cam.index)
        else:
            [cameras.extend(_enumerate_cameras(b)) for b in sorted(supported_backends)]
    else:
        cameras = _enumerate_cameras(backend)

    return cameras


def list_camera() -> list[str]:
    """List all cameras available.

    Warning:
    -------
    This function is deprecated. Use `list_camera_info` instead.

    Returns:
    -------
    list[str]
        A list of camera names.

    Examples:
    --------
    >>> list_camera()
    ['Camera 0', 'Camera 1', 'Camera 2']

    You can use `cv2.VideoCapture(index)` to open a camera.

    """
    logger.warning("`list_camera` is deprecated. Use `list_camera_info` instead.")

    all_cams = list_camera_info()
    return [cam.name for cam in all_cams]
