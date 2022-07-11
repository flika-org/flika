# -*- coding: utf-8 -*-
from ..logger import logger
logger.debug("Started 'reading process/measure.py'")
import os
import numpy as np
import pyqtgraph as pg
from qtpy import QtWidgets, QtCore, QtGui
from .. import global_vars as g
from ..utils.BaseProcess import BaseProcess
from ..utils.misc import save_file_gui

from ..roi import ROI_Base
__all__ = ['measure']


np.set_printoptions(suppress=True)
np.set_printoptions(precision=3)
            
class Measure(BaseProcess):
    """Measure(BaseProcess)

    Click in the graph to select a point.
    Shift-Click in the graph to select the nearest data point
    
    """
    def __init__(self):
        self.ON=False
        super().__init__()
    def gui(self):
        self.gui_reset()
        self.currentPoint = 0
        active_point = QtWidgets.QLineEdit() #active_point.setEnabled(False)
        second_point = QtWidgets.QLineEdit() #second_point.setEnabled(False)
        difference = QtWidgets.QLineEdit() #difference.setEnabled(False)
        slope = QtWidgets.QLineEdit() #slope.setEnabled(False)
        log = QtWidgets.QPushButton('Log Data')
        log.pressed.connect(self.log)
        newcol=QtWidgets.QPushButton('New Column')
        newcol.pressed.connect(self.newcol)
        self.table = pg.TableWidget()
        self.items.append({'name':'active_point','string':'Active Point: ','object':active_point})
        self.items.append({'name':'second_point','string':'Second Point: ','object':second_point})
        self.items.append({'name':'difference','string':'Difference: ','object':difference})
        self.items.append({'name':'slope','string':'Slope: ','object':slope})
        self.items.append({'name':'log','string':'','object':log})
        self.items.append({'name':'newcol','string':'','object':newcol})
        super().gui()
        self.fig = None
        self.ui.accepted.disconnect()
        self.ui.closeSignal.connect(self.close)
        self.ui.rejected.connect(self.close)
        self.ui.accepted.connect(self.close)
        self.ui.accepted.connect(self.export_gui)
        self.data = [[]]
        self.ON = True
    def log(self):
        point=[self.firstPoint[0],self.firstPoint[1],self.secondPoint[0],self.secondPoint[1],self.difference[0],self.difference[1],self.slope]
        self.data[len(self.data)-1].append(point)
    def newcol(self):
        self.data.append([])

    def clear(self):
        self.currentPoint = 0
        try:
            self.viewbox.removeItem(self.pathitem)
        except:
            pass

    def pointclicked(self,evt, window=None):
        if evt.button() != 1:
            return
        if self.ON is False:
            return
        pos = evt.pos()
        if isinstance(evt.currentItem, (ROI_Base, pg.ROI)):
            pos = evt.currentItem.mapToScene(pos)

        if window != None:
            if window != self.fig:
                self.clear()
                self.fig = window
                self.viewbox = self.fig.imageview.view
                self.pathitem=QtWidgets.QGraphicsPathItem(self.viewbox)
                self.pathitem.setPen(QtGui.QPen(QtCore.Qt.red, 0))
                self.viewbox.addItem(self.pathitem,ignoreBounds=True)
            mousePoint = self.fig.imageview.getImageItem().mapFromScene(pos)
            pos = np.array([mousePoint.y(),mousePoint.x()])
        else:
            if self.fig is not g.currentTrace: #if we created a new tracefig
                self.clear()
                self.fig=g.currentTrace
                self.viewbox=self.fig.vb
                if not g.currentTrace.p1.plotItem.sceneBoundingRect().contains(pos):
                    return
                self.pathitem=QtWidgets.QGraphicsPathItem(self.viewbox)
                self.pathitem.setPen(QtGui.QPen(QtCore.Qt.red, 0))
                self.viewbox.addItem(self.pathitem,ignoreBounds=True)
            mousePoint = self.viewbox.mapSceneToView(pos)
            pos = np.array([mousePoint.x(),mousePoint.y()])
        
        self.update(pos)

    def update(self, point):
        
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        if modifiers == QtCore.Qt.ShiftModifier:
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
        if type(self.fig) != type(g.currentTrace):
            points = [p[::-1] for p in points]
        path=QtGui.QPainterPath(QtCore.QPointF(*points[0]))
        for i in np.arange(1,len(points)):
            path.lineTo(QtCore.QPointF(*points[i]))
        self.pathitem.setPath(path)
        
    def close(self):
        if hasattr(self, "pathitem") and self.pathitem.parentWidget() != None:
            self.pathitem.parentWidget().removeItem(self.pathitem) 
        self.ON=False
    def getNearestPoint(self,point):
        if hasattr(self.fig, 'imageview'):
            return point
        roi=g.currentTrace.rois[0]
        d=roi['p2trace'].getData()
        index=np.abs(d[0]-point[0]).argmin()
        x=d[0][index]
        ys=[]
        for roi in g.currentTrace.rois:
            d=roi['p2trace'].getData()
            ys.append(d[1][index])
        roi_idx=np.argmin(abs(ys - point[1]))
        y=ys[roi_idx]
        return np.array([x,y])
    
    def export_gui(self):
        filename = g.settings['filename']
        directory = os.path.dirname(filename)
        if filename is not None:
            filename = save_file_gui('Save Measurements', directory, '*.txt')
        else:
            filename = save_file_gui('Save Measurements', None, '*.txt')
        filename = str(filename)
        if filename == '':
            return False
        else:
            self.export(filename)
            
    def export(self,filename):
        ''' This function saves out all the traces in the tracefig to a file specified by the argument 'filename'.
        The output file is a tab seperated ascii file where each column is a trace.  
        Traces are saved in the order they were added to the plot.

        Parameters:
            filename (str): name of file to save
        
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
    
measure = Measure()
logger.debug("Completed 'reading process/measure.py'")