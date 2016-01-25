# -*- coding: utf-8 -*-
"""
Created on Wed Jul 23 12:05:56 2014

@author: Kyle Ellefsen
"""

import pkgutil
import process
import global_vars as g
import numpy as np
import scipy
import pyqtgraph as pg
import window
import sys


def getnamespace():
    """
    This function gets the namespace for the script interpreter.  It goes through all the modules in the 'process' and 'analyze' packages and loads all the objects defined in their '__all__' variables. 
    """
    if sys.version_info.major==2:
        namespace=[g]
        for importer, modname, ispkg in pkgutil.iter_modules(process.__path__):
            exec('import {}.{}'.format(process.__name__,modname))
            exec('module={}.{}'.format(process.__name__,modname))
            exec("from {}.{} import *".format(process.__name__,modname))
            for f in module.__all__:
                exec("namespace.append({})".format(f))
        
        from roi import load_roi
        namespace.append(load_roi)
        d=dict()
        for n in namespace:
            d[n.__name__]=n
        d['g']=g
        d['np']=np
        d['scipy']=scipy
        d['pg']=pg
        d['plot']=pg.plot
        d['Window']=window.Window
        return d
    elif sys.version_info.major==3:
        namespace=[g]
        for importer, modname, ispkg in pkgutil.iter_modules(process.__path__):
            exec('import {}.{}'.format(process.__name__,modname))
            exec("from {}.{} import *".format(process.__name__,modname))
            print(process.__name__)
            print(modname)
            for f in eval('{}.{}.__all__'.format(process.__name__,modname)):
                exec("namespace.append({})".format(f))
        
        from roi import load_roi
        namespace.append(load_roi)
        d=dict()
        for n in namespace:
            d[n.__name__]=n
        d['g']=g
        d['np']=np
        d['scipy']=scipy
        d['pg']=pg
        d['plot']=pg.plot
        d['Window']=window.Window
        return d