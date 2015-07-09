# -*- coding: utf-8 -*-
"""
Created on Wed Jul 23 12:05:56 2014

@author: Kyle Ellefsen
"""

import pkgutil
import process, analyze
import global_vars as g
import numpy as np
import scipy
import pyqtgraph as pg
from window import Window
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
        from analyze.puffs.frame_by_frame_origin import frame_by_frame_origin
        namespace.append(frame_by_frame_origin)     
        from analyze.puffs.average_origin import average_origin
        namespace.append(average_origin)
        from analyze.puffs.threshold_cluster import threshold_cluster
        namespace.append(threshold_cluster)
        d=dict()
        for n in namespace:
            d[n.__name__]=n
        d['g']=g
        d['np']=np
        d['scipy']=scipy
        d['pg']=pg
        d['plot']=pg.plot
        d['Window']=Window
        return d
    elif sys.version_info.major==3:
        namespace=[g]
        for importer, modname, ispkg in pkgutil.iter_modules(process.__path__):
            exec('import {}.{}'.format(process.__name__,modname))
            exec("from {}.{} import *".format(process.__name__,modname))
            for f in eval('{}.{}.__all__'.format(process.__name__,modname)):
                exec("namespace.append({})".format(f))
        
        from roi import load_roi
        namespace.append(load_roi)
        from analyze.puffs.frame_by_frame_origin import frame_by_frame_origin
        namespace.append(frame_by_frame_origin)     
        from analyze.puffs.average_origin import average_origin
        namespace.append(average_origin)
        from analyze.puffs.threshold_cluster import threshold_cluster
        namespace.append(threshold_cluster)
        d=dict()
        for n in namespace:
            d[n.__name__]=n
        d['g']=g
        d['np']=np
        d['scipy']=scipy
        d['pg']=pg
        d['plot']=pg.plot
        d['Window']=Window
        return d