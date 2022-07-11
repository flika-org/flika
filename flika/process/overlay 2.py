# -*- coding: utf-8 -*-
from ..logger import logger
logger.debug("Started 'reading process/overlay.py'")
import numpy as np
import pyqtgraph as pg
from qtpy import QtWidgets, QtCore, QtGui
from .. import global_vars as g
from ..utils.BaseProcess import BaseProcess, SliderLabel, WindowSelector,  MissingWindowError, CheckBox, ComboBox

__all__ = ['time_stamp','background','scale_bar']
     


class Time_Stamp(BaseProcess):
    """time_stamp(framerate,show=True)

    Adds a time stamp to a movie
    
    Parameters:
        framerate (float): The number of frames per second
        show (bool): Turns on or off the time stamp
    Returns:
        None
    """
    def __init__(self):
        super().__init__()
    def gui(self):
        self.gui_reset()
        framerate=QtWidgets.QDoubleSpinBox()
        if hasattr(g.win,'framerate'):
            framerate.setValue(g.win.framerate)
        elif 'framerate' in g.settings.d.keys():
            framerate.setValue(g.settings['framerate'])
        framerate.setRange(0,1000000)
        framerate.setDecimals(10)
        show = CheckBox(); show.setChecked(True)
        self.items.append({'name':'framerate','string':'Frame Rate (Hz)','object':framerate})
        self.items.append({'name':'show','string':'Show','object':show})
        super().gui()
    def __call__(self,framerate,show=True,keepSourceWindow=None):
        w=g.win
        if show:
            w.framerate=framerate
            g.settings['framerate']=framerate
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


class ShowCheckbox(CheckBox):

    def __init__(self, opacity_slider, parent=None):
        super().__init__(parent)
        self.stateChanged.connect(self.changed)
        self.opacity_slider = opacity_slider

    def changed(self, state):
        if state == 0:  # unchecked
            self.opacity_slider.setEnabled(True)
        if state == 2:  # checked
            self.opacity_slider.setEnabled(False)


class Background(BaseProcess):
    """ background(background_window, data_window)

    Overlays the background_window onto the data_window
    
    Parameters:
        background_window (Window)
        data_window (Window)
    Returns:
        None
    """
    def __init__(self):
        super().__init__()
    def gui(self):
        self.gui_reset()
        background_window=WindowSelector()
        data_window=WindowSelector()
        opacity = SliderLabel(3)
        opacity.setRange(0,1)
        opacity.setValue(.5)
        show = ShowCheckbox(opacity)
        show.setChecked(True)
        self.items.append({'name':'background_window','string':'Background window','object':background_window})
        self.items.append({'name':'data_window','string':'Data window','object':data_window})
        self.items.append({'name':'opacity','string':'Opacity','object':opacity})
        self.items.append({'name':'show','string':'Show','object':show})
        super().gui()
    def __call__(self, background_window, data_window, opacity,show,keepSourceWindow=False):
        if background_window is None or data_window is None:
            return
        w=data_window
        if show:
            if hasattr(w, 'bgItem') and w.bgItem is not None:
                w.bgItem.hist_luttt.hide()
                w.imageview.ui.gridLayout.removeWidget(w.bgItem.hist_luttt)
                w.imageview.view.removeItem(w.bgItem)
            bgItem = pg.ImageItem(background_window.imageview.imageItem.image)
            bgItem.setOpacity(opacity)
            w.imageview.view.addItem(bgItem)
            bgItem.hist_luttt = pg.HistogramLUTWidget()
            bgItem.hist_luttt.setMinimumWidth(110)
            bgItem.hist_luttt.setImageItem(bgItem)
            w.imageview.ui.gridLayout.addWidget(bgItem.hist_luttt, 0, 4, 1, 4)
            w.bgItem = bgItem
        else:
            if hasattr(w, 'bgItem') and w.bgItem is not None:
                w.bgItem.hist_luttt.hide()
                w.imageview.ui.gridLayout.removeWidget(w.bgItem.hist_luttt)
                w.imageview.view.removeItem(w.bgItem)
                w.bgItem.hist_luttt = None
                w.bgItem = None
            return None
    def preview(self):
        background_window=self.getValue('background_window')
        data_window=self.getValue('data_window')
        opacity=self.getValue('opacity')
        show=self.getValue('show')
        self.__call__(background_window,data_window,opacity,show)
        
background=Background()

