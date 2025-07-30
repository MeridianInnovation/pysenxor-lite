"""Logging utilities for Senxor devices."""

from __future__ import annotations

import logging
import logging.config
from pathlib import Path
from typing import TYPE_CHECKING, TextIO, cast

import structlog

if TYPE_CHECKING:
    from structlog.types import FilteringBoundLogger

__all__ = [
    "get_logger",
    "setup_console_logger",
    "setup_file_logger",
    "setup_standard_logger",
]


def get_logger(*args, **kwargs) -> FilteringBoundLogger:
    """Get a structured logger instance.

    Parameters
    ----------
    *args : Any
        Positional arguments to pass to `structlog.get_logger`.
    **kwargs : Any
        Keyword arguments to pass to `structlog.get_logger`.

    Returns
    -------
    structlog.BoundLogger
        A structured logger instance.

    Examples
    --------
    >>> from senxor.log import get_logger
    >>> logger = get_logger(device_id="1")
    >>> logger.warning("This is a warning message.")
    [warning  ] This is a warning message.    device_id=1

    """
    return structlog.get_logger(*args, **kwargs)


class _ConsoleOutPutProcessor:
    def __init__(self):
        self._formatter = structlog.dev.ConsoleRenderer(sort_keys=False)
        self._writer = structlog.PrintLogger()

    def __call__(self, logger, method, event):
        ev = event.copy()
        msg = self._formatter(logger, method, event)
        self._writer.msg(msg)
        return ev


def setup_standard_logger():
    """Setup a standard logger.

    This logger redirects all messages to the built-in `logging` module.
    It is the default logger for `senxor`.
    This logger is used by default when `senxor` is used as a library, which
    means that `senxor` should not have any side effects on the logging system.

    Instead, use `setup_console_logger` or `setup_file_logger` to setup a
    logger for your application.
    """
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer(sort_keys=False),
    ]
    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def setup_console_logger(log_level: int = logging.INFO):
    """Setup a console logger.

    This logger is used to log messages to the console, can output colored
    and formatted messages.

    Parameters
    ----------
    log_level : int, optional
        The log level to use, by default `logging.INFO`

    """
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S", utc=False),
            structlog.dev.ConsoleRenderer(sort_keys=False),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def setup_file_logger(
    path: Path | str,
    log_level: int = logging.INFO,
    *,
    file_mode: str = "wt+",
    log_as_json: bool = False,
    log_to_console: bool = True,
):
    """Setup a file logger.

    This logger is used to log messages to the console and a file, can output
    formatted messages.

    Parameters
    ----------
    path : Path | str
        The path to the log file.
    log_level : int, optional
        The log level to use for the file, by default `logging.NOTSET`
    file_mode : str, optional
        The mode to open the log file in, by default `"wt+"`
    log_as_json : bool, optional
        Whether to log to the file in JSON format, by default `False`
    log_to_console : bool, optional
        Whether to log to the console, by default `True`

    """
    file = cast("TextIO", Path(path).open(file_mode))  # noqa: SIM115

    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S", utc=False),
    ]

    if log_to_console:
        processors.append(_ConsoleOutPutProcessor())

    if log_as_json:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(sort_keys=False, colors=False))

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.WriteLoggerFactory(file),
        cache_logger_on_first_use=True,
    )


setup_standard_logger()
