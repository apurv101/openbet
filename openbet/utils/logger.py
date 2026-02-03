"""Logging configuration for Openbet."""

import logging
import sys
from pathlib import Path
from typing import Optional

from openbet.config import get_settings


def setup_logger(
    name: str = "openbet",
    log_file: Optional[str] = None,
    log_level: Optional[str] = None,
) -> logging.Logger:
    """Setup and configure logger.

    Args:
        name: Logger name
        log_file: Log file path. If None, uses config value.
        log_level: Log level. If None, uses config value.

    Returns:
        Configured logger instance
    """
    settings = get_settings()

    log_file = log_file or settings.log_file
    log_level = log_level or settings.log_level

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# Default logger instance
logger = setup_logger()
