"""
Logging configuration for the trading bot.

Sets up a rotating file handler (logs/trading_bot.log) and a console handler,
both using a timestamped format that includes module name and log level.
"""

import logging
import logging.handlers
from pathlib import Path


LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_FILE = LOG_DIR / "trading_bot.log"
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_MAX_BYTES = 5 * 1024 * 1024   # 5 MB per file
_BACKUP_COUNT = 3               # keep 3 rotated backups


def setup_logging(level: int = logging.INFO) -> None:
    """Configure application-wide logging.

    Creates *logs/* if it does not exist, attaches a RotatingFileHandler and a
    StreamHandler to the root logger, and quiets noisy third-party loggers.

    Args:
        level: Root logging level (default: ``logging.INFO``).
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)

    # Rotating file handler — max 5 MB, 3 backups kept
    file_handler = logging.handlers.RotatingFileHandler(
        filename=LOG_FILE,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    # Console (stdout) handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)

    root = logging.getLogger()
    # Guard against duplicate handlers if called more than once
    if not root.handlers:
        root.setLevel(level)
        root.addHandler(file_handler)
        root.addHandler(console_handler)

    # Suppress noisy third-party loggers
    for noisy in ("urllib3", "requests", "websockets"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
