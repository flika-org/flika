import logging, sys
from logging import NullHandler
from .flika import start_flika
from . import global_vars as g
from .window import Window
from .version import __version__
from .process import *
from .roi import import_rois

# import modules that are commonly used inside Flika
import numpy as np
from pyqtgraph import plot, show
import pyqtgraph as pg
import pyqtgraph.opengl as gl


logging.getLogger('flika').addHandler(NullHandler())
def handle_exception(exc_type, exc_value, exc_traceback):
    try:
        logging.getLogger('flika').warn(str(exc_type) + "\n" + str(exc_value) + " " + str(exc_traceback.tb_frame.f_code))
    except:
        logging.getLogger('flika').warn(str(exc_type) + "\n" + str(exc_value))

    sys.__excepthook__(exc_type, exc_value, exc_traceback)
sys.excepthook = handle_exception