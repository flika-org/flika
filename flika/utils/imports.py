"""

My preferred startup sequence for running flika inside an IDE is this:

from flika import *
start_flika()
from flika.utils.imports import *
"""

from ..window import Window
from ..process import *
from ..roi import open_rois
import numpy as np
from pyqtgraph import plot, show
import pyqtgraph as pg
import pyqtgraph.opengl as gl