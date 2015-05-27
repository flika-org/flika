# -*- coding: utf-8 -*-
"""
Created on Fri Aug 01 14:12:20 2014

@author: Kyle Ellefsen

Run this file in Spyder after you've created a puffAnalyzer
"""
from __future__ import division
from pyqtgraph import plot,show
import pyqtgraph as pg
import numpy as np
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from matplotlib import cm

class OriginPlot(QWidget):
    def __init__(self,image=np.zeros((1,1)), nColors=10,parent=None):
        QWidget.__init__(self,parent)
        self.nColors=nColors
        self.view= pg.GraphicsLayoutWidget()
        self.l = QVBoxLayout()
        self.setLayout(self.l)
        self.l.addWidget(self.view)
        self.show()
        self.w1 = self.view.addPlot()
        self.w1.vb.setAspectLocked(True,ratio=1)
        self.w1.vb.invertY(True)
        self.s1 = pg.ScatterPlotItem(size=5, pen=pg.mkPen(None), brush=pg.mkBrush(255, 255, 255, 120))
        #self.s1.setData(x,y)
        
        self.w1.addItem(pg.ImageItem(image))
        self.w1.addItem(self.s1)
        self.brush_idx=0
        color=np.arange(self.nColors)/self.nColors
        color=np.array(cm.RdYlBu(color))*255
        color[:,3]=200 # set alpha channel
        self.brushes=[pg.mkBrush(QColor(*color[i,:].astype(uint16))) for i in np.arange(self.nColors)]
    def addPoints(self,x,y):
        pos=np.column_stack((x,y))
        #spots={'pos':pos,'data':1,'brush':self.brushes[self.brush_idx]}
        self.brush_idx+=1
        self.brush_idx%=self.nColors
        self.s1.addPoints(pos=pos,data=1,brush=self.brushes[self.brush_idx])
        self.w1.autoRange()


mat=g.m.currentWindow.image[200:300].mean(0)
origins=OriginPlot(mat)

i=0
for puff in g.m.puffAnalyzer.puffs:
    i+=1
    if puff.gaussianFit is None:
        puff.performGaussianFit()
    if puff.kinetics is None:
        puff.calculateKinetics()
    print("{}/{}".format(i,len(g.m.puffAnalyzer.puffs.puffs)))
    x=puff.kinetics['x']
    y=puff.kinetics['y']
    origins.addPoints(x,y)
    
    
    #puff=g.m.puffAnalyzer.puffs.getPuff()
    
    
    
    
    
    
    
    
    
    
    
    












  