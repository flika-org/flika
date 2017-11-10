# -*- coding: utf-8 -*-
from ..logger import logger
logger.debug("Started 'reading process/roi.py'")
import numpy as np
import skimage
from qtpy import QtWidgets
from .. import global_vars as g
from ..utils.BaseProcess import BaseProcess, CheckBox


__all__ = ['set_value']

class Set_value(BaseProcess):
    """ set_value(value, firstFrame, lastFrame, restrictToROI=False, restrictToOutside=False, keepSourceWindow=False)

    This sets the value from firstFrame to lastFrame to value.
    
    Parameters:
        value (int): The desired value
        firstFrame (int): The first frame whos value you are setting
        lastFrame (int): The last frame whos value you are altering
        restrictToROI (bool): Whether or not only the current ROI will be effected.
    Returns:
        newWindow
    """
    def __init__(self):
        super().__init__()
    def gui(self):
        self.gui_reset()
        value=QtWidgets.QDoubleSpinBox()
        if g.win is not None:
            value.setRange(-2**64,2**64)
            value.setValue(0)
            firstFrame=QtWidgets.QSpinBox()
            firstFrame.setRange(0,len(g.win.image)-1)
            lastFrame=QtWidgets.QSpinBox()
            lastFrame.setRange(0,len(g.win.image)-1)
            lastFrame.setValue(len(g.win.image)-1)
        self.items.append({'name': 'value',             'string': 'Value',                   'object': value})
        self.items.append({'name': 'firstFrame',        'string': 'First Frame',             'object': firstFrame})
        self.items.append({'name': 'lastFrame',         'string': 'Last Frame',              'object': lastFrame})
        self.items.append({'name': 'restrictToROI',     'string': 'Restrict to current ROI', 'object': CheckBox()})
        self.items.append({'name': 'restrictToOutside', 'string': 'Restrict to everything outside current ROI','object': CheckBox()})
        super().gui()
    def __call__(self,value,firstFrame,lastFrame,restrictToROI=False, restrictToOutside=False, keepSourceWindow=False):
        self.start(keepSourceWindow)
        self.newtif=np.copy(self.tif)
        nDim = len(self.tif.shape)
        if nDim == 3:
            mt, mx, my=self.tif.shape
        elif nDim == 2:
            mx, my = self.tif.shape
        if restrictToROI:
            roi = g.win.currentROI
            xx, yy = roi.getMask()
            if nDim == 2:
                self.newtif[xx,yy]=value
            elif nDim == 3:
                for i in np.arange(firstFrame,lastFrame+1):
                    self.newtif[i][xx,yy]=value
        elif restrictToOutside:
            roi=g.win.currentROI
            roi.pts = roi.getPoints()
            x=np.array([p[0] for p in roi.pts])
            y=np.array([p[1] for p in roi.pts])
            xx,yy=skimage.draw.polygon(x,y)
            inside_bounds=(xx>=0) & (yy>=0) & (xx<mx) & (yy<my)
            xx=xx[inside_bounds]
            yy=yy[inside_bounds]
            mask=np.ones((mx,my),np.bool)
            mask[xx,yy]=False
            if nDim==2:
                self.newtif[mask]=value
            elif nDim==3:
                for i in np.arange(firstFrame,lastFrame+1):
                    self.newtif[i][mask]=value
        
        else:
            if nDim==2:
                self.newtif[:] = value
            elif nDim==3:
                self.newtif[firstFrame:lastFrame+1] = value
        self.newname=self.oldname+' - value set to '+str(value)
        return self.end()
set_value=Set_value()

logger.debug("Completed 'reading process/roi.py'")