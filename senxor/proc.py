# Copyright (c) 2025 Meridian Innovation. All rights reserved.

"""Image processing utilities for Senxor devices."""

from __future__ import annotations

import importlib.resources
import json
from typing import Any, Literal

import numpy as np
from colormap_tool import get_colormaps, resample_lut

from senxor.consts import (
    CELSIUS_TO_FAHRENHEIT_RATIO,
    FAHRENHEIT_OFFSET,
    FAHRENHEIT_TO_CELSIUS_RATIO,
    KELVIN,
    SENXOR_FRAME_SHAPE,
)

__all__ = [
    "apply_colormap",
    "colormaps",
    "dk_to_celsius",
    "enlarge",
    "get_colormaps",
    "normalize",
    "raw_to_frame",
    "resample_lut",
]

_RESOURCE_DIR = importlib.resources.files("senxor").joinpath("resources")


colormaps = {
    "inferno": get_colormaps("inferno", namespace="cv"),
    "magma": get_colormaps("magma", namespace="cv"),
    "plasma": get_colormaps("plasma", namespace="cv"),
    # ------------------------------------------------------------
    "autumn": get_colormaps("autumn", namespace="cv"),
    "bone": get_colormaps("bone", namespace="cv"),
    "jet": get_colormaps("jet", namespace="cv"),
    "rainbow": get_colormaps("rainbow", namespace="cv"),
    "spring": get_colormaps("spring", namespace="cv"),
    "cool": get_colormaps("cool", namespace="cv"),
    "pink": get_colormaps("pink", namespace="cv"),
    "hot": get_colormaps("hot", namespace="cv"),
    "viridis": get_colormaps("viridis", namespace="cv"),
    "cividis": get_colormaps("cividis", namespace="cv"),
    "turbo": get_colormaps("turbo", namespace="cv"),
}

with (_RESOURCE_DIR / "cmaps.json").open() as f:
    _custom_cmaps = json.load(f)

for k, v in _custom_cmaps.items():
    lut = np.array(v, dtype=np.uint8).T.reshape(256, 3)
    colormaps[k] = lut


def bytes_to_raw(bytes_data: bytes, unit: Literal["dK", "dC", "dF", "K", "C", "F"]) -> np.ndarray:
    """Convert bytes data to raw data."""
    if unit == "dK":
        raw = np.frombuffer(bytes_data, dtype=np.uint16)
    elif unit in ["dC", "dF"]:
        raw = np.frombuffer(bytes_data, dtype=np.int16)
    elif unit in ["K", "C", "F"]:
        raw = np.frombuffer(bytes_data, dtype=np.float16)
    else:
        raise ValueError(f"Invalid unit: {unit}")
    return raw


def raw_to_temp(
    raw: np.ndarray,
    in_unit: Literal["dK", "dC", "dF", "K", "C", "F"],
    out_unit: Literal["K", "C", "F"],
) -> np.ndarray:
    """Convert raw data to temperature data."""
    if in_unit == "dK":
        data = raw / 10
        in_unit = "K"
    elif in_unit == "dC":
        data = (raw / 10) -273.15
        in_unit = "C"
    elif in_unit == "dF":
        data = raw / 10
        in_unit = "F"
    else:
        data = raw

    if out_unit == in_unit:
        temp = data
    else:
        if in_unit == "K" and out_unit == "C":
            temp = _kelvin_to_celsius(data)
        elif in_unit == "K" and out_unit == "F":
            temp = _kelvin_to_fahrenheit(data)
        elif in_unit == "C" and out_unit == "K":
            temp = _celsius_to_kelvin(data)
        elif in_unit == "C" and out_unit == "F":
            temp = _celsius_to_fahrenheit(data)
        elif in_unit == "F" and out_unit == "K":
            temp = _fahrenheit_to_kelvin(data)
        elif in_unit == "F" and out_unit == "C":
            temp = _fahrenheit_to_celsius(data)
        else:
            raise ValueError(f"Invalid output unit: {out_unit}")

    temp = np.round(temp, 2)

    return temp


