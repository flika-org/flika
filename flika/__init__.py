"""
Flika: An interactive image processing program for biologists written in Python.
"""

import flika.global_vars as g
from flika.flika import start_flika
from flika.version import __version__

# Define public API
__all__ = ["start_flika", "__version__", "g"]
