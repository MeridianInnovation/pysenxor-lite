"""Logging utilities for Senxor devices."""

from __future__ import annotations

import logging
import logging.config
from pathlib import Path

import structlog

default_logger = structlog.get_logger()


__all__ = [
    "get_logger",
    "setup_console_logger",
    "setup_file_logger",
    "setup_standard_logger",
]


def get_logger(name: str | None = None):
    """Get a structured logger instance.

    Parameters
    ----------
    name : str | None, optional
        The name of the logger, by default None

    Returns
    -------
    structlog.BoundLogger
        A structured logger instance.

    """
    if name is None:
        return default_logger
    else:
        return structlog.get_logger(name)


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
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.dev.ConsoleRenderer(
            sort_keys=False,
            colors=False,
        ),
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
    shared_processors = [
        structlog.stdlib.filter_by_level,
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S", utc=False),
        structlog.processors.StackInfoRenderer(),
    ]

    structlog.configure(
        processors=[*shared_processors, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.dev.ConsoleRenderer(sort_keys=False),
        ],
    )

    handler = logging.StreamHandler()
    # Use OUR `ProcessorFormatter` to format all `logging` entries.
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)


def setup_file_logger(
    log_file: Path | str,
    console_log_level: int = logging.INFO,
    file_log_level: int = logging.INFO,
):
    """Setup a file logger.

    This logger is used to log messages to the console and a file, can output
    formatted messages.

    Parameters
    ----------
    log_file : Path | str
        The path to the log file.
    console_log_level : int, optional
        The log level to use for the console, by default `logging.INFO`
    file_log_level : int, optional
        The log level to use for the file, by default `logging.INFO`

    """
    log_file = Path(log_file)

    timestamper = structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S")
    pre_chain = [
        structlog.stdlib.filter_by_level,
        # Add the log level and a timestamp to the event_dict if the log entry
        # is not from structlog.
        structlog.stdlib.add_log_level,
        # Add extra attributes of LogRecord objects to the event dictionary
        # so that values passed in the extra parameter of log methods pass
        # through to log output.
        structlog.stdlib.ExtraAdder(),
        timestamper,
    ]

    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "plain": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processors": [
                    structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                    structlog.dev.ConsoleRenderer(colors=False, sort_keys=False),
                ],
                "foreign_pre_chain": pre_chain,
            },
            "colored": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processors": [
                    structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                    structlog.dev.ConsoleRenderer(colors=True, sort_keys=False),
                ],
                "foreign_pre_chain": pre_chain,
            },
        },
        "handlers": {
            "default": {
                "level": console_log_level,
                "class": "logging.StreamHandler",
                "formatter": "colored",
            },
            "file": {
                "level": file_log_level,
                "class": "logging.handlers.WatchedFileHandler",
                "mode": "w",
                "filename": log_file.as_posix(),
                "formatter": "plain",
            },
        },
        "loggers": {
            "": {
                "handlers": ["default", "file"],
                "level": console_log_level,
                "propagate": True,
            },
        },
    })
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            timestamper,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


setup_standard_logger()
