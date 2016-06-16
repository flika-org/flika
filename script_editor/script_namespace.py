# -*- coding: utf-8 -*-
"""
Created on Wed Jul 23 12:05:56 2014

@author: Kyle Ellefsen
"""
from inspect import getmembers, ismodule
import process
import global_vars as g
import numpy as np
import scipy
import pyqtgraph as pg
import window
from roi import load_roi


def getnamespace():
    """
    This function gets the namespace for the script interpreter.  It goes through all the modules in the 'process' package and loads all the objects defined in their '__all__' variables.
    """
    namespace =[g]
    modnames = getmembers(process)
    modnames = [mod for mod in modnames if ismodule(mod[1])]
    for modname, mod in modnames:
        exec('import process.{}'.format(modname))
        exec('from process.{} import *'.format(modname))
        for f in mod.__all__:
            exec('namespace.append({})'.format(f))

    namespace.append(load_roi)
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
