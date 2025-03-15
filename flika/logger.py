"""
This module provides a logger for flika that uses datetime-based naming for log files.

The LEVEL variable can be set by the user below. Options are:

- logging.DEBUG
- logging.INFO
- logging.WARNING
- logging.ERROR
- logging.CRITICAL

"""
import logging
import sys
import pathlib
import beartype
from types import TracebackType
import datetime

# Set the default logging level
LEVEL = logging.WARNING


@beartype.beartype
def get_log_file() -> pathlib.Path:
    """Get the path to the log file using datetime-based naming."""
    log_dir = pathlib.Path.home() / '.FLIKA' / 'log'
    
    # Create log directory if it doesn't exist
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate timestamp for filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    return log_dir / f"flika_{timestamp}.log"

# Setup logging
log_file = get_log_file()
log_format = '%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(filename=str(log_file), format=log_format)

# Create logger
logger = logging.getLogger(__name__)
logger.setLevel(LEVEL)
handler = logging.StreamHandler()
handler.setLevel(LEVEL)
formatter = logging.Formatter(log_format)
handler.setFormatter(formatter)
logger.addHandler(handler)

@beartype.beartype
def handle_exception(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_traceback: TracebackType | None
) -> None:
    """Handle uncaught exceptions by logging them."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    # Use True to tell logger to use the current exception info
    logger.error("Uncaught exception", exc_info=True)

# Register exception handler
sys.excepthook = handle_exception
