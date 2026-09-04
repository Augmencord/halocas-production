"""Structured logging setup for HALOCAS.

Configures application-wide logging with timestamps, level names,
module attribution, and contextual data.
"""

import logging
import sys
from typing import Any


class StructuredFormatter(logging.Formatter):
    """Custom formatter providing clear, consistent log output across services."""

    def __init__(self) -> None:
        super().__init__(
            fmt="%(asctime)s [%(levelname)s] [%(name)s:%(lineno)d] - %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record with structured attributes."""
        formatted_message = super().format(record)
        # Append additional structured context attributes if present
        extra_attrs: dict[str, Any] = {
            k: v
            for k, v in record.__dict__.items()
            if k not in logging.LogRecord("", 0, "", 0, "", (), None).__dict__
            and not k.startswith("_")
        }
        if extra_attrs:
            formatted_message += f" | context={extra_attrs}"
        return formatted_message


def setup_logging(log_level: str = "INFO") -> None:
    """Initialize root logging configuration.

    Args:
        log_level: Desired minimum log verbosity string (e.g. DEBUG, INFO, WARNING, ERROR).
    """
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Avoid adding duplicate handlers if already configured
    if not root_logger.handlers:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(numeric_level)
        stream_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(stream_handler)
    else:
        for existing_handler in root_logger.handlers:
            existing_handler.setLevel(numeric_level)
            existing_handler.setFormatter(StructuredFormatter())

    # Quiet overly chatty third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a named logger instance.

    Args:
        name: Logger identifier, typically `__name__`.

    Returns:
        logging.Logger: Configured logger.
    """
    return logging.getLogger(name)
