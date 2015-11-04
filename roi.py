# -*- coding: utf-8 -*-
"""
Created on Fri Jul 18 18:10:04 2014

@author: Kyle Ellefsen
"""
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import global_vars as g
import pyqtgraph as pg
from skimage.draw import polygon, line
import numpy as np
from trace import roiPlot
import os
import time


class ROI(QWidget):
    " This is an ROI.  I need to document it better."
    translated=Signal()
    translate_done=Signal()
    deleteSignal=Signal()
    plotSignal=Signal()
    kind='freehand'
    def __init__(self,window,x,y):
        QWidget.__init__(self)
        self.window=window
        self.window.currentROI=self
        self.view=self.window.imageview.view
        self.path=QPainterPath(QPointF(x,y))
        self.pathitem=QGraphicsPathItem(self.view)
        self.color=Qt.yellow
        self.pathitem.setPen(QPen(self.color))
        self.pathitem.setPath(self.path)
        self.view.addItem(self.pathitem)
        self.mouseIsOver=False
        self.createActions()
        self.linkedROIs=[]
        self.beingDragged=False
        self.window.deleteButtonSignal.connect(self.deleteCurrentROI)
        self.window.closeSignal.connect(self.delete)
        self.colorDialog=QColorDialog()
        self.colorDialog.colorSelected.connect(self.colorSelected)
    def extend(self,x,y):
        self.path.lineTo(QPointF(x,y))
        self.pathitem.setPath(self.path)
    def deleteCurrentROI(self):
        if self.window.currentROI is self:
            self.delete()
    def delete(self):
        for roi in self.linkedROIs:
            roi.linkedROIs.remove(self)
        if self in self.window.rois:
            self.window.rois.remove(self)
        self.window.currentROI=None
        self.view.removeItem(self.pathitem)
        if g.m.currentTrace is not None and g.m.currentTrace.hasROI(self):
            a=set([r['roi'] for r in g.m.currentTrace.rois])
            b=set(self.window.rois)
            if len(a.intersection(b))==0:
                g.m.currentTrace.indexChanged.disconnect(self.window.setIndex)
            g.m.currentTrace.removeROI(self)
    def getPoints(self):
        points=[]
        for i in np.arange(self.path.elementCount()):
            e=self.path.elementAt(i)
            x=int(np.round(e.x)); y=int(np.round(e.y))
            if len(points)==0 or points[-1]!=(x,y):
                points.append((x,y))
        self.pts=points
        self.minn=np.min(np.array( [np.array([p[0],p[1]]) for p in self.pts]),0)
        return self.pts
    def getArea(self):
        self.getMask()
        return len(self.mask)
        #cnt=np.array([np.array([np.array([p[1],p[0]])]) for p in self.pts ])
        #area = cv2.contourArea(cnt)
        #return area
    def drawFinished(self):
        self.path.closeSubpath()
        self.draw_from_points(self.getPoints()) #this rounds all the numbers down
        if self.getArea()<1:
            self.delete()
            self.window.currentROI=None
        else:
            self.window.rois.append(self)
            self.getMask()

    def mouseOver(self,x,y):
        if self.mouseIsOver is False and self.contains(x,y):
            self.mouseIsOver=True
            self.pathitem.setPen(QPen(Qt.red))
        elif self.mouseIsOver and self.contains(x,y) is False:
            self.mouseIsOver=False
            self.pathitem.setPen(QPen(self.color))

    def contextMenuEvent(self, event):
        self.menu = QMenu(self)
        if g.m.currentTrace is not None and g.m.currentTrace.hasROI(self):
            self.menu.addAction(self.unplotAct)
        else:
            self.menu.addAction(self.plotAct)
        self.menu.addAction(self.colorAct)
        self.menu.addAction(self.copyAct)
        self.menu.addAction(self.deleteAct)
        self.menu.addAction(self.saveAct)
        self.menu.exec_(event.screenPos().toQPoint())

    def plot(self):
        roiPlot(self)
        g.m.currentTrace.indexChanged.connect(self.window.setIndex)
        self.plotSignal.emit()

    def unplot(self):
        g.m.currentTrace.indexChanged.disconnect(self.window.setIndex)
        g.m.currentTrace.removeROI(self)

    def copy(self):
        g.m.clipboard=self

    def save_gui(self):
        filename=g.m.settings['filename']
        directory=os.path.dirname(filename)
        if filename is not None:
            filename= QFileDialog.getSaveFileName(g.m, 'Save ROIs', directory, '*.txt')
        else:
            filename= QFileDialog.getSaveFileName(g.m, 'Save ROIs', '*.txt')
        filename=str(filename)
        if filename=='':
            return False
        else:
            self.save(filename)
    def save(self,filename):
        text=''
        for roi in g.m.currentWindow.rois:
            pts=roi.getPoints()
            text+=type(roi).kind+'\n'
            for pt in pts:
                text+="{0:<4} {1:<4}\n".format(pt[0],pt[1])
            text+='\n'
        f=open(filename,'w')
        f.write(text)
        f.close()
    def changeColor(self):
        self.colorDialog.open()
        
    def colorSelected(self, color):
        if color.isValid():
            self.color=QColor(color.name())
            self.pathitem.setPen(QPen(self.color))
            self.translate_done.emit()
            
            
            
    def createActions(self):
        self.plotAct = QAction("&Plot", self, triggered=self.plot)
        self.colorAct = QAction("&Change Color",self,triggered=self.changeColor)
        self.unplotAct = QAction("&un-Plot", self, triggered=self.unplot)
        self.copyAct = QAction("&Copy", self, triggered=self.copy)
        self.deleteAct = QAction("&Delete", self, triggered=self.delete)
        self.saveAct = QAction("&Save",self,triggered=self.save_gui)
                
    def contains(self,x,y):
        return self.path.contains(QPointF(x,y))
    def translate(self,difference,startpt):
        self.path.translate(difference)
        self.pathitem.setPath(self.path)
        for roi in self.linkedROIs:
            roi.draw_from_points(self.getPoints())
            roi.translated.emit()
        self.translated.emit()
    def finish_translate(self):
        for roi in self.linkedROIs:
            roi.draw_from_points(self.getPoints())
            roi.translate_done.emit()
            roi.beingDragged=False
        self.draw_from_points(self.getPoints())
        self.getMask()
        self.translate_done.emit()
        self.beingDragged=False
    def draw_from_points(self,pts):
        self.pts=pts
        self.path=QPainterPath(QPointF(pts[0][0],pts[0][1]))
        for i in np.arange(len(pts)-1)+1:        
            self.path.lineTo(QPointF(pts[i][0],pts[i][1]))
        self.pathitem.setPath(self.path)
        
    def getMask(self):
        pts=self.pts
        tif=self.window.image
        x=np.array([p[0] for p in pts])
        y=np.array([p[1] for p in pts])
        nDims=len(tif.shape)
        if nDims==4: #if this is an RGB image stack
            tif=np.mean(tif,3)
            mask=np.zeros(tif[0,:,:].shape,np.bool)
        elif nDims==3:
            mask=np.zeros(tif[0,:,:].shape,np.bool)
        if nDims==2: #if this is a static image
            mask=np.zeros(tif.shape,np.bool)
            
        xx,yy=polygon(x,y,shape=mask.shape)
        mask[xx,yy]=True
        pts_plus=np.array(np.where(mask)).T
        for pt in pts_plus:
            if not self.path.contains(QPointF(pt[0],pt[1])):
                mask[pt[0],pt[1]]=0
        self.minn=np.min(np.array( [np.array([p[0],p[1]]) for p in self.pts]),0)
        self.mask=np.array(np.where(mask)).T-self.minn
        
    def getTrace(self,bounds=None,pts=None):
        ''' bounds are two points in time.  If bounds is not None, we only calculate values between the bounds '''
        tif=self.window.image
        if len(tif.shape)==4: #if this is an RGB image stack
            tif=np.mean(tif,3)
        mx,my=tif[0,:,:].shape
        pts=self.mask+self.minn
        pts=pts[(pts[:,0]>=0)*(pts[:,0]<mx)*(pts[:,1]>=0)*(pts[:,1]<my)]
        xx=pts[:,0]; yy=pts[:,1]
        if bounds is None:
            bounds=[0,len(tif)]
        else:
            bounds=list(bounds)
            if bounds[0]<0: bounds[0]=0
            if bounds[1]>len(tif): bounds[1]=len(tif)
            if bounds[0]>len(tif) or bounds[1]<0:
                return np.array([])
        mn=np.zeros(bounds[1]-bounds[0])
        for t in np.arange(bounds[0],bounds[1]):
            mn[t-bounds[0]]=np.mean(tif[t,xx,yy])       
        return mn
        
    def link(self,roi):
        '''This function links this roi to another, so a translation of one will cause a translation of the other'''
        self.linkedROIs.append(roi)
        roi.linkedROIs.append(self)

