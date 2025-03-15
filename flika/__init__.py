"""
Flika: An interactive image processing program for biologists written in Python.
"""

# First, get the version directly
from flika.version import __version__

# After the version is imported, import other modules
# This prevents circular imports during setup
from flika.logger import logger
logger.debug("Started 'reading __init__.py'")
from flika.flika import start_flika
import flika.global_vars as g
logger.debug("Completed 'reading __init__.py'")

# Define public API
__all__ = ["start_flika", "__version__", "g"]