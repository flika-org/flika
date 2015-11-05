# -*- coding: utf-8 -*-
"""
Created on Thu Jun 26 19:44:11 2014

@author: Kyle Ellefsen
"""
from __future__ import (absolute_import, division,print_function, unicode_literals)
from future.builtins import (bytes, dict, int, list, object, range, str, ascii, chr, hex, input, next, oct, open, pow, round, super, filter, map, zip)

import numpy as np
import global_vars as g
from process.BaseProcess import BaseProcess
from PyQt4.QtGui import *
from PyQt4.QtCore import *

__all__ = ['subtract','multiply','power','ratio','absolute_value','subtract_trace']

class Subtract(BaseProcess):
    """ subtract(value, keepSourceWindow=False)
    This takes a value and subtracts it from the current window's image.
    
    Parameters:
        | value (int) -- The number you are subtracting.
    Returns:
        newWindow
    """
    __url__ = ""
    def __init__(self):
        super().__init__()
    def gui(self):
        self.gui_reset()
        value=QDoubleSpinBox()
        if g.m.currentWindow is not None:
            value.setRange(-np.max(g.m.currentWindow.image),np.max(g.m.currentWindow.image))
            value.setValue(np.min(g.m.currentWindow.image))
        self.items.append({'name':'value','string':'Value','object':value})
        self.items.append({'name':'preview','string':'Preview','object':QCheckBox()})
        super().gui()
    def __call__(self,value,keepSourceWindow=False):
        self.start(keepSourceWindow)
        self.newtif=self.tif-value
        self.newname=self.oldname+' - Subtracted '+str(value)
        return self.end()
    def preview(self):
        value=self.getValue('value')
        preview=self.getValue('preview')
        if preview:
            testimage=np.copy(g.m.currentWindow.image[g.m.currentWindow.currentIndex])
            testimage=testimage-value
            g.m.currentWindow.imageview.setImage(testimage,autoLevels=False)
        else:
            g.m.currentWindow.reset()
subtract=Subtract()

class Subtract_trace(BaseProcess):
    """ subtract_trace(keepSourceWindow=False)
    This takes the most recently plotted trace and subtracts it from each corresponding frame.
    
    Parameters:
        | 
    Returns:
        newWindow
    """
    def __init__(self):
        super().__init__()
    def __call__(self,keepSourceWindow=False):
        self.start(keepSourceWindow)
        trace=g.m.tracefig.rois[-1]['roi'].getTrace()
        nDims=len(self.tif.shape)
        if nDims !=3:
            print('Wrong number of dimensions')
            return self.end()
        if self.tif.shape[0]!=len(trace):
            print('Wrong trace length')
            return self.end()
        self.newtif=np.transpose(np.transpose(self.tif)-trace)
        self.newname=self.oldname+' - subtracted trace'
        return self.end()
subtract_trace=Subtract_trace()
    
class Multiply(BaseProcess):
    """ multiply(value, keepSourceWindow=False)
    This takes a value and multiplies it to the current window's image.
    
    Parameters:
        | value (float) -- The number you are multiplying by.
    Returns:
        newWindow
    """
    def __init__(self):
        super().__init__()
    def gui(self):
        self.gui_reset()
        value=QDoubleSpinBox()
        value.setRange(-2**64,2**64)
        self.items.append({'name':'value','string':'Value','object':value})
        self.items.append({'name':'preview','string':'Preview','object':QCheckBox()})
        super().gui()
    def __call__(self,value,keepSourceWindow=False):
        self.start(keepSourceWindow)
        self.newtif=self.tif*value
        self.newname=self.oldname+' - Multiplied '+str(value)
        return self.end()
    def preview(self):
        value=self.getValue('value')
        preview=self.getValue('preview')
        if preview:
            testimage=np.copy(g.m.currentWindow.image[g.m.currentWindow.currentIndex])
            testimage=testimage*value
            g.m.currentWindow.imageview.setImage(testimage,autoLevels=False)
        else:
            g.m.currentWindow.reset()
