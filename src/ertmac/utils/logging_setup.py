"""
ertmac.utils.logging_setup
===========================
Provides a consistent logger factory for the entire package.

Usage
-----
    from ertmac.utils.logging_setup import get_logger
    log = get_logger(__name__)
    log.info("Starting audit…")
"""

import logging
import sys
from pathlib import Path
from typing import Optional


_FMT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"


def get_logger(
    name: str,
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
) -> logging.Logger:
    """Return a named logger with a consistent format.

    Parameters
    ----------
    name:
        Logger name (pass ``__name__`` from the calling module).
    level:
        Logging level (default: INFO).
    log_file:
        Optional path to additionally write logs to a file.

    Returns
    -------
    logging.Logger
    """
    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers if the logger already exists
    if logger.handlers:
        return logger

    logger.setLevel(level)
    formatter = logging.Formatter(_FMT, datefmt=_DATEFMT)

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # Optional file handler
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger
