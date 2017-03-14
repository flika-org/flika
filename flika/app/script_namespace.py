# -*- coding: utf-8 -*-
"""
Flika
@author: Kyle Ellefsen
@author: Brett Settle
@license: MIT
"""
from inspect import getmembers, ismodule
import numpy as np
import scipy
import pyqtgraph as pg
from .. import process
from .. import global_vars as g
from .. import window
from ..roi import load_rois


def getnamespace():
    """
    This function gets the namespace for the script interpreter.  It goes through all the modules in the 'process' package and loads all the objects defined in their '__all__' variables.
    """
    namespace =[g]
    modnames = getmembers(process)
    modnames = [mod for mod in modnames if ismodule(mod[1])]
    for modname, mod in modnames:
        exec('from .process import {}'.format(modname))
        for f in mod.__all__:
            exec('namespace.append({})'.format(f))

    namespace.append(load_rois)
    d = dict()
    for n in namespace:
        d[n.__name__] = n
    d['g'] = g
    d['np'] = np
    d['scipy'] = scipy
    d['pg'] = pg
    d['plot'] = pg.plot
    d['Window'] = window.Window
    return d