class ROI_line(ROI):
    kind='line'
    def __init__(self,window,x,y):
        ROI.__init__(self, window,x,y)
        self.kymographAct = QAction("&Kymograph", self, triggered=self.update_kymograph)
        self.kymograph=None
        self.movingPoint=False #either False, 0 or 1
        self.beingDragged=False #either True or False depending on if a translation has been started or not
    def contextMenuEvent(self, event):
        self.menu = QMenu(self)
        if g.m.currentTrace is not None and g.m.currentTrace.hasROI(self):
            self.menu.addAction(self.unplotAct)
        else:
            self.menu.addAction(self.plotAct)
        self.menu.addAction(self.colorAct)
        self.menu.addAction(self.copyAct)
        self.menu.addAction(self.kymographAct)
        self.menu.addAction(self.deleteAct)
        self.menu.addAction(self.saveAct)
        self.menu.exec_(event.screenPos().toQPoint())
    def delete(self):
        ROI.delete(self)
        if self.kymograph is not None:
            self.kymograph.close()
    def update_kymograph(self):
        self.pts=self.getPoints()
        tif=self.window.image
        mt=tif.shape[0]
        x=np.array([p[0] for p in self.pts])
        y=np.array([p[1] for p in self.pts])
        xx,yy=line(x[0],y[0],x[1],y[1])
        mn=np.zeros((mt,len(xx)))
        for t in np.arange(mt):
            mn[t]=tif[t,xx,yy]
        mn=mn.T
        if self.kymograph is None:
            self.createKymograph(mn)
        else:
            self.kymograph.imageview.setImage(mn,autoLevels=False,autoRange=False)
            #self.kymograph.imageview.view.setAspectLocked(lock=True,ratio=mn.shape[1]/mn.shape[0])
    def createKymograph(self,mn):
        from window import Window
        oldwindow=g.m.currentWindow
        name=oldwindow.name+' - Kymograph'
        newWindow=Window(mn,name,metadata=self.window.metadata)
        self.kymograph=newWindow
        self.kymographproxy = pg.SignalProxy(self.translated, rateLimit=3, slot=self.update_kymograph) #This will only update 3 Hz
        self.kymograph.closeSignal.connect(self.deleteKymograph)
    def deleteKymograph(self):
        self.kymographproxy.disconnect()
        self.kymograph.closeSignal.disconnect(self.deleteKymograph)
        self.kymograph=None
    def contains(self,x,y):
        return self.path.intersects(QRectF(x-.5,y-.5,1,1)) #QRectF(x, y, width, height)
    def extend(self,x,y):
        e=self.path.elementAt(0)
        x0=int(np.round(e.x)); y0=int(np.round(e.y))
        self.path=QPainterPath(QPointF(x0,y0))
        self.path.lineTo(QPointF(x,y))
        self.pathitem.setPath(self.path)
    def drawFinished(self):
        self.draw_from_points(self.getPoints()) #this rounds all the numbers down
        if self.path.length()<2:
            self.delete()
            self.window.currentROI=None
        else:
            self.window.rois.append(self)
    def finish_translate(self):
        ROI.finish_translate(self)
        for roi in self.linkedROIs:
            roi.movingPoint=False
        self.movingPoint=False
    def translate(self,difference,startpt):
        ''' For an ROI_line object, this function must translate either one point, the other point, or the entire line, depending on where on the line we start.'''
        pts=self.getPoints()        
        if self.beingDragged==False:
            self.beingDragged=True
            d0=np.sqrt(difference.x()**2+difference.y()**2) #this is the difference we have dragged since the last move
            d1=np.sqrt((self.window.x-pts[0][0])**2+(self.window.y-pts[0][1])**2)
            d2=np.sqrt((self.window.x-pts[1][0])**2+(self.window.y-pts[1][1])**2)
            if d1<d0+self.path.length()/10:  # if distance_from(mousepoint,end1)<self.path.length()/10
                self.movingPoint=0
            elif d2<d0+self.path.length()/10:
                self.movingPoint=1
        else:
            if self.movingPoint is not False:
                pts[self.movingPoint]=(self.window.x,self.window.y) # translate end1 
                path=QPainterPath(QPointF(pts[0][0],pts[0][1]))
                path.lineTo(QPointF(pts[1][0],pts[1][1]))
                if path.length()<np.sqrt(2):
                    return
                else:
                    self.path=path
            else:
                self.path.translate(difference)
        
        self.pathitem.setPath(self.path)
        for roi in self.linkedROIs:
            roi.draw_from_points(self.getPoints())
            roi.translated.emit()
        self.translated.emit()