def bytes_to_adc(bytes_data: bytes) -> np.ndarray:
    """Convert bytes data to ADC data."""
    return np.frombuffer(bytes_data, dtype=np.uint16)


def raw_to_frame(raw: np.ndarray) -> np.ndarray:
    """Convert the raw data from `Senxor.read(..., raw=True)` to a shaped frame.

    Parameters
    ----------
    raw : np.ndarray
        The raw data from `Senxor.read(..., raw=True)`.

    Returns
    -------
    np.ndarray
        The shaped frame.

    """
    if raw.ndim != 1:
        raise ValueError("Raw data must be a 1D array.")

    raw_length = raw.size
    frame_shape = SENXOR_FRAME_SHAPE.get(raw_length, None)
    if frame_shape is None:
        raise ValueError(f"Invalid raw data size: {raw_length}")
    return raw.reshape(frame_shape)


def normalize(
    image: np.ndarray,
    in_range: tuple | None = None,
    out_range: tuple | None = None,
    dtype: Any | None = np.float32,
):
    """Normalize image intensity to a desired range and data type using NumPy.

    Supported dtypes:

    - `np.floating`
    - `np.uint8`
    - `np.uint16`
    - `np.int16`
    - `np.int32`

    Parameters
    ----------
    image : numpy.ndarray
        Input image.
    in_range : tuple or None, optional
        Min and max intensity values of the input image.
        If None, the min and max of the input image are used.
        Default is None.
        Providing (min, max) is recommended, because this can avoid re-computation.
    out_range : tuple or None, optional
        Min and max intensity values of the output image.

        The function does not validate the `out_range` parameter if it is specified, be careful.

        If None:

        - If `dtype` is specified as a floating-point type, (0.0, 1.0) is used.
        - If `dtype` is specified as an integer type, the min/max of `dtype` are used.
        - If `dtype` is None:
            - If image.dtype is a floating-point type, (0.0, 1.0) is used.
            - If image.dtype is an integer type, the min/max of image.dtype are used.
        Default is None.

    dtype : numpy.dtype or None, optional
        Desired output data type.
        If None, the input image's data type is used.
        Default is np.float32.

    Returns
    -------
    numpy.ndarray
        Normalized image with the specified range and data type.

    Examples
    --------
    This function normalizes any image or numerical array, scaling its intensity values
    to a desired output range and data type.

    1. Normalizing a float array to an 8-bit image (0 to 255):

    >>> data_float = np.array([[-0.5, 0.0, 0.5], [1.0, 1.5, 2.0]], dtype=np.float32)
    >>> print(data_float)
        [[-0.5  0.   0.5]
        [ 1.   1.5  2. ]]
    >>> normalized_uint8 = normalize(data_float, dtype=np.uint8)
    >>> print(normalized_uint8)
        [[  0  64 127]
        [191 255 255]]
    >>> print(normalized_uint8.dtype)
    uint8

    2. Normalizing an 8-bit image to float (0.0 to 1.0):

    >>> image_uint8 = np.array([[0, 100, 200], [50, 150, 255]], dtype=np.uint8)
    >>> print(image_uint8)
        [[  0 100 200]
        [ 50 150 255]]
    >>> normalized_float = normalize(image_uint8, dtype=np.float32)
    >>> print(normalized_float)
        [[0.   0.39215686 0.78431373]
        [0.19607843 0.58823529 1.        ]]
    >>> print(normalized_float.dtype)
    float32

    3. If the min/max value of in_range is more/less than the min/max image intensity,
    then the intensity levels are clipped:

    >>> image = np.array([51, 102, 153], dtype=np.float32)
    >>> normalize(image, in_range=(0, 255))
    array([0.2, 0.4, 0.6], dtype=float32)

    Notes
    -----
    1. Avoiding re-computation: If you've already computed min/max, provide them via `in_range` to avoid re-computation.
    2. Preserving original contrast: To prevent stretching, set `in_range` to the original data's known intensity bounds
    or full `dtype` range.
    3. Maintaining precision: For multi-step processing, use floating-point types (`np.float32`/`np.float64`) for
    intermediate steps. Only normalize to `np.uint8` as the **very last step** for display or saving.

    """
    target_dtype = dtype if dtype is not None else image.dtype

    if out_range is None:
        if np.issubdtype(target_dtype, np.floating):
            out_min, out_max = (0.0, 1.0)
        elif target_dtype == np.uint8:
            out_min, out_max = (0, 255)
        elif target_dtype == np.uint16:
            out_min, out_max = (0, 65535)
        elif target_dtype == np.int16:
            out_min, out_max = (-32768, 32767)
        elif target_dtype == np.int32:
            out_min, out_max = (-2147483648, 2147483647)
        else:
            raise ValueError(f"Unsupported dtype: {target_dtype}")
    else:
        # Simplified validation: no verbose warnings, trust user's out_range when explicitly given.
        # The np.clip will handle values outside this range.
        out_min, out_max = out_range

    if in_range is None:
        in_min = np.min(image)
        in_max = np.max(image)
    else:
        in_min, in_max = in_range

    # Handle the case where in_max equals in_min to avoid division by zero
    if in_max == in_min:
        # If all input values are the same, map them to the midpoint of the output range
        normalized_image = np.full_like(image, (float(out_min) + float(out_max)) / 2.0, dtype=np.float64)
    else:
        # Perform the linear normalizeping using float64 for intermediate precision
        normalized_image = (image.astype(np.float64) - in_min) * ((out_max - out_min) / (in_max - in_min)) + out_min

    # Clip values to the output range, then cast to target_dtype
    normalized_image = np.clip(normalized_image, out_min, out_max).astype(target_dtype)

    return normalized_image


