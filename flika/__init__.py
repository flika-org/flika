from .logger import logger
logger.debug("Started 'reading __init__.py'")


from .flika import start_flika
from . import global_vars as g
#from .window import Window
from .version import __version__
#from .process import *
#from .roi import open_rois


# import modules that are commonly used inside flika
#import numpy as np
#from pyqtgraph import plot, show
#import pyqtgraph as pg
#import pyqtgraph.opengl as gl

logger.debug("Completed 'reading __init__.py'")