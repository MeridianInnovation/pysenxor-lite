# Copyright (c) 2025 Meridian Innovation. All rights reserved.

"""RGB camera related utilities."""

from typing import TYPE_CHECKING

from cv2_enumerate_cameras import enumerate_cameras as _enumerate_cameras

from senxor.log import get_logger

if TYPE_CHECKING:
    from cv2_enumerate_cameras.camera_info import CameraInfo


def list_camera_info(
    backend: int = 0,
) -> list["CameraInfo"]:
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
    # 3.1.0: remove the exclude_same_index parameter and related logic
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
    get_logger().warning("`list_camera` is deprecated. Use `list_camera_info` instead.")

    all_cams = list_camera_info()
    return [cam.name for cam in all_cams]
