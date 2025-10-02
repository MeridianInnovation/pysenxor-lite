# Copyright (c) 2025 Meridian Innovation. All rights reserved.

"""Logging utilities for Senxor devices."""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

import structlog
from structlog.stdlib import BoundLogger

__all__ = [
    "SenxorLogger",
    "get_logger",
    "setup_console_logger",
    "setup_file_logger",
    "setup_standard_logger",
]

SenxorLogger = BoundLogger

DEFAULT_LOGGER_LEVEL = logging.WARNING
LOGGER_PROCESSORS = [
    structlog.stdlib.filter_by_level,
    structlog.stdlib.PositionalArgumentsFormatter(),
    structlog.processors.add_log_level,
    structlog.stdlib.add_logger_name,
    structlog.contextvars.merge_contextvars,
    structlog.processors.TimeStamper("%Y-%m-%dT%H:%M:%S%z", utc=False),
    structlog.processors.StackInfoRenderer(),
    structlog.dev.set_exc_info,
    structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
]


def get_logger(logger_name: str = "senxor", *args, **kwargs) -> SenxorLogger:
    """Get a structured logger instance.

    Parameters
    ----------
    logger_name : str, optional
        The name of the logger, by default `"senxor"`
    *args : Any
        Positional arguments to pass to `structlog.get_logger`.
    **kwargs : Any
        Keyword arguments to pass to `structlog.get_logger`.

    Returns
    -------
    SenxorLogger
        A structured logger instance.

    Examples
    --------
    >>> from senxor.log import get_logger
    >>> logger = get_logger(device_id="1")
    >>> logger.warning("This is a warning message.")
    [warning  ] This is a warning message.    device_id=1

    """
    logger: BoundLogger = structlog.get_logger(logger_name, *args, **kwargs)
    return logger


def setup_standard_logger():
    """Setup a standard logger.

    This logger redirects all messages to the built-in `logging` module.
    It is the default logger for `senxor`.
    This logger is used by default when `senxor` is used as a library, which
    means that `senxor` should not have any side effects on the logging system.

    Instead, use `setup_console_logger` or `setup_file_logger` to setup a
    logger for your application.
    """
    structlog.configure(
        processors=LOGGER_PROCESSORS,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter_processors = [
        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
        structlog.dev.ConsoleRenderer(sort_keys=False),
    ]

    senxor_logger = logging.getLogger("senxor")
    senxor_logger.setLevel(DEFAULT_LOGGER_LEVEL)

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=formatter_processors,
    )

    if senxor_logger.hasHandlers():
        for handler_ in senxor_logger.handlers:
            senxor_logger.removeHandler(handler_)

    handler = logging.StreamHandler()
    handler.setLevel(DEFAULT_LOGGER_LEVEL)
    handler.setFormatter(formatter)
    senxor_logger.addHandler(handler)
    senxor_logger.propagate = False


def setup_console_logger(log_level: int | str = "INFO", logger_name: str = "senxor", *, add_logger_name: bool = False):
    """Setup a console logger.

    This logger is used to log messages to the console, can output colored
    and formatted messages.

    Parameters
    ----------
    log_level : int | str | None, optional
        The log level to use, by default `logging.INFO`
    logger_name : str, optional
        The name of the logger, by default `"senxor"`
    add_logger_name : bool, optional
        Whether to add the logger name to the console output, by default `False`

    """
    formatter_processors = [
        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
        structlog.dev.ConsoleRenderer(sort_keys=False),
    ]

    if not add_logger_name:
        formatter_processors.insert(0, _remove_logger_name_processor)

    logger = logging.getLogger(logger_name)

    handler_level = _get_log_level(log_level)
    logger_level = logger.getEffectiveLevel()
    logger_level = min(logger_level, handler_level)
    logger.setLevel(logger_level)

    if logger.hasHandlers():
        for handler_ in logger.handlers:
            logger.removeHandler(handler_)

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=formatter_processors,
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handler.setLevel(handler_level)
    logger.addHandler(handler)
    logger.propagate = False


def setup_file_logger(
    file_path: Path | str,
    file_mode: str = "w",
    log_level: int | str = "INFO",
    logger_name: str = "senxor",
    *,
    watch_file: bool = False,
    json_format: bool = False,
):
    """Setup a file logger.

    This logger is used to log messages to a file, can output formatted messages.

    Parameters
    ----------
    file_path : Path | str
        The path to the log file.
    file_mode : str, optional
        The mode to use for the log file, by default `"w"`
    log_level : int | str, optional
        The log level to use, by default `logging.INFO`
    logger_name : str, optional
        The name of the logger, by default `"senxor"`
    watch_file : bool, optional
        Whether to use the `logging.handlers.WatchedFileHandler` handler, by default `False`
    json_format : bool, optional
        Whether to use the `structlog.processors.JSONRenderer` formatter, by default `False`

    """
    logger = logging.getLogger(logger_name)
    handler_level = _get_log_level(log_level)
    logger_level = logger.getEffectiveLevel()
    logger_level = min(logger_level, handler_level)
    logger.setLevel(logger_level)

    if logger.hasHandlers():
        for handler_ in logger.handlers:
            logger.removeHandler(handler_)

    file_path = Path(file_path)

    if watch_file:
        handler = logging.handlers.WatchedFileHandler(file_path, mode=file_mode)
    else:
        handler = logging.FileHandler(file_path, mode=file_mode)

    if json_format:
        formatter_processors = [
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),
        ]
    else:
        formatter_processors = [
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.dev.ConsoleRenderer(sort_keys=False, colors=False),
        ]

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=formatter_processors,
    )
    handler.setFormatter(formatter)
    handler.setLevel(handler_level)
    logger.addHandler(handler)
    logger.propagate = False


def _remove_logger_name_processor(_, __, event: dict):
    event.pop("logger", None)
    return event


def _get_log_level(level: int | str):
    if isinstance(level, str):
        log_level_ = logging.getLevelNamesMapping().get(level.upper())
        if log_level_ is None:
            raise KeyError(f"Invalid log level: {level}")
        return log_level_
    else:
        return level


setup_standard_logger()
