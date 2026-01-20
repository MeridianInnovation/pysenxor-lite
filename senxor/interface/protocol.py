# Copyright (c) 2025-2026 Meridian Innovation. All rights reserved.

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Literal, Protocol, TypeVar, overload

if TYPE_CHECKING:
    from senxor.interface.event import SenxorInterfaceEvent

TDevice = TypeVar("TDevice", bound="IDevice")
TInterface = TypeVar("TInterface", bound="ISenxorInterface")


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
# (e.g. clear buffers and retry), otherwise it should raise `SenxorReadTimeoutError` to the Senxor class.


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

    """

    name: str


class ISenxorInterface(Protocol[TDevice]):
    """Protocol class for the Senxor devices.

    This class is used to provide a uniform interface for the communication with
    the device, e.g. USB, TCP/IP, etc.

    Attributes
    ----------
    device : TDevice
        The device to communicate with.
    is_connected : bool
        Whether the device is connected.

    """

    device: TDevice
    is_connected: bool
    events: SenxorInterfaceEvent

    def __init__(self, device: TDevice) -> None:
        """Initialize the interface.

        Parameters
        ----------
        device : TDevice
            The device to connect to.
        **kwargs : Any
            Additional keyword arguments to pass to the interface.

        Returns
        -------
        None

        """

    @classmethod
    def list_devices(cls) -> list[TDevice]:
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

    def read(self, block: bool = True) -> tuple[bytes | None, bytes | None]:
        """Read a frame from the senxor.

        In block mode, the method should raise `SenxorReadTimeoutError` if no frame is available after the timeout.
        In non-block mode, the method should return None if no frame is available.

        Parameters
        ----------
        block : bool, optional
            Whether to block the read operation until a frame is available, by default True
            If False, the function will return None immediately if no frame is available.

        Raises
        ------
        SenxorReadTimeoutError
            If no frame is available after the timeout.


        Returns
        -------
        tuple[bytes | None, bytes | None]
            A tuple of two bytes containing the frame header and the frame data.
            If no frame is available, the function will return (None, None).

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

    @overload
    def on(self, event: Literal["open", "close"], listener: Callable[[], None]) -> Callable[[], None]: ...
    @overload
    def on(self, event: Literal["data"], listener: Callable[[bytes | None, bytes], None]) -> Callable[[], None]: ...
    @overload
    def on(self, event: Literal["error"], listener: Callable[[Exception], None]) -> Callable[[], None]: ...

    def on(self, event: Literal["open", "close", "data", "error"], listener: Callable) -> Callable[[], None]:
        """Register a listener for an event.

        Parameters
        ----------
        event : Literal["open", "close", "data", "error"]
            The event to register the listener for.
        listener : Callable
            The listener to register.

        Returns
        -------
        Callable[[], None]
            The function to clear the listener.

        Raises
        ------
        ValueError
            If the event is invalid.

        """
        if event == "open":
            return self.events.open.on(listener)
        elif event == "close":
            return self.events.close.on(listener)
        elif event == "data":
            return self.events.data.on(listener)
        elif event == "error":
            return self.events.error.on(listener)
        else:
            raise ValueError(f"Invalid event: {event}")

    def __repr__(self) -> str:
        """Return a string representation of the interface."""
        return f"{self.__class__.__name__}(device={self.device})"

    def __str__(self) -> str:
        """Return a string representation of the interface."""
        return f"{self.__class__.__name__} - {self.device.name}"
