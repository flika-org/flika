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

class ROI_Drawing(pg.GraphicsObject):
    def __init__(self, window, x, y, type):
        pg.GraphicsObject.__init__(self)
        window.imageview.addItem(self)
        self.pts = [pg.Point(int(x), int(y))]
        for roi in window.rois:
            if isinstance(roi, ROI_Rect_Line):
                a = roi.getNearestHandle(self.pts[0])
                if a:
                    roi.extendHandle = a[1]
                    self.extend = roi.extend
                    self.drawFinished = roi.drawFinished
                    #self.__dict__.update(roi.__dict__)
                    self.boundingRect = roi.boundingRect
                    return
        self.type = type
        self.window = window
        self.state = {'pos': pg.Point(x, y), 'size': pg.Point(0, 0)}

    def extend(self, x, y):
        new_pt = pg.Point(int(x), int(y))
        if self.type == 'freehand':
            self.pts.append(new_pt)
        elif self.type in ('line', 'rectangle', 'rect_line'):
            if len(self.pts) == 1:
                self.pts.append(new_pt)
            else:
                self.pts[1] = new_pt

            #self.pts = sorted(self.pts, key=lambda a: a.x()/a.y())

        self.state['pos'] = pg.Point(*np.min(self.pts, 0))
        self.state['size'] = pg.Point(*np.ptp(self.pts, 0))

        self.prepareGeometryChange()
        self.update()

    def paint(self, p, *args):
        p.setPen(QPen(QColor(255,255,255)))
        if self.type == 'freehand':
            p.drawPolyline(*self.pts)
        elif self.type == 'rectangle':
            p.drawRect(self.boundingRect())
        elif self.type in ('rect_line', 'line'):
            p.drawLine(*self.pts)

    def drawFinished(self):
        self.window.imageview.removeItem(self)
        args = {'removable': True, 'translateSnap': True}
        if self.type == 'freehand':
            r = ROI_Polygon(self.window, self.pts, **args)
        elif self.type == 'rectangle':
            r = ROI_Rect(self.window, self.state['pos'], self.state['size'], **args)
        elif self.type == 'line':
            r = ROI_Line(self.window, self.pts, **args)
        elif self.type == 'rect_line':
            r = ROI_Rect_Line(self.window, self.pts, **args)

        self.window.imageview.addItem(r)
        self.window.rois.append(r)
        self.window.currentROI = None

        return r

    def contains(self, *args):
        if len(args) == 2:
            args = [pg.Point(*args)]
        return pg.GraphicsObject.contains(self, *args)

    def boundingRect(self):
        return QRectF(self.state['pos'].x(), self.state['pos'].y(), self.state['size'].x(), self.state['size'].y())

