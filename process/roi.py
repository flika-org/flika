# -*- coding: utf-8 -*-
"""
Created on Mon Jul 21 09:53:16 2014

@author: Kyle Ellefsen
"""

from __future__ import (absolute_import, division,print_function, unicode_literals)
from future.builtins import (bytes, dict, int, list, object, range, str, ascii, chr, hex, input, next, oct, open, pow, round, super, filter, map, zip)

import numpy as np
import global_vars as g
from process.BaseProcess import BaseProcess
from PyQt4.QtGui import *
from PyQt4.QtCore import *
import cv2 

__all__ = ['set_value']

class Set_value(BaseProcess):
    """ set_value(value, firstFrame, lastFrame, restrictToROI=False, keepSourceWindow=False)
    This sets the value from firstFrame to lastFrame to value.
    
    Parameters:
        | value (int) -- The desired value
        | firstFrame (int) -- The first frame whos value you are setting
        | lastFrame (int) -- The last frame whos value you are altering
        | restrictToROI (bool) -- Whether or not only the current ROI will be effected.
    Returns:
        newWindow
    """
    def __init__(self):
        super().__init__()
    def gui(self):
        self.gui_reset()
        value=QDoubleSpinBox()
        if g.m.currentWindow is not None:
            value.setRange(-2**64,2**64)
            value.setValue(0)
            firstFrame=QSpinBox()
            firstFrame.setRange(0,len(g.m.currentWindow.image)-1)
            lastFrame=QSpinBox()
            lastFrame.setRange(0,len(g.m.currentWindow.image)-1)
            lastFrame.setValue(len(g.m.currentWindow.image)-1)
        self.items.append({'name':'value','string':'Value','object':value})
        self.items.append({'name':'firstFrame','string':'First Frame','object':firstFrame})
        self.items.append({'name':'lastFrame','string':'Last Frame','object':lastFrame})
        self.items.append({'name':'restrictToROI','string':'Restrict to current ROI','object':QCheckBox()})
        self.items.append({'name':'restrictToOutside','string':'Restrict to everything outside current ROI','object':QCheckBox()})
        super().gui()
    def __call__(self,value,firstFrame,lastFrame,restrictToROI=False, restrictToOutside=False, keepSourceWindow=False):
        self.start(keepSourceWindow)
        self.newtif=np.copy(self.tif)
        nDim=len(self.tif.shape)
        if nDim==3:
            mt,mx,my=self.tif.shape
        elif nDim==2:
            mx,my=self.tif.shape
        if restrictToROI:
            roi=g.m.currentWindow.currentROI
            roi.pts=roi.getPoints()
            cnt=np.array([np.array([np.array([p[1],p[0]])]) for p in roi.pts ])
            mask=np.zeros((mx,my),np.uint8)
            cv2.drawContours(mask,[cnt],0,255,-1)
            if nDim==2:
                self.newtif[mask.astype(np.bool)]=value
            elif nDim==3:
                for i in np.arange(firstFrame,lastFrame+1):
                    self.newtif[i][mask.astype(np.bool)]=value
        elif restrictToOutside:
            roi=g.m.currentWindow.currentROI
            roi.pts=roi.getPoints()
            cnt=np.array([np.array([np.array([p[1],p[0]])]) for p in roi.pts ])
            mask=255*np.ones((mx,my),np.uint8)
            cv2.drawContours(mask,[cnt],0,0,-1)
            if nDim==2:
                self.newtif[mask.astype(np.bool)]=value
            elif nDim==3:
                for i in np.arange(firstFrame,lastFrame+1):
                    self.newtif[i][mask.astype(np.bool)]=value
        
        else:
            if nDim==2:
                self.newtif=value
            elif nDim==3:
                self.newtif[firstFrame:lastFrame+1]=value
        self.newname=self.oldname+' - value set to '+str(value)
        return self.end()
set_value=Set_value()

