# Copyright (c) 2025 Meridian Innovation. All rights reserved.

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    import numpy as np

# The following is the protocol for the interface class.
# The interface class must inherit from this protocol.
# The interface class must implement the methods and properties defined in this protocol.

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


class SenxorInterfaceProtocol(Protocol):
    """Protocol class for the Senxor devices.

    This class is used to provide a uniform interface for the communication with
    the device, e.g. USB, TCP/IP, etc.
    """

    def __init__(self, address: Any, **kwargs) -> None:
        """Initialize the interface.

        Parameters
        ----------
        address : Any
            The address of the device to connect to.
        **kwargs : Any
            Additional keyword arguments to pass to the interface.

        Returns
        -------
        None

        """

    @staticmethod
    @abstractmethod
    def discover(*args, **kwargs) -> list[Any]:
        """Discover the devices on the network. Return a list of device objects."""
        ...

    @property
    @abstractmethod
    def is_connected(self) -> bool | None:
        """Check if the device is connected.

        Returns
        -------
        bool | None
            True if the device is connected, False if the device is not connected,
            None if the connection cannot be checked.

        """
        ...

    @property
    @abstractmethod
    def address(self) -> Any:
        """Get the address of the device."""
        ...

    @staticmethod
    @abstractmethod
    def is_valid_address(address: Any) -> bool:
        """Validate if the address is valid for the interface."""
        ...

    @abstractmethod
    def open(self) -> None:
        """Open the connection to the device.

        If the device is already open, this method should not raise an exception.
        """
        ...

    @abstractmethod
    def close(self) -> None:
        """Close the connection to the device.

        If the device is already closed, this method should not raise an exception.
        """
        ...

    @abstractmethod
    def read(self, block: bool = True, **kwargs) -> tuple[np.ndarray, np.ndarray] | None:
        """Read a frame from the senxor.

        In block mode, the method should raise `SenxorReadTimeoutError` if no frame is available after the timeout.
        In non-block mode, the method should return None if no frame is available.

        Parameters
        ----------
        block : bool, optional
            Whether to block the read operation until a frame is available, by default True
            If False, the function will return None immediately if no frame is available.
        **kwargs : Any
            Additional keyword arguments to pass to the read operation.

        Returns
        -------
        tuple[np.ndarray, np.ndarray] | None
            A tuple of two numpy arrays containing the frame header and the frame data.
            If no frame is available, the function will return None.

        """

    @abstractmethod
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

    @abstractmethod
    def read_regs(self, regs: list[int]) -> dict[int, int]:
        """Read multiple registers from the senxor.

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

    @abstractmethod
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

    # def hw_reset(self) -> None:
    #     """
    #     Perform a hardware reset of the device.

    #     Note: Only SPI/I2C communication interfaces support this feature.
    #     """
    #     ...

    # def data_ready_callback(self, **kwargs) -> None:
    #     """
    #     Callback function for when a new frame is available.

    #     Note: Only SPI/I2C communication interfaces support this feature.
    #     """
    #     ...
