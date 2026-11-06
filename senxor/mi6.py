# Copyright (c) 2025-2026 Meridian Innovation. All rights reserved.

"""MI6 device control and thermal, RGB, and fusion frame reads."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, TypedDict, overload

import numpy as np

from senxor.core import Senxor
from senxor.interface.tcpip_mi6 import TCPIPMI6Interface
from senxor.interface.tcpip_serial import TCPIPPort
from senxor.proc import colormaps, resample_lut
from senxor.regmap.mi6 import MI6FieldsManager, MI6RegistersManager

if TYPE_CHECKING:
    from collections.abc import Sequence

    from senxor.interface.protocol import ISenxorInterface

__all__ = [
    "MI6",
    "DetectionConfig",
    "FusionConfig",
]

_FusionStyle = Literal["blend", "hot_regions", "edges", "raw_index"]
_DetectionType = Literal["person", "drinkware", "appliances", "other"]
_Overlay = Literal["off", "outlines", "boxes"]

_FUSION_STYLES: tuple[_FusionStyle, ...] = ("blend", "hot_regions", "edges", "raw_index")
_DETECTION_TYPES: dict[_DetectionType, int] = {
    "person": 0x01,
    "drinkware": 0x02,
    "appliances": 0x04,
    "other": 0x08,
}
_OVERLAY_BITS: dict[_Overlay, tuple[int, int]] = {
    "off": (0x80, 0x00),
    "outlines": (0xC0, 0x80),
    "boxes": (0xC0, 0xC0),
}


class FusionConfig(TypedDict):
    """The fusion stream configuration.

    Attributes
    ----------
    enabled : bool
        Whether fusion frames are sent over TCP.
    style : {"blend", "hot_regions", "edges", "raw_index"}
        The fusion display style.
    mask : bool
        Whether thermal content is limited to the detected regions.
    shrink_step : int
        The mask shrink step, from 0 to 7.

    """

    style: _FusionStyle
    mask: bool
    shrink_step: int


class DetectionConfig(TypedDict):
    """The detection configuration.

    Attributes
    ----------
    enabled : bool
        Whether YOLO detection is running.
    types : list[str]
        The selected detection categories: "person", "drinkware",
        "appliances", and "other".
    overlay : {"off", "outlines", "boxes"}
        The detection overlay mode.

    """

    enabled: bool
    types: list[_DetectionType]
    overlay: _Overlay


def _nv12_to_bgr(data: bytes, width: int, height: int) -> np.ndarray:
    """Convert an NV12 payload to a uint8 BGR image using OpenCV."""
    import cv2  # noqa: PLC0415

    image = np.frombuffer(data, dtype=np.uint8).reshape(height * 3 // 2, width)
    return cv2.cvtColor(image, cv2.COLOR_YUV2BGR_NV12)


class MI6(Senxor):
    """The MI6 variant of Senxor.

    Attributes
    ----------
    interface : TCPIPMI6Interface
        The interface used to communicate with the device.
    regs : MI6RegistersManager
        The Senxor register system with MI6-specific controls.
    fields : MI6FieldsManager
        The Senxor fields with MI6 stream and image processing controls.

    """

    interface: TCPIPMI6Interface
    regs: MI6RegistersManager
    fields: MI6FieldsManager

    def __init__(
        self,
        host: str,
        port: int = 5600,
        *,
        timeout: float = 3.0,
        auto_open: bool = True,
    ) -> None:
        """Initialize the MI6 device.

        Parameters
        ----------
        host : str
            The device hostname or IP address.
        port : int, optional
            The TCP port of the device, by default 5600.
        timeout : float, optional
            The command reply timeout in seconds, by default 3.0.
        auto_open : bool, optional
            Whether to open and initialize the device automatically,
            by default True.

        Raises
        ------
        ValueError
            If `timeout` is not greater than zero.

        """
        interface = TCPIPMI6Interface(TCPIPPort(host, port), timeout=timeout)
        super().__init__(interface, auto_open=auto_open)

    def _create_registers_manager(self, interface: ISenxorInterface) -> MI6RegistersManager:
        """Create the MI6 register manager."""
        return MI6RegistersManager(interface)

    def _update_bits(self, reg: int, mask: int, value: int) -> None:
        """Read a register and update the selected bits."""
        current = self.read_reg(reg)
        self.write_reg(reg, (current & ~mask) | value)

    def set_streams(self, *, thermal: bool, rgb: bool, fusion: bool) -> None:
        """Select the complete set of TCP image streams."""
        value = 0x08 | int(thermal) << 5 | int(rgb) << 6 | int(fusion) << 7
        self.write_reg(0xB5, value)

    def set_fusion_config(
        self,
        *,
        style: _FusionStyle | None = None,
        mask: bool | None = None,
        shrink_step: int | None = None,
    ) -> None:
        """Update the specified fusion image settings."""
        update_mask = value = 0
        if style is not None:
            try:
                value |= _FUSION_STYLES.index(style)
            except ValueError:
                raise ValueError(f"Unknown fusion style: {style}") from None
            update_mask |= 0x03
        if mask is not None:
            update_mask |= 0x20
            value |= int(mask) << 5
        if shrink_step is not None:
            if not 0 <= shrink_step <= 7:
                raise ValueError("shrink_step must be between 0 and 7")
            update_mask |= 0x1C
            value |= shrink_step << 2
        if update_mask:
            self._update_bits(0x35, update_mask, value)

    def get_fusion_config(self) -> FusionConfig:
        """Get the fusion image settings."""
        value = self.read_reg(0x35)
        return {
            "style": _FUSION_STYLES[value & 0x03],
            "mask": bool(value & 0x20),
            "shrink_step": (value >> 2) & 0x07,
        }

    def set_fusion_distance(self, meters: float | None) -> None:
        """Set the fusion working distance in meters."""
        if meters is None:
            self.write_reg(0x39, 0)
            return
        if not 0.1 <= meters <= 25.5 or round(meters, 1) != meters:
            raise ValueError("meters must be between 0.1 and 25.5 in steps of 0.1")
        self.write_reg(0x39, round(meters * 10))

    def get_fusion_distance(self) -> float:
        """Get the effective fusion working distance in meters."""
        return self.read_reg(0x39) / 10

    def set_detection_config(
        self,
        *,
        enabled: bool | None = None,
        types: Sequence[_DetectionType] | None = None,
        overlay: _Overlay | None = None,
    ) -> None:
        """Update the specified detection settings."""
        type_bits = 0
        if types is not None:
            try:
                for name in types:
                    type_bits |= _DETECTION_TYPES[name]
            except KeyError as error:
                raise ValueError(f"Unknown detection type: {error.args[0]}") from None
        overlay_bits = None
        if overlay is not None:
            try:
                overlay_bits = _OVERLAY_BITS[overlay]
            except KeyError:
                raise ValueError(f"Unknown detection overlay: {overlay}") from None
        if types is not None:
            self._update_bits(0x38, 0x0F, type_bits)
        if overlay_bits is not None:
            self._update_bits(0x35, *overlay_bits)
        if enabled is not None:
            self.fields.DETECTION_ENABLE.set(int(enabled))

    def get_detection_config(self) -> DetectionConfig:
        """Get the detection configuration.

        Returns
        -------
        DetectionConfig
            A dictionary with keys "enabled", "types", and "overlay",
            read from the device.

        """
        enabled = self.fields.DETECTION_ENABLE.get() == 1
        types = self.read_reg(0x38)
        style = self.read_reg(0x35)
        overlay: _Overlay = "off"
        if style & 0x80:
            overlay = "boxes" if style & 0x40 else "outlines"
        return {
            "enabled": enabled,
            "types": [name for name, bit in _DETECTION_TYPES.items() if types & bit],
            "overlay": overlay,
        }

    def get_dncnn_enable(self) -> bool:
        """Get the DnCNN enable flag.

        Returns
        -------
        bool
            Whether DnCNN is enabled.

        """
        return self.fields.DNCNN_ENABLE.get() == 1

    def set_dncnn_enable(self, enabled: bool) -> None:
        """Set the DnCNN enable flag.

        Parameters
        ----------
        enabled : bool
            Whether to enable DnCNN.

        """
        self.fields.DNCNN_ENABLE.set(1 if enabled else 0)

    def disable_all_filters(self) -> None:
        """Disable all Senxor filters and DnCNN."""
        super().disable_all_filters()
        self.set_dncnn_enable(False)

    def get_filters_status(self) -> dict:
        """Get the status of all filters.

        Returns
        -------
        dict[str, bool]
            The enable flags for "stark", "mms_kxms", "mms_ra", "median",
            "temporal", and "dncnn".

        """
        return {**super().get_filters_status(), "dncnn": self.get_dncnn_enable()}

    @overload
    def read_rgb(self, *, block: Literal[False]) -> np.ndarray | None: ...

    @overload
    def read_rgb(self, *, block: Literal[True] = True) -> np.ndarray: ...

    def read_rgb(self, *, block: bool = True) -> np.ndarray | None:
        """Read the latest RGB frame from MI6.

        Parameters
        ----------
        block : bool, optional
            Whether to wait for a frame, by default True.
            If False, return immediately when no frame is available.

        Returns
        -------
        np.ndarray | None
            A uint8 BGR image with shape (360, 640, 3).
            If `block=False` and no new frame is available, returns None.

        Raises
        ------
        SenxorResponseTimeoutError
            If no frame arrives within the configured timeout.
        SenxorNotConnectedError
            If the device is not connected.
        ImportError
            If OpenCV is not installed.

        """
        data = self.interface.read_rgb(self.get_read_timeout() if block else 0)
        return None if data is None else _nv12_to_bgr(data, 640, 360)

    @overload
    def read_fusion(self, *, block: Literal[False]) -> np.ndarray | None: ...

    @overload
    def read_fusion(self, *, block: Literal[True] = True) -> np.ndarray: ...

    def read_fusion(self, *, block: bool = True) -> np.ndarray | None:
        """Read the latest fusion frame from MI6.

        Parameters
        ----------
        block : bool, optional
            Whether to wait for a frame, by default True.
            If False, return immediately when no frame is available.

        Returns
        -------
        np.ndarray | None
            A uint8 BGR image with shape (360, 480, 3).
            If `block=False` and no new frame is available, returns None.

        Raises
        ------
        SenxorResponseTimeoutError
            If no frame arrives within the configured timeout.
        SenxorNotConnectedError
            If the device is not connected.
        ImportError
            If an NV12 frame is read and OpenCV is not installed.

        Notes
        -----
        GFUS frames use the library's Inferno palette, which may differ
        from the device palette.

        """
        frame = self.interface.read_fusion(self.get_read_timeout() if block else 0)
        if frame is None:
            return None
        tag, data = frame
        if tag == "GFUC":
            return _nv12_to_bgr(data, 480, 360)
        image = np.frombuffer(data, dtype=np.uint8).reshape(360, 480)
        lut = resample_lut(colormaps["inferno"], 256).reshape(256, 3)
        return lut[:, ::-1][image]
