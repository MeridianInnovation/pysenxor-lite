from __future__ import annotations

from abc import abstractmethod
from typing import Any, Protocol

import numpy as np


class SenxorInterfaceProtocol(Protocol):
    """Protocol class for the Senxor devices.

    This class is used to provide a uniform interface for the communication with
    the device, e.g. USB, TCP/IP, etc.
    """

    def __init__(self, address: Any, auto_open: bool = True, **kwargs) -> None:
        """Initialize the interface.

        Parameters
        ----------
        address : Any
            The address of the device to connect to.
        auto_open : bool, optional
            Whether to automatically open the device.
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
        """Open the connection to the device."""
        ...

    @abstractmethod
    def close(self) -> None:
        """Close the connection to the device."""
        ...

    @abstractmethod
    def read(self, block: bool = True, **kwargs) -> tuple[np.ndarray, np.ndarray] | None:
        """Read a frame from the senxor.

        If senxor is not in streaming mode, this function will return None.

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
