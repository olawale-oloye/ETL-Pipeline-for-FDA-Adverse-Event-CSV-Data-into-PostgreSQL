"""
Central logging configuration for the project.

Creates:
    logs/app.log

Usage:
    from conf.conf import logger
"""

from pathlib import Path
import logging
from typing import Sequence


# Base directory = folder containing this file
BASE_DIR = Path(__file__).resolve().parent

# Project root directory
PROJECT_ROOT = BASE_DIR.parent

# Logs directory
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Log file
LOG_FILE = LOG_DIR / "app.log"


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """
    Configure application logging.

    Args:
        level: logging level

    Returns:
        configured logger instance
    """

    handlers: Sequence[logging.Handler] = [
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
        force=True
    )

    return logging.getLogger("app")


# create shared logger instance
logger = setup_logging()