from .logger import logger
logger.debug("Started 'reading __init__.py'")
from .version import __version__
from .flika import start_flika
from . import global_vars as g
logger.debug("Completed 'reading __init__.py'")