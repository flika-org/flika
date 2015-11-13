# -*- coding: utf-8 -*-
"""
Created on Mon Jul 21 10:37:27 2014

@author: Kyle Ellefsen
"""

from __future__ import (absolute_import, division,print_function, unicode_literals)
from future.builtins import (bytes, dict, int, list, object, range, str, ascii, chr, hex, input, next, oct, open, pow, round, super, filter, map, zip)

import numpy as np
import global_vars as g
from process.BaseProcess import BaseProcess, WindowSelector, MissingWindowError
from PyQt4.QtGui import *
from PyQt4.QtCore import *

from .puffAnalyzer import getCentersOfMass, Puffs, PuffAnalyzer


        
class Frame_by_frame_origin(BaseProcess):
    """ frame_by_frame_origin(binary_window, data_window)
    Performs lots of analyses on puffs
    
    Parameters:
        | binary_window (Window)
        | data_window (Window)
    Returns:
        newWindow
    """
    def __init__(self):
        super().__init__()
    def gui(self):
        self.gui_reset()
        binary_window=WindowSelector()
        data_window=WindowSelector()
        self.items.append({'name':'binary_window','string':'Binary window containing puffs','object':binary_window})
        self.items.append({'name':'data_window','string':'Data window containing raw data','object':data_window})
        super().gui()
    def __call__(self,binary_window, data_window,keepSourceWindow=False):

        
        g.m.statusBar().showMessage('Performing {}...'.format(self.__name__))
        if binary_window is None or data_window is None:
            raise(MissingWindowError("You cannot execute '{}' without selecting a window first.".format(self.__name__)))
        if set(np.unique(binary_window.image.astype(np.int)))!=set([0,1]): #tests if image is not boolean
            msg='The Frame-by-Frame origin analyzer requires a binary window as input.  Select a binary window.'
            g.m.statusBar().showMessage(msg)
            self.msgBox = QMessageBox()
            self.msgBox.setText(msg)
            self.msgBox.show()
            return
            
            
        positions,bounds=getCentersOfMass(binary_window.image,data_window.image)
        puffs=Puffs(positions,bounds,data_window.image)
        puffAnalyzer = PuffAnalyzer(puffs)
        puffAnalyzer.linkTif(data_window)
        g.m.statusBar().showMessage('Finished with {}.'.format(self.__name__))
        return puffAnalyzer

frame_by_frame_origin=Frame_by_frame_origin()

def frame_by_frame_gui():
    frame_by_frame_origin.gui()