# Copyright (c) 2025-2026 Meridian Innovation. All rights reserved.

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, cast

from serial import PortNotOpenError, Serial, SerialException
from serial.tools import list_ports

from senxor.consts import SENXOR_PRODUCT_ID, SENXOR_VENDER_ID
from senxor.error import SenxorLostConnectionError, SenxorNotConnectedError
from senxor.interface.protocol import IDevice
from senxor.interface.serial_port.base import SerialInterfaceBase, SerialTransportBase

if TYPE_CHECKING:
    from serial.tools.list_ports_common import ListPortInfo


def is_serial_port_senxor(port: ListPortInfo) -> bool:
    """Check if the serial port is a senxor device."""
    return (port.vid == SENXOR_VENDER_ID) and (port.pid in SENXOR_PRODUCT_ID)


def list_senxor_serial_ports(exclude_open_ports: bool = True) -> list[SerialPort]:
    """List all the senxor serial ports.

    Parameters
    ----------
    exclude_open_ports : bool, optional
        If True, exclude the ports that are currently open (in use).
        Default is True.

    """
    ports = list_ports.comports()
    senxor_ports = []
    for port in ports:
        if not is_serial_port_senxor(port):
            continue
        if exclude_open_ports:
            try:
                s = Serial(port.device, exclusive=True)
                s.close()
            except SerialException:
                continue
        senxor_ports.append(SerialPort(port))
    return senxor_ports


class SerialPort(IDevice):
    INTERFACE_TYPE = "serial"

    def __init__(self, port: ListPortInfo):
        self.port = port

    @property
    def name(self) -> str:
        return self.port.name

    @property
    def device(self) -> str:
        return self.port.device

    @property
    def vid(self) -> int:
        return self.port.vid

    @property
    def pid(self) -> int:
        return self.port.pid

    def __repr__(self) -> str:
        return f"SerialPort(port={self.port})"

    def __str__(self) -> str:
        return f"SerialPort {self.name}"


class SerialTransport(SerialTransportBase):
    SENXOR_SERIAL_PARAMS: ClassVar[dict[str, Any]] = {
        "baudrate": 115200,
        "bytesize": 8,
        "parity": "N",
        "stopbits": 1,
        "xonxoff": False,
        "rtscts": False,
        "dsrdtr": False,
        "timeout": 1,
        "write_timeout": 0.2,
        "exclusive": True,
    }

    def __init__(self, device: SerialPort):
        super().__init__(device)
        self.ser: Serial = Serial()

    @property
    def is_open(self) -> bool:
        return self.ser.is_open

    def open(self) -> None:
        device = cast("SerialPort", self.device)
        if self.ser.is_open:
            return
        else:
            self.ser.port = device.device
            self.ser.apply_settings(self.SENXOR_SERIAL_PARAMS)
            self.ser.open()

    def close(self) -> None:
        self.ser.close()

    def cancel_read(self) -> None:
        self.ser.cancel_read()

    def read(self) -> bytes:
        try:
            data = self.ser.read(self.ser.in_waiting or 1)
        except Exception as e:
            if isinstance(e, PortNotOpenError):
                raise SenxorNotConnectedError from e
            elif isinstance(e, SerialException):
                raise SenxorLostConnectionError from e
            else:
                raise e
        else:
            return data

    def write(self, data: bytes) -> None:
        try:
            self.ser.write(data)
        except Exception as e:
            if isinstance(e, PortNotOpenError):
                raise SenxorNotConnectedError from e
            elif isinstance(e, SerialException):
                raise SenxorLostConnectionError from e
            else:
                raise e


class SerialInterface(SerialInterfaceBase):
    TRANSPORT_CLASS = SerialTransport

    def __init__(self, device: SerialPort):
        if not is_serial_port_senxor(device.port):
            raise ValueError(f"The serial port {device.device} is not a senxor device.")
        super().__init__(device)

    @property
    def device(self) -> SerialPort:
        return cast("SerialPort", self._device)

    @classmethod
    def list_devices(cls) -> list[SerialPort]:
        return list_senxor_serial_ports()
