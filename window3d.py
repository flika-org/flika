# -*- coding: utf-8 -*-
"""
Created on Thu Jun 26 16:10:00 2014

@author: Kyle Ellefsen
"""
from __future__ import (absolute_import, division,print_function, unicode_literals)
from future.builtins import (bytes, dict, int, list, object, range, str, ascii, chr, hex, input, next, oct, open, pow, round, super, filter, map, zip)

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtCore import pyqtSignal as Signal
import pyqtgraph as pg
pg.setConfigOptions(useWeave=False)
import os, time
import numpy as np
from trace import TraceFig
import global_vars as g
import pyqtgraph.opengl as gl

class Window3D(QWidget):
    closeSignal=Signal()
    keyPressSignal=Signal(QEvent)
    deleteButtonSignal=Signal()
    name = "3D Plot View"
    def __init__(self):
        QWidget.__init__(self)
       
        if g.m.currentWindow is None:
            width=684
            height=585
            nwindows=len(g.m.windows)
            x=10+10*nwindows
            y=484+10*nwindows
        else:
            oldGeometry=g.m.currentWindow.geometry()
            width=oldGeometry.width()
            height=oldGeometry.height()
            x=oldGeometry.x()+10
            y=oldGeometry.y()+10
        self.setCurrentWindow()
        self.view=gl.GLViewWidget(self)
        self.view.installEventFilter(self)

        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.view)
        self.layout.setContentsMargins(0,0,0,0)
        self.setGeometry(QRect(x, y, width, height))
        self.scatterPoints=[[]]
        self.scatterPlot=gl.GLScatterPlotItem(pos=np.array([[0, 0, 0]]), size=3, color=(0,0,0, 255))  #this is the plot that all the red points will be drawn on
        self.view.addItem(self.scatterPlot)
        self.pasteAct = QAction("&Paste", self, triggered=self.paste)
        g.widgetCreated(self)
        if self not in g.m.windows:
            g.m.windows.append(self)
        self.closed=False

    def setCurrentWindow(self):
        g.m.currentWindow = self
        
    def addScatter(self, scatterPoints, clear=False):
        if clear:
            self.scatterPoints = np.array([[]])
        if np.size(self.scatterPoints) > 0:
            self.scatterPoints = np.vstack([self.scatterPoints, scatterPoints])
        else:
            self.scatterPoints = scatterPoints
        self.scatterPlot.setData(pos=np.array(self.scatterPoints), color=(255, 255, 255, 255), size=3)
        self.moveTo(np.average(scatterPoints, 0))

    def moveTo(self, pos=(0, 0, 0), distance = 1000):
        atX, atY, atZ = self.view.cameraPosition()
        self.view.pan(-atX, -atY, -atZ)
        self.view.opts['distance'] = distance
        self.view.opts['center'] = QVector3D(*pos)

    def closeEvent(self, event):
        if self.closed:
            print('This window was already closed')
            event.accept()
        else:
            self.closeSignal.emit()
            if hasattr(self,'image'):
                del self.image
            self.view.close()
            del self.view
            g.m.setWindowTitle("FLIKA")
            if g.m.currentWindow==self:
                g.m.currentWindow = None
            if self in g.m.windows:
                g.m.windows.remove(self)
            self.closed=True
            event.accept() # let the window close
            
    def resizeEvent(self, event):
        event.accept()
        self.view.resize(self.size())

    def reset(self):
        while self.view.items:
            self.view.removeItem(self.view.items[0])
        self.view.addItem(self.scatterPlot)

    def paste(self):
        if isinstance(g.m.clipboard, gl.GLScatterPlotItem):
            return False
        self.addItem(g.m.clipboard)
        
        
    def updateTimeStampLabel(self,frame):
        if self.framerate==0:
            label.setHtml("<span style='font-size: 12pt;color:white;background-color:None;'>Frame rate is 0 Hz</span>" )
        time=frame/self.framerate
        label=self.timeStampLabel
        if time<1:
            time=time*1000
            label.setHtml("<span style='font-size: 12pt;color:white;background-color:None;'>{:.0f} ms</span>".format(time))
        elif time<60:
            label.setHtml("<span style='font-size: 12pt;color:white;background-color:None;'>{:.3f} s</span>".format(time))
        elif time<3600:
            minutes=int(np.floor(time/60))
            seconds=time % 60
            label.setHtml("<span style='font-size: 12pt;color:white;background-color:None;'>{}m {:.3f} s</span>".format(minutes,seconds))
        else:
            hours=int(np.floor(time/3600))
            mminutes=time-hours*3600
            minutes=int(np.floor(mminutes/60))
            seconds=mminutes-minutes*60
            label.setHtml("<span style='font-size: 12pt;color:white;background-color:None;'>{}h {}m {:.3f} s</span>".format(hours,minutes,seconds))
