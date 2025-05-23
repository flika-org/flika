"""
Script namespace for flika.
"""

from inspect import getmembers, ismodule

import numpy as np
import pyqtgraph as pg
import scipy

from flika import global_vars as g
from flika import process, window
from flika.roi import open_rois


def getnamespace():
    """
    This function gets the namespace for the script interpreter.  It goes through all the modules in the 'process' package and loads all the objects defined in their '__all__' variables.
    """

    d = {}
    for name, mod in getmembers(process):
        if ismodule(mod):
            for func in mod.__all__:
                d[func] = mod.__dict__[func]
    d["g"] = g
    d["np"] = np
    d["scipy"] = scipy
    d["pg"] = pg
    d["plot"] = pg.plot
    d["Window"] = window.Window
    d["open_rois"] = open_rois
    return d
