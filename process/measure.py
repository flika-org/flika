# -*- coding: utf-8 -*-
"""
Created on Thu Aug 28 12:54:12 2014

@author: Kyle Ellefsen
"""

from __future__ import (absolute_import, division,print_function, unicode_literals)
from future.builtins import (bytes, dict, int, list, object, range, str, ascii, chr, hex, input, next, oct, open, pow, round, super, filter, map, zip)

import os

import numpy as np
import global_vars as g
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from process.BaseProcess import BaseProcess
import pyqtgraph as pg

np.set_printoptions(suppress=True)
np.set_printoptions(precision=3)
            
class Measure(BaseProcess):
    """
    Click in the graph to select a point.
    Shift-Click in the graph to select the nearest data point
    
    """
    def __init__(self):
        self.ON=False
        super().__init__()
    def gui(self):
        self.gui_reset()
        self.currentPoint=0
        active_point=QLineEdit(); #active_point.setEnabled(False)
        second_point=QLineEdit(); #second_point.setEnabled(False)
        difference=QLineEdit(); #difference.setEnabled(False)
        slope=QLineEdit(); #slope.setEnabled(False)
        log=QPushButton('Log Data')
        log.pressed.connect(self.log)
        newcol=QPushButton('New Column')
        newcol.pressed.connect(self.newcol)
        self.table = pg.TableWidget()
        self.items.append({'name':'active_point','string':'Active Point: ','object':active_point})
        self.items.append({'name':'second_point','string':'Second Point: ','object':second_point})
        self.items.append({'name':'difference','string':'Difference: ','object':difference})
        self.items.append({'name':'slope','string':'Slope: ','object':slope})
        self.items.append({'name':'log','string':'','object':log})
        self.items.append({'name':'newcol','string':'','object':newcol})
        
        super().gui()
        
        self.tracefig=None
        
        self.ui.accepted.disconnect()
        self.ui.closeSignal.connect(self.close)
        self.ui.rejected.connect(self.close)
        self.ui.accepted.connect(self.close)
        self.ui.accepted.connect(self.export_gui)
        self.data=[[]]
        self.ON=True
    def log(self):
        point=[self.firstPoint[0],self.firstPoint[1],self.secondPoint[0],self.secondPoint[1],self.difference[0],self.difference[1],self.slope]
        self.data[len(self.data)-1].append(point)
    def newcol(self):
        self.data.append([])
    def pointclicked(self,evt):
        if self.ON is False:
            return
        pos=evt.pos()
        if self.tracefig is not g.m.currentTrace: #if we created a new tracefig
            self.tracefig=g.m.currentTrace
            self.viewbox=self.tracefig.p1.getPlotItem().vb
            self.pathitem=QGraphicsPathItem(self.viewbox)
            self.pathitem.setPen(QPen(Qt.red))
            self.viewbox.addItem(self.pathitem,ignoreBounds=True)
        if not g.m.currentTrace.p1.plotItem.sceneBoundingRect().contains(pos):
            return
        mousePoint = g.m.currentTrace.vb.mapSceneToView(pos)
        point = np.array([mousePoint.x(),mousePoint.y()])

        modifiers = QApplication.keyboardModifiers()
        if modifiers == Qt.ShiftModifier:
            point=self.getNearestPoint(point)
        if self.currentPoint==0:
            self.currentPoint=1
            self.firstPoint=point
            self.ui.items[0]['object'].setText(str(point))
            self.ui.items[1]['object'].setText('')
            self.ui.items[2]['object'].setText('')
            self.ui.items[3]['object'].setText('')
            self.secondPoint=None
            self.draw([self.firstPoint])
        else:
            self.currentPoint=0
            self.secondPoint=point
            self.ui.items[1]['object'].setText(str(point))
            self.difference=self.secondPoint-self.firstPoint
            self.ui.items[2]['object'].setText(str(self.difference))
            if self.difference[0]==0:
                self.slope=np.inf
            else:
                self.slope=self.difference[1]/self.difference[0]
            self.ui.items[3]['object'].setText(str(self.slope))
            self.draw([self.firstPoint,self.secondPoint])
                    
    def draw(self,points):
        path=QPainterPath(QPointF(*points[0]))
        for i in np.arange(1,len(points)):
            path.lineTo(QPointF(*points[i]))
        self.pathitem.setPath(path)
        
    def close(self):
        self.viewbox.removeItem(self.pathitem)
        self.ON=False
    def getNearestPoint(self,point):
        
        roi=g.m.currentTrace.rois[0]
        d=roi['p2trace'].getData()
        index=np.abs(d[0]-point[0]).argmin()
        x=d[0][index]
        ys=[]
        for roi in g.m.currentTrace.rois:
            d=roi['p2trace'].getData()
            ys.append(d[1][index])
        roi_idx=np.argmin(abs(ys-point[1]))
        y=ys[roi_idx]
        return np.array([x,y])
    
    def export_gui(self):
        filename=g.m.settings['filename']
        directory=os.path.dirname(filename)
        if filename is not None:
            filename= QFileDialog.getSaveFileName(g.m, 'Save Measurements', directory, '*.txt')
        else:
            filename= QFileDialog.getSaveFileName(g.m, 'Save Measurements', '*.txt')
        filename=str(filename)
        if filename=='':
            return False
        else:
            self.export(filename)
            
    def export(self,filename):
        ''' This function saves out all the traces in the tracefig to a file specified by the argument 'filename'.
        The output file is a tab seperated ascii file where each column is a trace.  
        Traces are saved in the order they were added to the plot.
        
        '''
        g.m.statusBar().showMessage('Saving {}'.format(os.path.basename(filename)))
        d=self.data
        output=''
        maxj=np.max([len(j) for j in d])
        header=['x1' ,'y1','x2','y2','x difference','y difference' , 'slope']
        for i in np.arange(len(d)):
            for k in np.arange(7):
                output+=header[k]+'\t'
            output+='\t'
        output+='\n'
        for j in np.arange(maxj): #this loops through each row of data
            for i in np.arange(len(d)): #this loops through each mega-column, each of which is composed of 7 mini-columns.
                for k in np.arange(7): #this loops through each of the seven values
                    try:
                        output+=str(d[i][j][k])+'\t'
                    except IndexError:
                        output+='\t'
                output+='\t'
            output+='\n'
        f = open(filename, 'w')
        f.write(output)
        f.close()
        g.m.statusBar().showMessage('Successfully saved {}'.format(os.path.basename(filename)))
    
measure=Measure()


    
    
#                if index > 0:
#                    self.label.setText("<span style='font-size: 12pt'>frame={0}</span>".format(index))
#                    self.indexChanged.emit(index)
