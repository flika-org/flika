"""
Flika: An interactive image processing program for biologists written in Python.
"""

from flika.version import __version__
from flika.logger import logger
from flika.flika import start_flika
import flika.global_vars as g

# Define public API
__all__ = ["start_flika", "__version__", "g"]
