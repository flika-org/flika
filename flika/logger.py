import logging
import sys
import pathlib
import beartype
from types import TracebackType
# Set the default logging level
LEVEL = logging.WARNING

@beartype.beartype
def get_log_file() -> pathlib.Path:
    """Get the path to the log file with simple rotation."""
    log_dir = pathlib.Path.home() / '.FLIKA' / 'log'
    max_log_idx = 99

    # Create log directory if it doesn't exist
    log_dir.mkdir(parents=True, exist_ok=True)

    # Get existing log files
    existing_files = list(log_dir.glob('*.log'))

    # Find available log index
    try:
        existing_idxs = [int(f.stem) for f in existing_files if f.stem.isdigit()]
    except ValueError:
        print("Error with log folder. Delete all files in ~/.FLIKA/log/ and restart flika.")
        existing_idxs = []

    log_idx = 0
    while log_idx in existing_idxs:
        log_idx += 1
    log_idx = log_idx % max_log_idx

    # Delete next log in rotation if it exists
    idx_to_delete = (log_idx + 1) % max_log_idx
    log_file_to_delete = log_dir / f"{idx_to_delete:03d}.log"
    if log_file_to_delete.exists():
        try:
            log_file_to_delete.unlink()
        except Exception as e:
            print(f"Could not delete log file: {e}")

    return log_dir / f"{log_idx:03d}.log"

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