class ROI_Wrapper():
    def __init__(self):
        self.getMenu()
        self.colorDialog=QColorDialog()
        self.colorDialog.colorSelected.connect(self.colorSelected)
        self.window.closeSignal.connect(self.delete)
        self.traceWindow = None
        self.linkedROIs = set()
        #self.proxy = pg.SignalProxy(self.sigRegionChanged, rateLimit=3, slot=self.getMask)
        #self.sigRegionChanged.connect(self.getMask)
        #self.getMask()

    def plot(self):
        self.traceWindow = roiPlot(self)
        self.traceWindow.indexChanged.connect(self.window.setIndex)
        self.plotSignal.emit()

    def changeColor(self):
        self.colorDialog.open()
        
    def colorSelected(self, color):
        if color.isValid():
            self.setPen(QColor(color.name()))
            self.sigRegionChangeFinished.emit(self)

    def save_gui(self):
        filename=g.settings['filename']
        if filename is not None and os.path.isfile(filename):
            filename= QFileDialog.getSaveFileName(g.m, 'Save ROI', filename, "*.txt")
        else:
            filename= QFileDialog.getSaveFileName(g.m, 'Save ROI', '', '*.txt')
        filename=str(filename)
        if filename != '':
            self.save(filename)
        else:
            g.m.statusBar().showMessage('No File Selected')

    def unplot(self):
        self.traceWindow.indexChanged.disconnect(self.window.setIndex)
        self.traceWindow.removeROI(self)
        self.traceWindow = None

    def copy(self):
        g.m.clipboard=self

    def link(self,roi):
        '''This function links this roi to another, so a translation of one will cause a translation of the other'''
        self.linkedROIs.add(roi)
        roi.linkedROIs.add(self)

    def raiseContextMenu(self, ev):
        pos = ev.screenPos()
        self.menu.popup(QPoint(pos.x(), pos.y()))
    
    def getMenu(self):
        self.plotAct = QAction("&Plot", self, triggered=self.togglePlot)
        self.plotAllAct = QAction('&Plot All', self, triggered=lambda : [roi.plot() for roi in self.window.rois])
        self.colorAct = QAction("&Change Color",self,triggered=self.changeColor)
        self.copyAct = QAction("&Copy", self, triggered=self.copy)
        self.remAct = QAction("&Delete", self, triggered=self.delete)
        self.saveAct = QAction("&Save ROIs",self,triggered=self.save_gui)        
        self.menu = QMenu("ROI Menu")
        
        self.menu.addAction(self.plotAct)
        self.menu.addAction(self.plotAllAct)
        self.menu.addAction(self.colorAct)
        self.menu.addAction(self.copyAct)
        self.menu.addAction(self.remAct)
        self.menu.addAction(self.saveAct)
    
    def delete(self):
        if self.traceWindow != None:
            self.unplot()
        for roi in self.linkedROIs:
            if self in roi.linkedROIs:
                roi.linkedROIs.remove(self)
        if self in self.window.rois:
            self.window.rois.remove(self)
        self.window.currentROI=None
        self.window.imageview.removeItem(self)
        self.window.closeSignal.disconnect(self.delete)
        
    def togglePlot(self):
        if self.traceWindow != None:
            self.plotAct.setText("Plot")
            self.unplot()
            self.plotted = False
        else:
            self.plotAct.setText("Unplot")
            self.plot()
            self.plotted = True

class ROI_Line(ROI_Wrapper, pg.LineSegmentROI):
    kind = 'line'
    plotSignal = Signal()
    def __init__(self, window, pos, *args, **kargs):
        self.window = window
        self.pts = pos
        pg.LineSegmentROI.__init__(self, positions=pos, *args, **kargs)
        self.kymographAct = QAction("&Kymograph", self, triggered=self.update_kymograph)
        self.kymograph = None
        ROI_Wrapper.__init__(self)

    def getMenu(self):
        ROI_Wrapper.getMenu(self)
        self.menu.addAction(self.kymographAct)

    def getPoints(self):
        self.pts = [h['item'].pos() + self.pos() for h in self.handles]
        x=np.array([p[0] for p in self.pts], dtype=int)
        y=np.array([p[1] for p in self.pts], dtype=int)
        xx,yy=line(x[0],y[0],x[1],y[1])
        
        #exclude points outside bounds
        w, h = np.shape(self.window.image[0])
        rect = QRect(0, 0 ,w, h)
        ids = np.where([rect.contains(x, y) for x, y in zip(xx, yy)])
        return np.array([pg.Point(p) for p in np.transpose([xx[ids], yy[ids]])], dtype=int)

    def getTrace(self, bounds=None, pts=None):
        pts = self.getPoints()
        if len(pts) == 0:
            vals = np.zeros(len(self.window.image))
        else:
            xx, yy = pts.T
            vals = self.window.image[:, xx, yy]
            vals = np.average(vals, np.arange(np.ndim(vals)-1, 0, -1))
        
        if bounds:
            vals = vals[bounds[0]:bounds[1]]

        return vals

    def update_kymograph(self):
        
        tif=self.window.image
        xx, yy = self.getPoints().T
        mt = len(tif)
        if len(xx) == 0:
            return
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
        #self.kymographproxy = pg.SignalProxy(self.sigRegionChanged, rateLimit=3, slot=self.update_kymograph) #This will only update 3 Hz
        self.sigRegionChanged.connect(self.update_kymograph)
        self.kymograph.closeSignal.connect(self.deleteKymograph)

    def deleteKymograph(self):
        self.kymographproxy.disconnect()
        self.kymograph.closeSignal.disconnect(self.deleteKymograph)
        self.kymograph=None

