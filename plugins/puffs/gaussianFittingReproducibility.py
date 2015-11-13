# -*- coding: utf-8 -*-
"""
Created on Tue Aug 12 10:38:28 2014

@author: Kyle Ellefsen
"""
from scipy.fftpack import *
from .gaussianFitting import fitGaussian
import pyqtgraph as pg
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import numpy as np
import global_vars as g


        
class ReproducibilityPlot(QWidget):
    def __init__(self,image=np.zeros((1,1)), parent=None):
        QWidget.__init__(self,parent)
        from .puffAnalyzer import PuffAnalyzer
        self.puffs=[p for p in g.m.windows if type(p) is PuffAnalyzer][0].puffs
        self.view=pg.GraphicsLayoutWidget()
        self.layout=QVBoxLayout()
        self.setLayout(self.layout)
        self.layout.addWidget(self.view)
        self.show()
        self.plot=self.view.addPlot()
        self.plot.vb.setAspectLocked(True,ratio=1)
        self.plot.vb.invertY(True)
        self.plot.addItem(pg.ImageItem(image))
        self.points=dict()
        self.circles=dict()
        
        self.addPuffButton=QPushButton('Add Current Puff')
        self.addPuffButton.pressed.connect(self.addPuff)
        self.removePuffButton=QPushButton('Remove Current Puff')
        self.removePuffButton.pressed.connect(self.removePuff)
        self.showPoints=QCheckBox("Show simulated origins")
        self.showPoints.setChecked(True)
        self.showPoints.stateChanged.connect(self.togglePoints)
        self.showCircles=QCheckBox("Show circles which contain origins with 95% certainty")
        self.showCircles.setChecked(True)
        self.showCircles.stateChanged.connect(self.toggleCircles)
        self.l_right=QGridLayout()
        self.l_right.addWidget(self.addPuffButton,0,0)
        self.l_right.addWidget(self.removePuffButton,0,1)
        self.l_right.addWidget(self.showPoints,0,2)
        self.l_right.addWidget(self.showCircles,0,3)
        self.layout.addLayout(self.l_right)
    def addPuff(self,color=(255,0,0)):
        index=self.puffs.index
        if index in self.points.keys(): #Don't add if it's already been added
            return
        puff=self.puffs[index]
        if hasattr(puff, 'origin_positions'):
            positions=puff.origin_positions
        else:
            positions=self.runSimulation(puff)
            puff.origin_positions=positions
        # MAKE SCATTER PLOT OF POINTS
        red,green,blue=color
        brush=pg.mkBrush(red, green,blue,50)
        self.points[index] = pg.ScatterPlotItem(size=.01 , pen=pg.mkPen(None), brush=brush)
        self.points[index].setPxMode(False) # size in terms of original image pixels, not screen pixels.
        for pos in positions:
            spots = [{'pos': po, 'data': 1} for po in pos]
            self.points[index].addPoints(spots)
        if self.showPoints.isChecked():
            self.plot.addItem(self.points[index])
        # MAKE SCATTER PLOT OF CIRCLES
        brush=pg.mkBrush(red, green,blue,20)
        self.circles[index]=pg.ScatterPlotItem(size=5, pen=pg.mkPen(None), brush=brush)
        self.circles[index].setPxMode(False) # size in terms of original image pixels, not screen pixels.
        for pos in positions:
            sigma=np.mean([np.std(pos[:,0]),np.std(pos[:,1])]) #take the mean of the standard deviations of the x and y values
            circ=np.column_stack((np.mean(pos[:,0]),np.mean(pos[:,1])))
            spot = [{'pos': circ[0], 'data': 1, 'brush':brush, 'size':4*sigma }]
            self.circles[index].addPoints(spot)
        if self.showCircles.isChecked():
            self.plot.addItem(self.circles[index])
    def togglePoints(self,state):
        if state==0: #if we are removing the points
            for p in self.points.values():
                self.plot.removeItem(p)
        elif state==2: #if we are adding back the points
            for p in self.points.values():
                self.plot.addItem(p)
    def toggleCircles(self,state):
        if state==0: #if we are removing the circles
            for p in self.circles.values():
                self.plot.removeItem(p)
        elif state==2: #if we are adding back the circles
            for p in self.circles.values():
                self.plot.addItem(p)
        
    def removePuff(self):
        index=self.puffs.index
        if index not in self.points.keys(): #if the current puff hasn't been added, don't do anything
            return 
        self.plot.removeItem(self.circles[index])
        self.plot.removeItem(self.points[index])
        del self.circles[index]
        del self.points[index]
        
    def runSimulation(self,puff,nTimes=100):
        fit=np.copy(puff.gaussianFit)
        offsets=puff.gaussianParams[:,5]
        volume=np.copy(puff.getVolume())
        mt=len(offsets)
        for i in np.arange(mt):
            volume[i]=volume[i]-offsets[i]
            fit[i]=fit[i]-offsets[i]
        b=puff.bounds        
        p=puff.position
        xorigin=p[1]-b[1][0]
        yorigin=p[2]-b[2][0]
        sigma=3
        amplitude=1
        offset=1
        p0=(xorigin,yorigin,sigma,amplitude,offset) #(xorigin,yorigin,sigmax,sigmay,angle,amplitude,offset)
        bounds = [(0.0, 2*puff.paddingXY), (0, 2*puff.paddingXY),(2,5),(0,5),(0,2)]#[(0.0, 2*self.paddingXY), (0, 2*self.paddingXY),(0,10),(0,10),(0,90),(0,5),(0,2)]

        t_i=puff.kinetics['start_frame']-puff.bounds[0][0]
        t_f=puff.kinetics['end_frame']-puff.bounds[0][0]
        positions=[]
        for frameN in np.arange(t_i,t_f+1):
            remander=volume[frameN]-fit[frameN]
            xs=[]
            ys=[]
            for i in np.arange(nTimes):
                noise=np.std(remander)*np.random.randn(*remander.shape)
                I=noise+fit[frameN]
                p, I_fit= fitGaussian(I,p0,bounds)
                p[0]=p[0]+puff.bounds[1][0] #Put back in regular coordinate system.  Add back x
                p[1]=p[1]+puff.bounds[2][0] #add back y 
                x,y,sigma,amplitude,offset=p
                xs.append(x)
                ys.append(y)
                #print("X={}, Y={}".format(xorigin,yorigin))
            pos=np.column_stack((xs,ys))
            positions.append(pos)
        return positions
        




#mt,mx,my=volume.shape
#M=np.zeros((mx,my))
#for x in np.arange(mx):
#    for y in np.arange(my):
#        M[x,y]=np.correlate(volume[:,x,y],remander)[0]





if __name__=='__main__':
    mat=g.m.currentWindow.image[200:300].mean(0)

    puffs=puffAnalyzer.puffs
    self=ReproducibilityPlot(mat)
    self.addPuff(puffs)
    self.removePuff(puffs)