multiply=Multiply()

class Power(BaseProcess):
    """ power(value, keepSourceWindow=False)
    This raises the current window's image to the power of 'value'.
    
    Parameters:
        | value (int) -- The exponent.
    Returns:
        newWindow
    """
    def __init__(self):
        super().__init__()
    def gui(self):
        self.gui_reset()
        value=QDoubleSpinBox()
        if g.m.currentWindow is not None:
            value.setRange(-100,100)
            value.setValue(1)
        self.items.append({'name':'value','string':'Value','object':value})
        self.items.append({'name':'preview','string':'Preview','object':QCheckBox()})
        super().gui()
    def __call__(self,value,keepSourceWindow=False):
        self.start(keepSourceWindow)
        self.newtif=self.tif**value
        self.newname=self.oldname+' - Power of '+str(value)
        return self.end()
    def preview(self):
        value=self.getValue('value')
        preview=self.getValue('preview')
        if preview:
            testimage=np.copy(g.m.currentWindow.image[g.m.currentWindow.currentIndex])
            testimage=testimage**value
            g.m.currentWindow.imageview.setImage(testimage,autoLevels=False)
        else:
            g.m.currentWindow.reset()
power=Power()
    
class Ratio(BaseProcess):
    """ ratio(first_frame,nFrames,ratio_type, keepSourceWindow=False)
    Takes a set of frames, combines them into a 2D array according to ratio_type, and divides the entire 3D array frame-by-frame by this array.
    
    Parameters:
        | first_frame (int) -- The first frame in the set of frames to be combined
        | nFrames (int) -- The number of frames to be combined.
        | ratio_type (str) -- The method used to combine the frames.  Either 'standard deviation' or 'average'.
    Returns:
        newWindow
    """
    def __init__(self):
        super().__init__()
    def gui(self):
        self.gui_reset()
        nFrames=1
        if g.m.currentWindow is not None:
            nFrames=g.m.currentWindow.image.shape[0]
        first_frame=QSpinBox()
        first_frame.setMaximum(nFrames)
        self.items.append({'name':'first_frame','string':'First Frame','object':first_frame})
        nFrames_spinbox=QSpinBox()
        nFrames_spinbox.setMaximum(nFrames)
        nFrames_spinbox.setMinimum(1)
        self.items.append({'name':'nFrames','string':'Number of Frames','object':nFrames_spinbox})
        ratio_type=QComboBox()
        ratio_type.addItem('average')
        ratio_type.addItem('standard deviation')
        self.items.append({'name':'ratio_type','string':'Ratio Type','object':ratio_type})
        super().gui()
    def __call__(self,first_frame,nFrames,ratio_type,keepSourceWindow=False):
        self.start(keepSourceWindow)
        if ratio_type=='average':
            baseline=self.tif[first_frame:first_frame+nFrames].mean(0)
            baseline[baseline==0]=np.min(np.abs(baseline[baseline!=0])) #This isn't mathematically correct.  I do this to avoid dividing by zero
        elif ratio_type=='standard deviation':
            baseline=self.tif[first_frame:first_frame+nFrames].std(0)
            baseline[baseline==0]=np.min(np.abs(baseline[baseline!=0]))
        self.newtif=self.tif/baseline
        self.newname=self.oldname+' - Ratioed by '+str(ratio_type)
        return self.end()
ratio=Ratio()


class Absolute_value(BaseProcess):
    """ absolute_value(keepSourceWindow=False)
    Takes the absolute value of a set of frames
    
    Parameters:
        | None
    Returns:
        newWindow
    """
    def __init__(self):
        super().__init__()
    def gui(self):
        self.gui_reset()
        if super().gui()==False:
            return False
    def __call__(self,keepSourceWindow=False):
        self.start(keepSourceWindow)
        self.newtif=np.abs(self.tif)
        self.newname=self.oldname+' - Absolute Value'
        return self.end()
absolute_value=Absolute_value()