class ROI_Rect_Line(ROI_Wrapper, pg.MultiRectROI):
    kind = 'rect_line'
    plotSignal = Signal()
    def __init__(self, window, pts, width=.5, pen=QPen(QColor(255, 255, 255)), *args, **kargs):
        self.window = window
        self.width = width
        pg.MultiRectROI.__init__(self, pts, width, pen=pen, *args, **kargs)
        self.kymographAct = QAction("&Kymograph", self, triggered=self.update_kymograph)
        ROI_Wrapper.__init__(self)
        self.extending = False
        self.extendHandle = None
        w, h = self.lines[-1].size()
        self.lines[-1].scale([1.0, width/5.0], center=[0.5,0.5])
        self.currentLine = None

    def hoverEvent(self, l, ev):
        self.currentLine = l
        if ev.enter:
            self.currentPen = QPen(QColor(255, 255, 0))
        elif ev.exit:
            self.currentPen = QPen(QColor(255, 255, 255))

    def removeLink(self):
        self.removeSegment(self.lines.index(self.currentLine))

    def getMenu(self):
        ROI_Wrapper.getMenu(self)
        removeLinkAction = QAction('Remove Link', self, triggered=self.removeLink)
        self.menu.addAction(removeLinkAction)
        self.menu.removeAction(self.copyAct)
        self.menu.addAction(self.kymographAct)

    def setPen(self, pen):
        self.pen = pen
        for l in self.lines:
            l.setPen(pen)

    def getArrayRegion(self, arr, img=None, axes=(0,1), returnMappedCoords=False):
        rgns = []
        coords = []
        for l in self.lines:
            rgn = l.getArrayRegion(arr, img, axes=axes, returnMappedCoords=returnMappedCoords)
            if rgn is None:
                continue
                #return None
            if returnMappedCoords:
                rgn, coord = rgn
                coords.append(np.concatenate(coord.T))
            rgns.append(rgn)
            #print l.state['size']
            
        ## make sure orthogonal axis is the same size
        ## (sometimes fp errors cause differences)
        ms = min([r.shape[axes[1]] for r in rgns])
        sl = [slice(None)] * rgns[0].ndim
        sl[axes[1]] = slice(0,ms)
        rgns = [r[sl] for r in rgns]
        #print [r.shape for r in rgns], axes
        if returnMappedCoords:
            return np.concatenate(rgns, axis=axes[0]), np.concatenate(coords)

        return np.concatenate(rgns, axis=axes[0])

    def addSegment(self, *arg, **args):
        pg.MultiRectROI.addSegment(self, *arg, **args)
        self.lines[-1].raiseContextMenu = self.raiseContextMenu
        self.lines[-1].getMenu = self.getMenu
        l = self.lines[-1]
        self.lines[-1].hoverEvent = lambda ev: self.hoverEvent(l, ev)

    def getTracePoints(self):
        if self.lines[0].handles[1]['item'].pos()[1] <= 1:
            xx = []
            yy = []
            for l in self.lines:
                pts=[self.window.imageview.getImageItem().mapFromScene(l.getSceneHandlePositions(i)[1]) for i in range(2)]
                x=np.array([p.x() for p in pts], dtype=int)
                y=np.array([p.y() for p in pts], dtype=int)
                xs,ys=line(x[0],y[0],x[1],y[1])
                xx.append(xs)
                yy.append(ys)
            xx = np.concatenate(xx)
            yy = np.concatenate(yy)

        else:
            vals, coords = self.getArrayRegion(self.window.image, self.window.imageview.getImageItem(), axes=(1, 2), returnMappedCoords=True)
            # vals includes outside coordinates. Recalculate
            xx, yy = coords.T.astype(int)
        return xx, yy

    def getTrace(self, bounds=None, pts=None):
        xx, yy = self.getTracePoints()

        pts = [pg.Point(p) for p in np.transpose([xx, yy])]
        w, h = np.shape(self.window.image[0])
        rect = QRect(0, 0 ,w, h)
        ids = np.where([rect.contains(p[0], p[1]) for p in pts])
        xx = xx[ids]
        yy = yy[ids]
        vals = self.window.image[:, xx, yy]

        if len(vals) == 0:
            return np.zeros(len(self.window.image))
        vals = np.average(vals, np.arange(np.ndim(vals)-1, 0, -1))
        if bounds:
            vals = vals[bounds[0]:bounds[1]]

        return vals

    def getNearestHandle(self, pos, distance=3):
        for l in self.lines:
            for i in range(2):
                p = self.window.imageview.getImageItem().mapFromScene(l.getSceneHandlePositions(i)[1])
                if (p - pos).manhattanLength() <= distance:
                    return l, l.handles[i]['item']

    def extend(self, x, y):
        if not self.extending:
            self.extending = True
            self.addSegment(pg.Point(int(x), int(y)), connectTo=self.extendHandle)
        else:
            self.lines[-1].handles[-1]['item'].movePoint(self.window.imageview.getImageItem().mapToScene(pg.Point(x, y))) 

    def drawFinished(self):
        self.extending = False
        self.extendHandle = None

    def getHandleTuples(self):
        pos = []
        for l in self.lines:
            pts=[self.window.imageview.getImageItem().mapFromScene(l.getSceneHandlePositions(i)[1]) for i in range(2)]
            for handle in lineRect.handles:
                if handle['type'] == 'sr':
                    pos.append((lineRect, handle['item'], lineRect.mapToParent(handle['item'].pos())))
        return pos

    def update_kymograph(self):
        tif=self.window.image
        mt=tif.shape[0]
        xx, yy = self.getTracePoints()
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
        self.kymographproxy = pg.SignalProxy(self.sigRegionChanged, rateLimit=3, slot=self.update_kymograph) #This will only update 3 Hz
        self.sigRegionChanged.connect(self.update_kymograph)
        self.kymograph.closeSignal.connect(self.deleteKymograph)

    def deleteKymograph(self):
        self.kymographproxy.disconnect()
        self.kymograph.closeSignal.disconnect(self.deleteKymograph)
        self.kymograph=None
        