class ROI_rectangle(ROI):
    kind='rectangle'
    def __init__(self,window,x,y):
        ROI.__init__(self, window,x,y)
        self.movingPoint=False #either False, 0,1,2,3
        self.beingDragged=False #either True or False depending on if a translation has been started or not
        self.cropAct = QAction("&Crop", self, triggered=self.crop)
    def extend(self,x,y):
        e=self.path.elementAt(0)
        x0=int(np.round(e.x)); y0=int(np.round(e.y))
        self.path=QPainterPath(QPointF(x0,y0))
        self.path.lineTo(QPointF(x0,y))
        self.path.lineTo(QPointF(x,y))
        self.path.lineTo(QPointF(x,y0))
        self.path.lineTo(QPointF(x0,y0))
        self.pathitem.setPath(self.path)
    def contextMenuEvent(self, event):
        self.menu = QMenu(self)
        if g.m.currentTrace is not None and g.m.currentTrace.hasROI(self):
            self.menu.addAction(self.unplotAct)
        else:
            self.menu.addAction(self.plotAct)
        self.menu.addAction(self.colorAct)
        self.menu.addAction(self.copyAct)
        self.menu.addAction(self.deleteAct)
        self.menu.addAction(self.saveAct)
        self.menu.addAction(self.cropAct)
        self.menu.exec_(event.screenPos().toQPoint())
    def crop(self):
        from window import Window
        self.pts=self.getPoints()
        x1=np.min([self.pts[0][0],self.pts[2][0]])
        x2=np.max([self.pts[0][0],self.pts[2][0]])
        y1=np.min([self.pts[0][1],self.pts[2][1]])
        y2=np.max([self.pts[0][1],self.pts[2][1]])
        tif=self.window.image
        if len(tif.shape)==3:
            mt,mx,my=tif.shape
            if x1<0: x1=0
            if y1<0: y1=0
            if x2>=mx: x2=mx-1
            if y2>=my: y2=my-1
            newtif=tif[:,x1:x2+1,y1:y2+1]
        elif len(tif.shape)==2:
            if x1<0: x1=0
            if y1<0: y1=0
            if x2>=mx: x2=mx-1
            if y2>=my: y2=my-1
            mx,my=tif.shape
            newtif=tif[x1:x2+1,y1:y2+1]
        return Window(newtif,self.window.name+' Cropped',metadata=self.window.metadata)
        
    def translate(self,difference,startpt):
        ''' For an ROI_line object, this function must translate either one point, the other point, or the entire line, depending on where on the line we start.'''
        pts=self.getPoints()        
        if self.beingDragged==False:
            self.beingDragged=True
            distances=np.array([np.sqrt((startpt.x()-pts[i][0])**2+(startpt.y()-pts[i][1])**2) for i in np.arange(4)]) #distances away from each point in the rectangle
            closestpt=np.argmin(distances)
            if distances[closestpt]<self.path.length()/16.0: # this defines how close we must be to a corner
                self.movingPoint=closestpt
        else: 
            if self.movingPoint is not False: #resizing the rectangle
                staticPoint=np.mod(self.movingPoint+2,4)
                self.movingPoint=2
                x0,y0=pts[staticPoint]
                x,y=(self.window.x,self.window.y)
                path=QPainterPath(QPointF(x0,y0))
                path.lineTo(QPointF(x0,y))
                path.lineTo(QPointF(x,y))
                path.lineTo(QPointF(x,y0))
                path.lineTo(QPointF(x0,y0))
                if np.abs(x-x0)<1 or np.abs(y-y0)<1:
                    return
                else:
                    self.path=path
                    self.getMask()
            else:
                self.path.translate(difference)
        
        self.pathitem.setPath(self.path)
        for roi in self.linkedROIs:
            roi.draw_from_points(self.getPoints())
            roi.translated.emit()
        self.translated.emit()
    def finish_translate(self):
        ROI.finish_translate(self)
        for roi in self.linkedROIs:
            roi.movingPoint=False
        self.movingPoint=False
        
