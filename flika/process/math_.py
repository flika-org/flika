# -*- coding: utf-8 -*-
"""
Created on Thu Jun 26 19:44:11 2014

@author: Kyle Ellefsen
"""
import numpy as np
import flika.global_vars as g
from flika.process.BaseProcess import BaseProcess, ComboBox, CheckBox
from qtpy import QtWidgets

__all__ = ['subtract','multiply','power','ratio','absolute_value','subtract_trace','divide_trace']
from flika.window import Window

def upgrade_dtype(dtype):
    if dtype==np.uint8:
        return np.uint16
    elif dtype==np.uint16:
        return np.uint32
    elif dtype==np.uint32:
        return np.uint64
    elif dtype==np.uint64:
        return np.int8
    elif dtype==np.int8:
        return np.int16
    elif dtype==np.int16:
        return np.int32
    elif dtype==np.int32:
        return np.int64
    elif dtype==np.float16:
        return np.float32
    elif dtype==np.float32:
        return np.float64

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
        value=QtWidgets.QDoubleSpinBox()
        if g.currentWindow is not None:
            value.setRange(-1 * np.max(g.currentWindow.image),np.max(g.currentWindow.image)) # -np.max sometimes returns abnormal large value
            value.setValue(np.min(g.currentWindow.image))
        self.items.append({'name':'value','string':'Value','object':value})
        self.items.append({'name':'preview','string':'Preview','object':CheckBox()})
        super().gui()
    def __call__(self,value,keepSourceWindow=False):
        self.start(keepSourceWindow)
        if hasattr(value,'is_integer') and value.is_integer():
            value=int(value)
        if np.issubdtype(self.tif.dtype,np.integer):
            ddtype=np.iinfo(self.tif.dtype)
            while np.min(self.tif)-value<ddtype.min or np.max(self.tif)-value>ddtype.max: # if we exceed the bounds of the datatype
                ddtype=np.iinfo(upgrade_dtype(ddtype.dtype))
            self.newtif=self.tif.astype(ddtype.dtype)-value
        else:
            self.newtif=self.tif-value
        self.newname=self.oldname+' - Subtracted '+str(value)
        return self.end()
    def preview(self):
        value=self.getValue('value')
        preview=self.getValue('preview')
        if preview:
            testimage=np.copy(g.currentWindow.image[g.currentWindow.currentIndex])
            testimage=testimage-value
            g.currentWindow.imageview.setImage(testimage,autoLevels=False)
        else:
            g.currentWindow.reset()
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
        trace=g.currentTrace.rois[-1]['roi'].getTrace()
        nDims=len(self.tif.shape)
        if nDims !=3:
            g.alert('Wrong number of dimensions')
            return self.end()
        if self.tif.shape[0]!=len(trace):
            g.alert('Wrong trace length')
            return self.end()
        self.newtif=np.transpose(np.transpose(self.tif)-trace)
        self.newname=self.oldname+' - subtracted trace'
        return self.end()
subtract_trace=Subtract_trace()

class Divide_trace(BaseProcess):
    """ divide_trace(keepSourceWindow=False)
    This takes the most recently plotted trace and divides each pixel in the current Window by its value.
    
    Parameters:
        | 
    Returns:
        newWindow
    """
    def __init__(self):
        super().__init__()
    def __call__(self,keepSourceWindow=False):
        self.start(keepSourceWindow)
        trace=g.currentTrace.rois[-1]['roi'].getTrace()
        nDims=len(self.tif.shape)
        if nDims !=3:
            g.alert('Wrong number of dimensions')
            return self.end()
        if self.tif.shape[0]!=len(trace):
            g.alert('Wrong trace length')
            return self.end()
        self.newtif=np.transpose(np.transpose(self.tif)/trace)
        self.newname=self.oldname+' - divided trace'
        return self.end()
divide_trace=Divide_trace()
    
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
        value=QtWidgets.QDoubleSpinBox()
        value.setRange(-2**64,2**64)
        self.items.append({'name':'value','string':'Value','object':value})
        self.items.append({'name':'preview','string':'Preview','object':CheckBox()})
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
            testimage=np.copy(g.currentWindow.image[g.currentWindow.currentIndex])
            testimage=testimage*value
            g.currentWindow.imageview.setImage(testimage,autoLevels=False)
        else:
            g.currentWindow.reset()
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
        value=QtWidgets.QDoubleSpinBox()
        if g.currentWindow is not None:
            value.setRange(-100,100)
            value.setValue(1)
        self.items.append({'name':'value','string':'Value','object':value})
        self.items.append({'name':'preview','string':'Preview','object':CheckBox()})
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
            testimage=np.copy(g.currentWindow.image[g.currentWindow.currentIndex])
            testimage=testimage**value
            g.currentWindow.imageview.setImage(testimage,autoLevels=False)
        else:
            g.currentWindow.reset()
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
        if g.currentWindow is not None:
            nFrames=g.currentWindow.image.shape[0]
        first_frame=QtWidgets.QSpinBox()
        first_frame.setMaximum(nFrames)
        self.items.append({'name':'first_frame','string':'First Frame','object':first_frame})
        nFrames_spinbox=QtWidgets.QSpinBox()
        nFrames_spinbox.setMaximum(nFrames)
        nFrames_spinbox.setMinimum(1)
        self.items.append({'name':'nFrames','string':'Number of Frames','object':nFrames_spinbox})
        ratio_type=ComboBox()
        ratio_type.addItem('average')
        ratio_type.addItem('standard deviation')
        self.items.append({'name':'ratio_type','string':'Ratio Type','object':ratio_type})
        super().gui()
    def __call__(self,first_frame,nFrames,ratio_type,keepSourceWindow=False):
        self.start(keepSourceWindow)
        if self.oldwindow.volume is None:
            A = self.tif
        else:
            A = self.oldwindow.volume
        if ratio_type=='average':
            baseline=A[first_frame:first_frame+nFrames].mean(0)
            baseline[baseline == 0] = np.min(np.abs(baseline[baseline != 0])) #This isn't mathematically correct.  I do this to avoid dividing by zero
        elif ratio_type=='standard deviation':
            baseline=A[first_frame:first_frame+nFrames].std(0)
            baseline[baseline == 0] = np.min(np.abs(baseline[baseline != 0]))
        else:
            g.alert("'{}' is an unknown ratio_type.  Try 'average' or 'standard deviation'".format(ratio_type))
            return None

        newA = (A/baseline).astype(g.settings['internal_data_type'])
        if self.oldwindow.volume is None:
            self.newtif=newA
            self.newname=self.oldname+' - Ratioed by '+str(ratio_type)
            return self.end()
        else:
            from plugins.light_sheet_analyzer.light_sheet_analyzer import Volume_Viewer
            self.newtif = np.squeeze(newA[:, 0, :, :])
            self.newname = self.oldname + ' - Ratioed by ' + str(ratio_type)
            w = self.end()
            w.volume = newA
            Volume_Viewer(w)
            return w
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


