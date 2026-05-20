# Copyright (c) 2025-2026 Meridian Innovation. All rights reserved.

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, Protocol

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(frozen=True)
class DeviceState:
    is_streaming: bool
    frame_shape: tuple[int, int]
    fps_divider: int
    no_header: bool


# The following is the protocol for the interface class.
# The interface class must implement the methods and properties defined in this protocol class.

# Note:

# 1. Return values
# The interface class must return values or raise exceptions as specified in each method's docstring.

# 2. Input parameters
# Register-related method parameter validation is implemented by the Senxor class, the interface class is only
# responsible for device communication.

# 3. Error handling
# Check the docstring of each method to see whether the method should raise an exception.
# The interface class should try to raise exceptions defined in the senxor._error module.
# The principle of error handling is separation of responsibilities
# - the interface class should handle communication errors,
# - the Senxor class should handle business logic errors.
# The interface class should pass errors it cannot handle to the Senxor class for processing.
# For example, when the `read` method times out, this could be because the device is not in streaming mode
# or due to communication errors.
# If the interface class can determine it's a communication error, it can handle it directly
# (e.g. clear buffers and retry), otherwise it should raise `SenxorResponseTimeoutError` to the Senxor class.


# Specifically, if the device is disconnected, the interface class should set the `is_connected` property to False
# and raise a `SenxorNotConnectedError` exception.
# For example, for a serial interface, if the device is disconnected, a SerialException will occur on the next
# read/write operation. The interface class should catch this exception, then enter the error handling flow.
# For TCP/IP interfaces, the interface class can perform simple retries. If retries fail,
# then enter the error handling flow.


class IDevice(Protocol):
    """Protocol class for the device.

    This class is used to provide a uniform interface for the communication with
    the device, e.g. serial port, socket, etc. It must have a `name` attribute for identification.

    Attributes
    ----------
    name : str
        The name of the device.
    interface_type : ClassVar[str]
        The type of the interface.

    """

    INTERFACE_TYPE: ClassVar[str]

    @property
    def name(self) -> str:
        """The name of the device."""
        ...


class ISenxorInterface(Protocol):
    """Protocol class for the Senxor devices.

    This class is used to provide a uniform interface for the communication with
    the device, e.g. USB, TCP/IP, etc.

    Attributes
    ----------
    device : IDevice
        The device to communicate with.
    is_connected : bool
        Whether the device is connected.
    data_ready : bool
        Whether the data is ready to be read.

    """

    _device_state: DeviceState

    def __init__(self, device: IDevice) -> None:
        """Initialize the interface.

        Parameters
        ----------
        device : IDevice
            The device to connect to.
        **kwargs : Any
            Additional keyword arguments to pass to the interface.

        Returns
        -------
        None

        """

    @property
    def device(self) -> IDevice:
        """The device to communicate with."""
        ...

    @property
    def is_connected(self) -> bool:
        """Whether the device is connected."""
        ...

    @property
    def data_ready(self) -> bool:
        """(Optional) Whether the data is ready to be read."""
        raise NotImplementedError("Data ready is not supported by this interface.")

    @classmethod
    def list_devices(cls) -> Sequence[IDevice]:
        """List all the devices of this interface."""
        ...

    def open(self) -> None:
        """Open the connection to the device.

        If the device is already open, this method should not raise an exception.
        """
        ...

    def close(self) -> None:
        """Close the connection to the device.

        If the device is already closed, this method should not raise an exception.
        """
        ...

    def bind_state(self, state: DeviceState) -> None:
        """Receive the latest device state snapshot from Senxor."""
        self._device_state = state

    def read(self, timeout: float | None = None) -> tuple[bytes | None, bytes | None]:
        """Read a frame from the senxor.

        Parameters
        ----------
        timeout : float | None, optional
            Maximum seconds to wait for a frame. ``None`` waits until a frame is available.
            ``0`` returns immediately when no frame is available.

        Raises
        ------
        SenxorResponseTimeoutError
            If no frame is available before the timeout expires.

        Returns
        -------
        tuple[bytes | None, bytes | None]
            Frame header and payload bytes. When ``timeout=0`` and no frame is available,
            returns ``(None, None)``.

        """
        ...

    def read_reg(self, reg: int) -> int:
        """Read a register value from the senxor.

        If this operation fails, this function should raise an exception depending on the error.

        Parameters
        ----------
        reg : int
            The register to read.

        Returns
        -------
        int
            The value of the register.

        """
        ...

    def read_regs(self, regs: list[int]) -> dict[int, int]:
        """(Optional) Read multiple registers from the senxor.

        If this operation fails, this function should raise an exception depending on the error.

        Parameters
        ----------
        regs : list[int]
            The list of registers to read.

        Returns
        -------
        dict[int, int]
            The dictionary of register addresses and their values.

        """
        ...

    def write_reg(self, reg: int, value: int) -> None:
        """Write a value to a register.

        If this operation fails, this function should raise an exception depending on the error.

        Parameters
        ----------
        reg : int
            The register to write to.
        value : int
            The value to write to the register.

        """
        ...

    def write_regs(self, regs: dict[int, int]) -> None:
        """(Optional) Write multiple registers to the senxor.

        If this operation fails, this function should raise an exception depending on the error.

        Parameters
        ----------
        regs : dict[int, int]
            The dictionary of register addresses and their values to write.

        """
        ...

    def hard_reset(self) -> None:
        """(Optional) Hard reset the device.

        This operation is optional and may not be supported by all devices.

        This method should not automatically re-open the connection to the device.

        Returns
        -------
        None


        Raises
        ------
        NotImplementedError
            If the device does not support hard reset.

        """
        raise NotImplementedError("Hard reset is not supported by this interface.")

    def __repr__(self) -> str:
        """Return a string representation of the interface."""
        return f"{self.__class__.__name__}(device={self.device})"

    def __str__(self) -> str:
        """Return a string representation of the interface."""
        return f"{self.__class__.__name__} - {self.device.name}"
