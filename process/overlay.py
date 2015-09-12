# -*- coding: utf-8 -*-
"""
Created on Wed Sep 17 15:10:30 2014

@author: Kyle Ellefsen
"""

from __future__ import (absolute_import, division,print_function, unicode_literals)
from future.builtins import (bytes, dict, int, list, object, range, str, ascii, chr, hex, input, next, oct, open, pow, round, super, filter, map, zip)

import numpy as np
import global_vars as g
import pyqtgraph as pg

from process.BaseProcess import BaseProcess, SliderLabel, WindowSelector,  MissingWindowError
from PyQt4.QtGui import *
from PyQt4.QtCore import *    

__all__ = ['time_stamp','background','scale_bar']
     


class Time_Stamp(BaseProcess):
    """time_stamp(framerate,show=True)
    Adds a time stamp to a movie
    
    Parameters:
        | framerate (float) -- The number of frames per second
        | show (bool) -- Turns on or off the time stamp
    Returns:
        None
    """
    def __init__(self):
        super().__init__()
    def gui(self):
        self.gui_reset()
        framerate=QDoubleSpinBox()
        if hasattr(g.m.currentWindow,'framerate'):
            framerate.setValue(g.m.currentWindow.framerate)
        elif 'framerate' in g.m.settings.d.keys():
            framerate.setValue(g.m.settings['framerate'])
        framerate.setRange(0,1000000)
        show=QCheckBox(); show.setChecked(True)
        self.items.append({'name':'framerate','string':'Frame Rate (Hz)','object':framerate})
        self.items.append({'name':'show','string':'Show','object':show})
        super().gui()
    def __call__(self,framerate,show=True,keepSourceWindow=None):
        w=g.m.currentWindow
        if show:
            w.framerate=framerate
            g.m.settings['framerate']=framerate
            if hasattr(w,'timeStampLabel') and w.timeStampLabel is not None:
                return
            w.timeStampLabel= pg.TextItem(html="<span style='font-size: 12pt;color:white;background-color:None;'>0 ms</span>")
            w.imageview.view.addItem(w.timeStampLabel)
            w.sigTimeChanged.connect(w.updateTimeStampLabel)
        else:
            if hasattr(w,'timeStampLabel') and w.timeStampLabel is not None:
                w.imageview.view.removeItem(w.timeStampLabel)
                w.timeStampLabel=None
                w.sigTimeChanged.disconnect(w.updateTimeStampLabel)
        return None
    def preview(self):
        framerate=self.getValue('framerate')
        show=self.getValue('show')
        self.__call__(framerate,show)

     
time_stamp=Time_Stamp()

class Background(BaseProcess):
    """ background(background_window, data_window)
    Overlays the background_window onto the data_window
    
    Parameters:
        | background_window (Window)
        | data_window (Window)
    Returns:
        None
    """
    def __init__(self):
        super().__init__()
    def gui(self):
        self.gui_reset()
        background_window=WindowSelector()
        data_window=WindowSelector()
        opacity=SliderLabel(3)
        opacity.setRange(0,1)
        opacity.setValue(.5)
        show=QCheckBox(); show.setChecked(True)
        self.items.append({'name':'background_window','string':'Background window','object':background_window})
        self.items.append({'name':'data_window','string':'Data window','object':data_window})
        self.items.append({'name':'opacity','string':'Opacity','object':opacity})
        self.items.append({'name':'show','string':'Show','object':show})
        super().gui()
    def __call__(self,background_window, data_window, opacity,show,keepSourceWindow=False):
        if background_window is None or data_window is None:
            return
        w=data_window
        if show:
            bg=background_window.image
            bgItem=pg.ImageItem(bg)
            bgItem.setOpacity(opacity)
            if hasattr(w,'bgItem') and w.bgItem is not None:
                w.imageview.view.removeItem(w.bgItem)
            w.bgItem=bgItem
            w.imageview.view.addItem(w.bgItem)
            #lut = np.zeros((256,3), dtype=np.ubyte)
            #lut[:128,0] = np.arange(0,255,2)
            #lut[128:,0] = 255
            #lut[:,1] = np.arange(256)
            #bgItem.setLookupTable(lut)
        else:
            w.imageview.view.removeItem(w.bgItem)
            w.bgItem=None
            return None
    def preview(self):
        background_window=self.getValue('background_window')
        data_window=self.getValue('data_window')
        opacity=self.getValue('opacity')
        show=self.getValue('show')
        self.__call__(background_window,data_window,opacity,show)
        
background=Background()

class Scale_Bar(BaseProcess):
    def __init__(self):
        super().__init__()
    def gui(self):
        print('running')
        self.gui_reset()
        win=g.m.currentWindow
        width_microns=QDoubleSpinBox()
        width_pixels=QSpinBox()
        width_pixels.setRange(.001,1000000)
        width_pixels.setRange(1,win.mx*2)
        width_pixels.setValue(win.mx)
        font_size=QSpinBox()
        font_size.setValue(12)
        color=QComboBox()
        color.addItem("White")
        background=QComboBox()
        background.addItem('None')
        location=QComboBox()
        location.addItem('Lower Right')
        location.addItem('Lower Left')
        location.addItem('Top Right')
        location.addItem('Top Left')

        show=QCheckBox(); show.setChecked(True)
        self.items.append({'name':'width_microns','string':'Width in microns','object':width_microns})
        self.items.append({'name':'width_pixels','string':'Width in pixels','object':width_pixels})
        self.items.append({'name':'font_size','string':'Font size','object':font_size})
        self.items.append({'name':'color','string':'Color','object':color})
        self.items.append({'name':'background','string':'Background','object':background})
        self.items.append({'name':'location','string':'Location','object':location})
        self.items.append({'name':'show','string':'Show','object':show})
        super().gui()
    def __call__(self,width_microns, width_pixels, font_size, color, background,location,show=True,keepSourceWindow=None):
        w=g.m.currentWindow
        if show:
            if hasattr(w,'scaleBarLabel') and w.scaleBarLabel is not None:
                return
            w.scaleBarLabel= pg.TextItem(html="<span style='font-size: {}pt;color:{};background-color:{};'>hihihi</span>".format(font_size, color, background))
            
            w.imageview.view.addItem(w.scaleBarLabel)
        else:
            if hasattr(w,'scaleBarLabel') and w.scaleBarLabel is not None:
                w.imageview.view.removeItem(w.scaleBarLabel)
                w.scaleBarLabel=None
        return None
    def preview(self):
        width_microns=self.getValue('width_microns')
        width_pixels=self.getValue('width_pixels')
        font_size=self.getValue('font_size')
        color=self.getValue('color')
        background=self.getValue('background')
        location=self.getValue('location')
        show=self.getValue('show')
        self.__call__(width_microns, width_pixels, font_size, color, background, location, show)
scale_bar=Scale_Bar()







