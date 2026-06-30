"""Centralised logging setup.

Call :func:`setup_logging` once at program start (the CLI scripts do this), then use
:func:`get_logger` anywhere to obtain a namespaced child logger.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

_ROOT_NAME = "personalai"
_CONFIGURED = False


def setup_logging(level: str = "INFO", log_dir: str | Path | None = None) -> logging.Logger:
    """Configure the root ``personalai`` logger with console (and optional file) output."""
    global _CONFIGURED
    logger = logging.getLogger(_ROOT_NAME)
    if _CONFIGURED:
        return logger

    logger.setLevel(getattr(logging, str(level).upper(), logging.INFO))
    logger.propagate = False
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)-7s %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    logger.addHandler(console)

    if log_dir:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path / "personalai.log", encoding="utf-8")
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)

    _CONFIGURED = True
    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a namespaced child logger, e.g. ``get_logger("ingest")``."""
    if name:
        return logging.getLogger(f"{_ROOT_NAME}.{name}")
    return logging.getLogger(_ROOT_NAME)
