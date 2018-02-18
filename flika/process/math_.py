# -*- coding: utf-8 -*-
from ..logger import logger
logger.debug("Started 'reading process/math_.py'")
import numpy as np
from qtpy import QtGui, QtWidgets, QtCore
from .. import global_vars as g
from ..utils.BaseProcess import BaseProcess, CheckBox, ComboBox
from ..window import Window

__all__ = ['subtract','multiply','divide','power','ratio','absolute_value','subtract_trace','divide_trace', 'sqrt']


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
        value (int): The number you are subtracting.
    Returns:
        newWindow
    """
    __url__ = ""
    def __init__(self):
        super().__init__()
    def gui(self):
        self.gui_reset()
        value=QtWidgets.QDoubleSpinBox()
        if g.win is not None:
            maxx = np.max(g.win.image) * 100
            minn = -1 * maxx # -np.max sometimes returns abnormal large value
            value.setRange(minn, maxx)
            value.setValue(np.min(g.win.image))
        self.items.append({'name':'value','string':'Value','object':value})
        self.items.append({'name':'preview','string':'Preview','object':CheckBox()})
        super().gui()
    def __call__(self,value,keepSourceWindow=False):
        self.start(keepSourceWindow)
        if hasattr(value,'is_integer') and value.is_integer():
            value = int(value)
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
            testimage=np.copy(g.win.image[g.win.currentIndex])
            testimage=testimage-value
            g.win.imageview.setImage(testimage,autoLevels=False)
        else:
            g.win.reset()
subtract=Subtract()

class Subtract_trace(BaseProcess):
    """ subtract_trace(keepSourceWindow=False)

    This takes the most recently plotted trace and subtracts it from each corresponding frame.

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
        value (float): The number you are multiplying by.
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
        self.newtif = self.tif*value
        self.newname = self.oldname+' - Multiplied by '+str(value)
        return self.end()
    def preview(self):
        value=self.getValue('value')
        preview=self.getValue('preview')
        if preview:
            testimage=np.copy(g.win.image[g.win.currentIndex])
            testimage=testimage*value
            g.win.imageview.setImage(testimage,autoLevels=False)
        else:
            g.win.reset()
multiply=Multiply()


class Divide(BaseProcess):
    """ divide(value, keepSourceWindow=False)

    This takes a value and divides it to the current window's image.

    Parameters:
        value (float): The number you are dividing by.
    Returns:
        newWindow
    """

    def __init__(self):
        super().__init__()

    def gui(self):
        self.gui_reset()
        value = QtWidgets.QDoubleSpinBox()
        value.setRange(-2 ** 64, 2 ** 64)
        self.items.append({'name': 'value', 'string': 'Value', 'object': value})
        self.items.append({'name': 'preview', 'string': 'Preview', 'object': CheckBox()})
        super().gui()

    def __call__(self, value, keepSourceWindow=False):
        self.start(keepSourceWindow)
        self.newtif = self.tif / value
        self.newname = self.oldname + ' - Divided by ' + str(value)
        return self.end()

    def preview(self):
        value = self.getValue('value')
        preview = self.getValue('preview')
        if preview:
            testimage = np.copy(g.win.image[g.win.currentIndex])
            testimage = testimage / value
            g.win.imageview.setImage(testimage, autoLevels=False)
        else:
            g.win.reset()


divide = Divide()

class Power(BaseProcess):
    """ power(value, keepSourceWindow=False)

    This raises the current window's image to the power of 'value'.
    
    Parameters:
        value (int): The exponent.
    Returns:
        newWindow
    """
    def __init__(self):
        super().__init__()
    def gui(self):
        self.gui_reset()
        value=QtWidgets.QDoubleSpinBox()
        if g.win is not None:
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
            testimage=np.copy(g.win.image[g.win.currentIndex])
            testimage=testimage**value
            g.win.imageview.setImage(testimage,autoLevels=False)
        else:
            g.win.reset()
power=Power()

class Sqrt(BaseProcess):
    """ sqrt(value, keepSourceWindow=False)

    This takes the square root of the current window's image.
    In this function, the square root of a negative number is set to 0.
    
    Parameters:
        value (int): The exponent.
    Returns:
        newWindow
    """
    def __init__(self):
        super().__init__()
    def gui(self):
        self.gui_reset()
        self.items.append({'name':'preview', 'string':'Preview', 'object':CheckBox()})
        super().gui()
    def __call__(self, keepSourceWindow=False):
        self.start(keepSourceWindow)
        A = np.copy(self.tif)
        A[A<0] = 0
        self.newtif = np.sqrt(A)
        self.newname = self.oldname+' - Sqrt '
        return self.end()
    def preview(self):
        preview = self.getValue('preview')
        if preview:
            A = np.copy(g.win.image[g.win.currentIndex])
            A[A<0] = 0
            A = np.sqrt(A)
            g.win.imageview.setImage(A, autoLevels=False)
        else:
            g.win.reset()
sqrt = Sqrt()
    
class Ratio(BaseProcess):
    """ ratio(first_frame, nFrames, ratio_type, black_level, keepSourceWindow=False)

    Takes a set of frames, combines them into a 2D array according to ratio_type, and divides the entire 3D array frame-by-frame by this array.
    
    Parameters:
        first_frame (int): The first frame in the set of frames to be combined
        nFrames (int): The number of frames to be combined.
        ratio_type (str): The method used to combine the frames.  Either 'standard deviation' or 'average'.
        black_level (float): The value to subtract from the entire movie prior to the ratio operation.
    Returns:
        newWindow
    """
    def __init__(self):
        super().__init__()

    def gui(self):
        self.gui_reset()
        nFrames = 1
        if g.win is not None:
            nFrames = g.win.image.shape[0]
        first_frame = QtWidgets.QSpinBox()
        first_frame.setMaximum(nFrames)
        self.items.append({'name': 'first_frame', 'string': 'First Frame', 'object': first_frame})
        nFrames_spinbox = QtWidgets.QSpinBox()
        nFrames_spinbox.setMaximum(nFrames)
        nFrames_spinbox.setMinimum(1)
        self.items.append({'name': 'nFrames', 'string': 'Number of Frames', 'object': nFrames_spinbox})
        ratio_type = ComboBox()
        ratio_type.addItem('average')
        ratio_type.addItem('standard deviation')
        self.items.append({'name': 'ratio_type', 'string': 'Ratio Type', 'object': ratio_type})
        black_level = QtWidgets.QDoubleSpinBox()
        black_level.setMinimum(0)
        black_level.setMaximum(1000)
        self.items.append({'name': 'black_level', 'string': 'Black Level', 'object': black_level})
        super().gui()

    def __call__(self, first_frame, nFrames, ratio_type, black_level=0, keepSourceWindow=False):
        self.start(keepSourceWindow)
        if self.oldwindow.volume is None:
            A = self.tif - black_level
        else:
            A = self.oldwindow.volume - black_level
        if ratio_type == 'average':
            baseline = A[first_frame:first_frame+nFrames].mean(0)
            baseline[baseline == 0] = np.min(np.abs(baseline[baseline != 0])) # This isn't mathematically correct.  I do this to avoid dividing by zero
        elif ratio_type == 'standard deviation':
            baseline = A[first_frame:first_frame+nFrames].std(0)
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


logger.debug("Completed 'reading process/math_.py'")