def load_roi_gui():
    filename=g.m.settings['filename']
    if filename is not None and os.path.isfile(filename):
        filename= QFileDialog.getOpenFileName(g.m, 'Open File', filename, '*.txt')
    else:
        filename= QFileDialog.getOpenFileName(g.m, 'Open File', '','*.txt')
    filename=str(filename)
    if filename=='':
        return False
    else:
        load_roi(filename)
    
def makeROI(kind,pts,window=None):
    if window is None:
        window=g.m.currentWindow
    if kind=='freehand':
        roi=ROI(window,0,0)
    elif kind=='rectangle':
        roi=ROI_rectangle(window,0,0)
    elif kind=='line':
        roi=ROI_line(window,0,0)
    else:
        print("ERROR: THIS TYPE OF ROI COULD NOT BE FOUND: {}".format(kind))
        return None
    roi.draw_from_points(pts)
    roi.drawFinished()
    return roi
def load_roi(filename):
    f = open(filename, 'r')
    text=f.read()
    f.close()
    kind=None
    pts=None
    for line in text.split('\n'):
        if kind is None:
            kind=line
            pts=[]
        elif line=='':
            makeROI(kind,pts)
            kind=None
            pts=None
        else:
            pts.append(tuple(int(i) for i in line.split()))      
    
    
    
    
    
    
    
    
    