def enlarge(image: np.ndarray, scale: int) -> np.ndarray:
    """Enlarge an image by an integer scale factor using nearest neighbor (no interpolation).

    Parameters
    ----------
    image : np.ndarray
        Input image array (2D or 3D).
    scale : int
        Integer scale factor for enlargement (must be >= 1).

    Returns
    -------
    np.ndarray
        Enlarged image array.

    """
    if scale < 1 or not isinstance(scale, int):
        raise ValueError("Scale must be an integer >= 1.")
    if image.ndim == 2 or image.ndim == 3:
        return image.repeat(scale, axis=0).repeat(scale, axis=1)
    else:
        raise ValueError("Input image must be 2D or 3D array.")


def apply_colormap(
    image: np.ndarray,
    lut: np.ndarray,
    in_range: tuple | None = None,
    to_int: bool = True,
    resample_size: int = 256,
    norm: bool = False,
) -> np.ndarray:
    """Apply a colormap to a grayscale image using numpy. Return a uint8/float32 RGB image, depending on the `to_int`.

    Parameters
    ----------
    image : np.ndarray
        The image to apply the colormap to. Should be a 2D array.
    lut : np.ndarray
        The colormap to apply. Should be a 2D array of shape (N, 3) or (N, 1, 3).
    in_range : tuple | None, optional
        The input range of the image. If `None`, the image's min/max are used.
        providing (min, max) is recommended, because this can avoid re-computation.
    to_int : bool, optional
        If True, the color image will be converted to uint8 after applying the colormap.
        If False and image.dtype is not uint8, the color image will be normalized to float32.
    resample_size : int, optional
        The colormap will be resampled to this size. For image formats with more
        detail, such as float32, increasing `resample_size` can help preserve
        more of the original image's fidelity. However, the actual effectiveness
        depends on the characteristics of the input image. Default is 256.
    norm : bool, optional
        Whether to normalize the image before applying the colormap. Default is False.

    Examples
    --------
    >>> image = np.array([[0, 100, 200], [50, 150, 255]], dtype=np.uint8)
    >>> lut = get_colormaps("viridis", namespace="cv", n=256)
    >>> color_image = apply_colormap(image, lut)
    >>> print(color_image.dtype)
    uint8

    >>> image = np.array([[0, 100, 200], [50, 150, 255]], dtype=np.float32)
    >>> lut = get_colormaps("viridis", namespace="cv", n=256)
    >>> color_image = apply_colormap(image, lut, to_int=False)
    >>> print(color_image.dtype)
    float32

    """
    if not isinstance(resample_size, int) or resample_size < 256:
        raise ValueError("resample_size must be an integer >= 256 if specified.")
    if image.ndim != 2:
        raise ValueError("Input image must be a 2D array.")

    if lut.ndim == 3 and lut.shape[1] == 1 and lut.shape[2] == 3:
        lut = lut.reshape(-1, 3)

    if lut.ndim != 2 or lut.shape[1] != 3:
        raise ValueError("LUT must be of shape (N, 3) or (N, 1, 3).")

    if np.issubdtype(image.dtype, np.floating):
        image = image.astype(np.float32)

    image_dtype = image.dtype

    if image_dtype == np.uint8:
        resampled_lut = resample_lut(lut, 256)
        image_ = normalize(image, in_range, dtype=np.uint8) if norm else image
        color_image = resampled_lut[image_]
    elif image_dtype == np.float32 or image_dtype == np.uint16 or image_dtype == np.int16 or image_dtype == np.int32:
        resampled_lut = resample_lut(lut, resample_size)
        min_, max_ = (np.min(image), np.max(image)) if in_range is None else in_range
        # convert to float32
        float_image = normalize(image, (min_, max_), dtype=np.float32) if norm or image_dtype != np.float32 else image

        indices = np.clip(float_image * (resample_size - 1), 0, resample_size - 1).astype(np.int64)
        color_image = resampled_lut[indices]  # dtype: uint8

        if to_int:  # noqa: SIM108
            color_image = color_image.astype(np.uint8)
        else:
            color_image = normalize(color_image, dtype=np.float32)

    else:
        raise TypeError(f"Unsupported image dtype: {image_dtype}")

    return color_image