class ROI_Rect(ROI_Wrapper, pg.ROI):
    kind = 'rectangle'
    plotSignal = Signal()
    def __init__(self, window, *args, **kargs):
        self.window = window
        pg.ROI.__init__(self, *args, **kargs)
        self.addScaleHandle([0, 1], [1, 0])
        self.addScaleHandle([1, 0], [0, 1])
        self.addScaleHandle([0, 0], [1, 1])
        self.addScaleHandle([1, 1], [0, 0])
        self.cropAction = QAction('&Crop', self, triggered=self.crop)
        ROI_Wrapper.__init__(self)

    def getMenu(self):
        ROI_Wrapper.getMenu(self)
        self.menu.addAction(self.cropAction)

    def crop(self):
        from window import Window
        r = self.boundingRect()
        p1 = r.topLeft() + self.state['pos']
        p2 = r.bottomRight() + self.state['pos']
        x1, y1 = p1.x(), p1.y()
        x2, y2 = p2.x(), p2.y()

        tif=self.window.image
        if len(tif.shape)==3:
            mt,mx,my=tif.shape
            if x1<0: x1=0
            if y1<0: y1=0
            if x2>=mx: x2=mx-1
            if y2>=my: y2=my-1
            newtif=tif[:,x1:x2+1,y1:y2+1]
        elif len(tif.shape)==2:
            mx,my=tif.shape
            if x1<0: x1=0
            if y1<0: y1=0
            if x2>=mx: x2=mx-1
            if y2>=my: y2=my-1
            mx,my=tif.shape
            newtif=tif[x1:x2+1,y1:y2+1]
        return Window(newtif,self.window.name+' Cropped',metadata=self.window.metadata)

    def getTrace(self, bounds=None, pts=None):
        x, y = self.state['pos']
        w, h = self.state['size']
        if x < 0:
            w = max(0, w + x)
            x = 0
        if y < 0:
            h = max(0, h + y)
            y = 0
        trace = np.average(self.window.image[:, x:x+w, y:y+h], (2, 1))
        if bounds:
            trace = trace[bounds[0]:bounds[1]]
        return trace

    def getMask(self):
        tif=self.window.image
        nDims=len(tif.shape)
        if nDims==4: #if this is an RGB image stack
            tif=np.mean(tif,3)
            mask=np.zeros(tif[0,:,:].shape,np.bool)
        elif nDims==3:
            if self.window.metadata['is_rgb']:  # [x, y, colors]
                mask=np.zeros(tif[:,:,0].shape,np.bool)
            else:                               # [t, x, y]
                mask=np.zeros(tif[0,:,:].shape,np.bool)  
        if nDims==2: #if this is a static image
            mask=np.zeros(tif.shape,np.bool)

        x, y = self.state['pos']
        w, h = self.state['size']
        if x < 0:
            w = max(0, w + x)
            x = 0
        if y < 0:
            h = max(0, h + y)
            y = 0

        mask[x:x+w, y:y+h] = True
        self.mask=np.array(np.where(mask)).T

