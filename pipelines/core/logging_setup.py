"""Consistent logging setup for pipeline modules."""

import logging
import sys
from datetime import datetime
from pathlib import Path


def setup_logging(name: str = "pipeline", log_dir: str = ".") -> logging.Logger:
    """Configure logging with file and console handlers.

    Args:
        name: Logger name and log file prefix.
        log_dir: Directory for log files.

    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # Already configured

    logger.setLevel(logging.DEBUG)

    # Console handler — INFO and above
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(console)

    # File handler — DEBUG and above
    log_path = Path(log_dir) / f"{name}_{datetime.now():%Y%m%d_%H%M%S}.log"
    file_handler = logging.FileHandler(str(log_path))
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(file_handler)

    return logger