# ===============================
# Private functions
# ===============================


def _kelvin_to_celsius(kelvin: np.ndarray) -> np.ndarray:
    """Convert Kelvin to Celsius."""
    return kelvin - KELVIN


def _celsius_to_kelvin(celsius: np.ndarray) -> np.ndarray:
    """Convert Celsius to Kelvin."""
    return celsius + KELVIN


def _kelvin_to_fahrenheit(kelvin: np.ndarray) -> np.ndarray:
    """Convert Kelvin to Fahrenheit."""
    return (kelvin - KELVIN) * CELSIUS_TO_FAHRENHEIT_RATIO + FAHRENHEIT_OFFSET


def _fahrenheit_to_kelvin(fahrenheit: np.ndarray) -> np.ndarray:
    """Convert Fahrenheit to Kelvin."""
    return (fahrenheit - FAHRENHEIT_OFFSET) * FAHRENHEIT_TO_CELSIUS_RATIO + KELVIN


def _celsius_to_fahrenheit(celsius: np.ndarray) -> np.ndarray:
    """Convert Celsius to Fahrenheit."""
    return celsius * CELSIUS_TO_FAHRENHEIT_RATIO + FAHRENHEIT_OFFSET


def _fahrenheit_to_celsius(fahrenheit: np.ndarray) -> np.ndarray:
    """Convert Fahrenheit to Celsius."""
    return (fahrenheit - FAHRENHEIT_OFFSET) * FAHRENHEIT_TO_CELSIUS_RATIO


# ===============================
# Deprecated functions
# ===============================


def dk_to_celsius(raw: np.ndarray) -> np.ndarray:
    """Convert raw data from `Senxor.read()` to Celsius degrees data.

    The senxor device returns data in uint16 format, which is 1/10 Kelvin.
    This function converts the data to Celsius degrees.

    Parameters
    ----------
    raw : np.ndarray
        The raw data.

    """
    kelvin = raw / 10
    celsius = kelvin - KELVIN
    celsius = np.round(celsius, 1)
    return celsius