class ROI_Polygon(ROI_Wrapper, pg.ROI):
    kind = 'freehand'
    plotSignal = Signal()
    def __init__(self, window, pts, *args, **kargs):
        self.window = window
        self.pts = pts
        pg.ROI.__init__(self, (0, 0), np.max(pts, 0), *args, **kargs)
        ROI_Wrapper.__init__(self)
        self.sigRegionChanged.connect(self.getMask)
        self.getMask()

    def contains(self, *pos):
        if len(pos) == 2:
            pos = [pg.Point(*pos)]
        p = QPainterPath()

        p.moveTo(self.pts[0])
        for i in range(len(self.pts)):
            p.lineTo(self.pts[i])
        return p.contains(*pos)

    def paint(self, p, *args):
        p.setPen(self.currentPen)
        for i in range(len(self.pts)):
            p.drawLine(self.pts[i], self.pts[i-1])

    def getMask(self):
        if hasattr(self, 'mask'):
            d = self.state['pos'] - self.lastState['pos']
            self.mask += np.array([d[0], d[1]], dtype=int)
            return
        pts=self.pts
        tif=self.window.image
        x=np.array([p[0] for p in pts])
        y=np.array([p[1] for p in pts])
        nDims=len(tif.shape)
        if nDims==4: #if this is an RGB image stack
            tif=np.mean(tif,3)
            mask=np.zeros(tif[0,:,:].shape,np.bool)
        elif nDims==3:
            if self.window.metadata['is_rgb']:  # [x, y, colors]
                mask=np.zeros(tif[:,:,0].shape,np.bool)
            else:                               # [t, x, y]
                mask=np.zeros(tif[0,:,:].shape,np.bool)  
        if nDims==2: #if this is a static image
            mask=np.zeros(tif.shape,np.bool)
            
        xx,yy=polygon(x,y,shape=mask.shape)
        mask[xx,yy]=True
        pts_plus=np.array(np.where(mask)).T
        for pt in pts_plus:
            if not self.contains(QPointF(pt[0],pt[1])):
                mask[pt[0],pt[1]]=0
        self.mask=np.array(np.where(mask)).T

    def getTrace(self,bounds=None,pts=None):
        ''' bounds are two points in time.  If bounds is not None, we only calculate values between the bounds '''
        tif=self.window.image
        nDims=len(tif.shape)
        if nDims==4: #if this is an RGB image stack  #[t, x, y, colors]
            tif=np.mean(tif,3)
            mx,my=tif[0,:,:].shape
        elif nDims==3:
            if self.window.metadata['is_rgb']:  # [x, y, colors]
                tif=np.mean(tif,2)
                mx,my=tif.shape
                tif=tif[np.newaxis]
            else: 
                mx,my=tif[0,:,:].shape
        elif nDims==2:
            mx,my=tif.shape
            tif=tif[np.newaxis]
        
        pts=self.mask
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

        trace=np.mean(tif[bounds[0]:bounds[1],xx,yy], 1) 
        if np.isnan(np.sum(trace)):
            return np.zeros(len(trace))
        return trace
    
def makeROI(kind,pts,window=None):
    if window is None:
        window=g.m.currentWindow

    if kind=='freehand':
        roi=ROI_Polygon(window, pts)
    elif kind=='rectangle':
        roi=ROI_Rectangle(window,pts[0], pts[1])
    elif kind=='line':
        roi=ROI_Line(window, pts[0], pts[1])
    elif kind == 'rect_line':
        roi = ROI_Rect_Line(window, pts)
    else:
        print("ERROR: THIS TYPE OF ROI COULD NOT BE FOUND: {}".format(kind))
        return None

    #roi.draw_from_points(pts)
    #roi.drawFinished()
    return roi
def load_roi(filename):
    f = open(filename, 'r')
    text=f.read()
    f.close()
    kind=None
    pts=None
    for text_line in text.split('\n'):
        if kind is None:
            kind=text_line
            pts=[]
        elif line=='':
            makeROI(kind,pts)
            kind=None
            pts=None
        else:
            pts.append(tuple(int(float(i)) for i in line.split()))