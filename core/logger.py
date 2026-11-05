"""
Safe logger wrapper.
Uses loguru when available, falls back to standard logging.
This prevents ModuleNotFoundError in frozen PyInstaller EXEs.
"""

from __future__ import annotations

import logging
import sys

try:
    from loguru import logger as _loguru_logger
    _HAS_LOGURU = True
    logger = _loguru_logger
except ImportError:
    _HAS_LOGURU = False
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )
    logger = logging.getLogger("scanner")

    # Add convenience methods so code that calls logger.success / logger.exception still works
    def _success(msg, *args, **kwargs):
        logger.info(msg, *args, **kwargs)

    def _exception(msg, *args, **kwargs):
        logger.error(msg, *args, **kwargs, exc_info=True)

    logger.success = _success  # type: ignore
    logger.exception = _exception  # type: ignore