class Scale_Bar(BaseProcess):
    ''' scale_bar(width_microns, width_pixels, font_size, color, background, location, show=True)

    Parameters:
        width_microns (float): width in microns
        width_pixels (float): width in pixels
        font_size (int): size of the font
        color (string): ['Black', White']
        background (string): ['Black','White', 'None']
        location (string): ['Lower Right','Lower Left','Top Right','Top Left']
        show (bool): controls whether the Scale_bar is displayed or not
    '''
    
    def __init__(self):
        super().__init__()
    def gui(self):
        self.gui_reset()
        w=g.win
        width_microns=QtWidgets.QDoubleSpinBox()
        
        width_pixels=QtWidgets.QSpinBox()
        width_pixels.setRange(.001,1000000)
        width_pixels.setRange(1,w.mx)
        
        font_size=QtWidgets.QSpinBox()
        
        color=ComboBox()
        color.addItem("White")
        color.addItem("Black")
        background=ComboBox()
        background.addItem('None')
        background.addItem('Black')
        background.addItem('White')
        location=ComboBox()
        location.addItem('Lower Right')
        location.addItem('Lower Left')
        location.addItem('Top Right')
        location.addItem('Top Left')
        show=CheckBox()
        if hasattr(w,'scaleBarLabel') and w.scaleBarLabel is not None: #if the scaleBarLabel already exists
            props=w.scaleBarLabel.flika_properties
            width_microns.setValue(props['width_microns'])
            width_pixels.setValue(props['width_pixels'])
            font_size.setValue(props['font_size'])
            color.setCurrentIndex(color.findText(props['color']))
            background.setCurrentIndex(background.findText(props['background']))
            location.setCurrentIndex(location.findText(props['location']))
        else:
            font_size.setValue(12)
            width_pixels.setValue(int(w.mx/8))
            width_microns.setValue(1)
            
        show.setChecked(True) 
        self.items.append({'name':'width_microns','string':'Width of bar in microns','object':width_microns})
        self.items.append({'name':'width_pixels','string':'Width of bar in pixels','object':width_pixels})
        self.items.append({'name':'font_size','string':'Font size','object':font_size})
        self.items.append({'name':'color','string':'Color','object':color})
        self.items.append({'name':'background','string':'Background','object':background})
        self.items.append({'name':'location','string':'Location','object':location})
        self.items.append({'name':'show','string':'Show','object':show})
        
        super().gui()
        self.preview()
    def __call__(self,width_microns, width_pixels, font_size, color, background,location,show=True,keepSourceWindow=None):
        w=g.win
        if show:
            if hasattr(w,'scaleBarLabel') and w.scaleBarLabel is not None:
                w.imageview.view.removeItem(w.scaleBarLabel.bar)
                w.imageview.view.removeItem(w.scaleBarLabel)
                w.imageview.view.sigResized.disconnect(self.updateBar)
            if location=='Top Left':
                anchor=(0,0)
                pos=[0,0]
            elif location=='Top Right':
                anchor=(0,0)
                pos=[w.mx,0]
            elif location=='Lower Right':
                anchor=(0,0)
                pos=[w.mx,w.my]
            elif location=='Lower Left':
                anchor=(0,0)
                pos=[0,w.my]
            w.scaleBarLabel= pg.TextItem(anchor=anchor, html="<span style='font-size: {}pt;color:{};background-color:{};'>{} μm</span>".format(font_size, color, background,width_microns))
            w.scaleBarLabel.setPos(pos[0],pos[1])
            w.scaleBarLabel.flika_properties={item['name']:item['value'] for item in self.items}
            w.imageview.view.addItem(w.scaleBarLabel)
            if color=='White':
                color255=[255,255,255,255]
            elif color=='Black':
                color255=[0,0,0,255]
            textRect=w.scaleBarLabel.boundingRect()
            
            if location=='Top Left':
                barPoint=QtCore.QPoint(0, textRect.height())
            elif location=='Top Right':
                barPoint=QtCore.QPoint(-width_pixels, textRect.height())
            elif location=='Lower Right':
                barPoint=QtCore.QPoint(-width_pixels, -textRect.height())
            elif location=='Lower Left':
                barPoint=QtCore.QPoint(0, -textRect.height())
                
            bar = QtWidgets.QGraphicsRectItem(QtCore.QRectF(barPoint, QtCore.QSizeF(width_pixels,int(font_size/3))))
            bar.setPen(pg.mkPen(color255)); bar.setBrush(pg.mkBrush(color255))
            w.imageview.view.addItem(bar)
            #bar.setParentItem(w.scaleBarLabel)
            w.scaleBarLabel.bar=bar
            w.imageview.view.sigResized.connect(self.updateBar)
            self.updateBar()
            
        else:
            if hasattr(w,'scaleBarLabel') and w.scaleBarLabel is not None:
                w.imageview.view.removeItem(w.scaleBarLabel.bar)
                w.imageview.view.removeItem(w.scaleBarLabel)
                w.scaleBarLabel=None
                w.imageview.view.sigResized.disconnect(self.updateBar)
        return None
        
    def updateBar(self):
        w=g.win
        width_pixels=self.getValue('width_pixels')
        location=self.getValue('location')
        view = w.imageview.view
        textRect=w.scaleBarLabel.boundingRect()
        textWidth=textRect.width()*view.viewPixelSize()[0]
        textHeight=textRect.height()*view.viewPixelSize()[1]
        
        if location=='Top Left':
            barPoint=QtCore.QPoint(0, 1.3*textHeight)
            w.scaleBarLabel.setPos(QtCore.QPointF(width_pixels/2-textWidth/2,0))
        elif location=='Top Right':
            barPoint=QtCore.QPoint(w.mx-width_pixels, 1.3*textHeight)
            w.scaleBarLabel.setPos(QtCore.QPointF(w.mx-width_pixels/2-textWidth/2,0))
        elif location=='Lower Right':
            barPoint=QtCore.QPoint(w.mx-width_pixels, w.my-1.3*textHeight)
            w.scaleBarLabel.setPos(QtCore.QPointF(w.mx-width_pixels/2-textWidth/2,w.my-textHeight))
        elif location=='Lower Left':
            barPoint=QtCore.QPoint(0, w.my-1.3*textHeight)
            w.scaleBarLabel.setPos(QtCore.QPointF(QtCore.QPointF(width_pixels/2-textWidth/2,w.my-textHeight)))
        w.scaleBarLabel.bar.setRect(QtCore.QRectF(barPoint, QtCore.QSizeF(width_pixels,textHeight/4)))
        
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



logger.debug("Completed 'reading process/overlay.py'")



