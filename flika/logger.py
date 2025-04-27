"""
This module provides a logger for flika that uses datetime-based naming for log files.

The LEVEL variable can be set by the user below. Options are:

- logging.DEBUG
- logging.INFO
- logging.WARNING
- logging.ERROR
- logging.CRITICAL

"""

import datetime
import logging
import pathlib
import sys
from types import TracebackType

import colorama
from colorama import Fore, Style

# Set the default logging level
LEVEL = logging.INFO

colorama.init()


class ColoredFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": Fore.CYAN,
        "INFO": Fore.GREEN,
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
        "CRITICAL": Fore.RED + Style.BRIGHT,
    }

    def format(self, record):
        # Color the level name
        levelname = record.levelname
        if levelname in self.COLORS:
            colored_levelname = f"{self.COLORS[levelname]}{levelname}{Style.RESET_ALL}"
            record.levelname = colored_levelname

        # Color the clickable link part
        filename = record.filename
        lineno = record.lineno
        funcName = record.funcName

        # Use a distinct color for the clickable link
        colored_link = f"{Fore.BLUE}{filename}:{lineno}:{funcName}{Style.RESET_ALL}"

        # Temporarily replace the values with our colored version
        record.filename = ""
        record.lineno = ""
        record.funcName = colored_link

        # Format with a simplified format string
        result = logging.Formatter("%(levelname)s %(funcName)s - %(message)s").format(
            record
        )

        # Restore the original values
        record.filename = filename
        record.lineno = lineno
        record.funcName = funcName

        return result


def get_log_file() -> pathlib.Path:
    """Get the path to the log file using datetime-based naming."""
    log_dir = pathlib.Path.home() / ".FLIKA" / "log"

    # Create log directory if it doesn't exist
    log_dir.mkdir(parents=True, exist_ok=True)

    # Generate timestamp for filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    return log_dir / f"flika_{timestamp}.log"


# Setup logging
log_format = "%(levelname)s %(filename)s:%(lineno)d - %(message)s"
log_format = "%(levelname)s %(filename)s:%(lineno)d:%(funcName)s - %(message)s"
log_file = get_log_file()
formatter = ColoredFormatter(log_format)
handler = logging.StreamHandler()
handler.setFormatter(formatter)


logging.basicConfig(filename=str(log_file), format=log_format)

# Create logger
logger = logging.getLogger(__name__)
logger.setLevel(LEVEL)
logger.addHandler(handler)


def handle_exception(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_traceback: TracebackType | None,
) -> None:
    """Handle uncaught exceptions by logging them."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    # Use True to tell logger to use the current exception info
    logger.error("Uncaught exception", exc_info=True)


# Register exception handler
sys.excepthook = handle_exception
