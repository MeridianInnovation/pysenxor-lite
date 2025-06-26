import time

import numpy as np
import pytest

# Try to import the necessary module and check for cameras.
# Skip all tests in this module if senxor.cam or its dependencies are not available,
# or if no cameras are found.
try:
    from senxor.cam import LiteCamera, _litecam_imported, list_camera

    _no_camera = not list_camera()
except (ImportError, RuntimeError):
    _litecam_imported = False
    _no_camera = True


pytestmark = [
    pytest.mark.skipif(
        not _litecam_imported,
        reason="lite-camera package not found or failed to initialize",
    ),
    pytest.mark.skipif(_no_camera, reason="No physical camera found on this system"),
]


@pytest.fixture(scope="module")
def camera():
    """Module-scoped fixture to initialize and release the default camera."""
    cam = LiteCamera(0)
    assert cam.isOpened(), "Failed to open camera for testing"

    # Set a resolution to ensure the camera is in a valid state for reading
    media_types = cam.listMediaTypes()
    if not media_types:
        pytest.skip("Camera does not report any media types, cannot run tests.")

    # Sort media types by width to have a predictable order
    media_types.sort(key=lambda x: x["width"])

    media_type = media_types[0]
    width, height = media_type["width"], media_type["height"]
    assert cam.setResolution(width, height)

    yield cam

    cam.release()
    assert not cam.isOpened(), "Failed to release camera after tests"


def test_list_camera():
    """Test that list_camera returns a non-empty list of strings."""
    devices = list_camera()
    assert isinstance(devices, list)
    assert len(devices) > 0
    assert all(isinstance(dev, str) for dev in devices)


def test_camera_open_and_is_opened(camera: LiteCamera):
    """Test camera is opened via fixture."""
    assert camera.isOpened()
    assert camera.is_open


def test_camera_properties(camera: LiteCamera):
    """Test width and height properties of the camera."""
    assert camera.width > 0
    assert camera.height > 0


def test_camera_get(camera: LiteCamera):
    """Test the get method for frame width and height."""
    width = camera.get(3)  # CAP_PROP_FRAME_WIDTH
    height = camera.get(4)  # CAP_PROP_FRAME_HEIGHT
    assert width == camera.width
    assert height == camera.height
    with pytest.raises(ValueError):
        camera.get(999)  # Invalid property


def test_camera_read(camera: LiteCamera):
    """Test reading a frame from the camera."""
    # The fixture should have already set a valid resolution.
    # We loop a few times to give the camera time to start streaming.
    ret = False
    frame = None
    for _ in range(10):
        ret, frame = camera.read()
        if ret:
            break
        time.sleep(0.1)

    assert ret, "camera.read() failed to capture a frame after multiple attempts"
    assert isinstance(frame, np.ndarray)
    assert frame.shape == (camera.height, camera.width, 3)
    assert frame.dtype == np.uint8


def test_camera_release():
    """Test releasing the camera."""
    cam = LiteCamera(0)
    assert cam.isOpened()
    cam.release()
    assert not cam.isOpened()
