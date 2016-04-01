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
import threading

SHOW_MASK = False

ROI_COLOR = QColor(255, 255, 255)

class ROI_Drawing(pg.GraphicsObject):
    def __init__(self, window, x, y, type):
        pg.GraphicsObject.__init__(self)
        window.imageview.addItem(self)
        self.window = window
        self.pts = [pg.Point(round(x), round(y))]
        if self.extendRectLine():
            window.imageview.removeItem(self)
            return
        self.type = type
        self.state = {'pos': pg.Point(x, y), 'size': pg.Point(0, 0)}

    def extendRectLine(self):
        for roi in self.window.rois:
            if isinstance(roi, ROI_Rect_Line):
                a = roi.getNearestHandle(self.pts[0])
                if a:
                    roi.extendHandle = a[1]
                    self.extend = roi.extend
                    self.drawFinished = roi.extendFinished
                    #self.__dict__.update(roi.__dict__)
                    self.boundingRect = roi.boundingRect
                    return True
        return False

    def extend(self, x, y):
        new_pt = pg.Point(round(x), round(y))
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
        p.setPen(QPen(ROI_COLOR))
        if self.type == 'freehand':
            p.drawPolyline(*self.pts)
        elif self.type == 'rectangle':
            p.drawRect(self.boundingRect())
        elif self.type in ('rect_line', 'line'):
            p.drawLine(*self.pts)

    def drawFinished(self):
        self.window.imageview.removeItem(self)
        if self.type == 'freehand':
            r = ROI_Polygon(self.window, self.pts)
        elif self.type == 'rectangle':
            r = ROI_Rect(self.window, self.state['pos'], self.state['size'])
        elif self.type == 'line':
            r = ROI_Line(self.window, self.pts)
        elif self.type == 'rect_line':
            r = ROI_Rect_Line(self.window, self.pts)

        r.drawFinished()
        
        return r

    def contains(self, *args):
        if len(args) == 2:
            args = [pg.Point(*args)]
        return pg.GraphicsObject.contains(self, *args)

    def boundingRect(self):
        return QRectF(self.state['pos'].x(), self.state['pos'].y(), self.state['size'].x(), self.state['size'].y())

class ROI_Wrapper():
    init_args = {'removable': True, 'translateSnap': True, 'pen':ROI_COLOR}
    def __init__(self):
        self.getMenu()
        self.colorDialog=QColorDialog()
        self.colorDialog.colorSelected.connect(self.colorSelected)
        self.window.closeSignal.connect(self.delete)
        self.traceWindow = None
        self.mask=None
        self.linkedROIs = set()
        self.sigRegionChanged.connect(self.onRegionChange)

    def onRegionChange(self):
        self.getMask()
        to_move = self.linkedROIs.copy()
        rois = self.linkedROIs.copy()
        while rois:
            roi = rois.pop()
            to_move = to_move | roi.linkedROIs
            rois = rois | (roi.linkedROIs - to_move - {self})
        for roi in to_move:
            roi.sigRegionChanged.disconnect(roi.onRegionChange)
            roi.setPoints(self.pts)
            roi.sigRegionChanged.connect(roi.onRegionChange)

    def plot(self):
        self.plotAct.setText("Unplot")
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
        filename=g.settings['filename'].split('.')[0]
        if filename is not None and os.path.isfile(filename):
            filename= QFileDialog.getSaveFileName(g.m, 'Save ROI', filename, "Text Files (*.txt);;All Files (*.*)")
        else:
            filename= QFileDialog.getSaveFileName(g.m, 'Save ROI', '', "Text Files (*.txt);;All Files (*.*)")
        filename=str(filename)
        if filename != '':
            reprs = [repr(roi) for roi in self.window.rois]
            reprs = '\n'.join(reprs)
            open(filename, 'w').write(reprs)
        else:
            g.m.statusBar().showMessage('No File Selected')

    def unplot(self):
        self.plotAct.setText("Plot")
        try:
            self.traceWindow.indexChanged.disconnect(self.window.setIndex)
        except:
            # sometimes errors, says signals not connected
            pass
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
        self.plotAct = QAction("&Plot", self, triggered=lambda : self.plot() if self.traceWindow == None else self.unplot())
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

    def drawFinished(self):
        self.window.imageview.addItem(self)
        self.window.rois.append(self)
        self.window.currentROI = self
        self.getMask()

    def getMask(self):
        raise NotImplementedError(None)

    def getTrace(self):
        raise NotImplementedError(None)

    def __repr__(self):
        s = self.kind + '\n'
        for x, y in self.pts:
            s += '%d %d\n' % (x, y)
        return s

class ROI_Line(ROI_Wrapper, pg.LineSegmentROI):
    kind = 'line'
    plotSignal = Signal()
    def __init__(self, window, pos, *args, **kargs):
        self.init_args.update(kargs)
        self.window = window
        self.pts = pos
        pg.LineSegmentROI.__init__(self, positions=pos, *args, **self.init_args)
        self.kymographAct = QAction("&Kymograph", self, triggered=self.update_kymograph)
        self.kymograph = None
        ROI_Wrapper.__init__(self)

    def getMenu(self):
        ROI_Wrapper.getMenu(self)
        self.menu.addAction(self.kymographAct)

    def getMask(self):
        self.pts = [h['item'].pos() + self.pos() for h in self.handles]
        x=np.array([p[0] for p in self.pts], dtype=int)
        y=np.array([p[1] for p in self.pts], dtype=int)
        xx,yy=line(x[0],y[0],x[1],y[1])
        
        #exclude points outside bounds
        w, h = np.shape(self.window.image[0])
        rect = QRect(0, 0 ,w, h)
        ids = np.where([rect.contains(x, y) for x, y in zip(xx, yy)])
        self.mask = np.array([pg.Point(p) for p in np.transpose([xx[ids], yy[ids]])], dtype=int)
        if len(self.mask) > 0:
            self.minn = np.min(self.mask, 0)

    def getTrace(self, bounds=None, pts=None):
        if pts == None:
            pts = self.mask
        if len(pts) == 0:
            vals = np.zeros(len(self.window.image))
        else:
            xx, yy = pts.T
            vals = self.window.image[:, xx, yy]
            vals = np.average(vals, np.arange(np.ndim(vals)-1, 0, -1))
        
        if bounds:
            vals = vals[bounds[0]:bounds[1]]

        return vals

    def setPoints(self, pts):
        self.movePoint(self.handles[0]['item'], pts[0])
        self.movePoint(self.handles[1]['item'], pts[1])

    def update_kymograph(self):
        tif=self.window.image
        xx, yy = self.mask.T
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
        self.kymograph=Window(mn,name,metadata=self.window.metadata)
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
    def __init__(self, window, pts, width=1, *args, **kargs):
        self.init_args.update(kargs)
        self.window = window
        self.width = width
        self.pts = pts
        pg.MultiRectROI.__init__(self, pts, width, *args, **self.init_args)
        self.kymographAct = QAction("&Kymograph", self, triggered=self.update_kymograph)
        ROI_Wrapper.__init__(self)
        self.maskProxy = pg.SignalProxy(self.sigRegionChanged, rateLimit=5, slot=self.getMask) #This will only update 3 Hz
        self.kymograph = None
        self.extending = False
        self.extendHandle = None
        w, h = self.lines[0].size()
        self.lines[0].scale([1.0, width/5.0], center=[0.5,0.5])
        self.width = width
        self.currentLine = None

    def drawFinished(self):
        ROI_Wrapper.drawFinished(self)
        self.lines[0].removeHandle(2)
    
    def setPoints(self, pts):
        self.lines[0].movePoint(self.lines[0].handles[0]['item'], pts[0])
        for i in range(1, len(self.lines)):
            self.lines[i-1].movePoint(self.lines[i-1].handles[1]['item'], pts[i])
            self.lines[i].movePoint(self.lines[i].handles[0]['item'], pts[i])
        self.lines[-1].movePoint(self.lines[-1].handles[-1]['item'], pts[-1])
        self.maskProxy = pg.SignalProxy(self.sigRegionChanged, rateLimit=5, slot=self.getMask)

    def setCurrentPen(self, pen):
        for l in self.lines:
            l.currentPen = pen
            l.update()

    def hoverEvent(self, l, ev):
        self.currentLine = l
        if ev.enter:
            self.setCurrentPen(QPen(QColor(255, 255, 0)))
        elif ev.exit:
            self.setCurrentPen(l.pen)
        pg.ROI.hoverEvent(l, ev)

    def removeLink(self):
        ind = self.lines.index(self.currentLine)
        if ind == 0:
            self.delete()
            return
        for i in range(len(self.lines)-1, ind-1, -1):
            self.removeSegment(i)

    def getMenu(self):
        ROI_Wrapper.getMenu(self)
        removeLinkAction = QAction('Remove Link', self, triggered=self.removeLink)
        setWidthAction = QAction("Set Width", self, triggered=lambda: self.setWidth())
        self.menu.addAction(removeLinkAction)
        self.menu.addAction(setWidthAction)
        self.menu.addAction(self.kymographAct)

    def setWidth(self, newWidth=None):
        s = True
        if newWidth == None:
            newWidth, s = QInputDialog.getInt(None, "Enter a width value", 'Float Value', value = self.width)
        if not s:
            return
        self.lines[0].scale([1.0, newWidth/self.width], center=[0.5,0.5])
        self.width = newWidth

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
            if returnMappedCoords:
                rgn, coord = rgn
                coords.append(np.concatenate(coord.T))
            rgns.append(rgn)
            
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
        l = self.lines[-1]
        self.lines[-1].raiseContextMenu = self.raiseContextMenu
        self.lines[-1].getMenu = self.getMenu
        self.lines[-1].hoverEvent = lambda ev: self.hoverEvent(l, ev)

    def getMask(self):
        self.pts = [pg.Point(self.window.imageview.getImageItem().mapFromScene(self.lines[0].getSceneHandlePositions(0)[1]))]
        for l in self.lines:
            self.pts.append(pg.Point(self.window.imageview.getImageItem().mapFromScene(l.getSceneHandlePositions(1)[1])))

        if self.lines[0].handles[1]['item'].pos()[1] <= 1:
            xx = []
            yy = []
            for i in range(1, len(self.pts)):
                p1, p2=[self.pts[i-1], self.pts[i]]
                xs,ys=line(*[int(a) for a in (p1.x(),p1.y(),p2.x(),p2.y())])
                xx.append(xs)
                yy.append(ys)
            xx = np.concatenate(xx)
            yy = np.concatenate(yy)

        else:
            vals, coords = self.getArrayRegion(self.window.image, self.window.imageview.getImageItem(), axes=(1, 2), returnMappedCoords=True)
            # vals includes outside coordinates. Recalculate
            xx, yy = coords.T.astype(int)
        
        w, h = np.shape(self.window.image[0])
        rect = QRect(0, 0 ,w, h)
        ids = np.where([rect.contains(xx[i], yy[i]) for i in range(len(xx))])
        xx = xx[ids]
        yy = yy[ids]

        self.mask = np.transpose([xx, yy])
        if self.mask.size != 0:
            self.minn = np.min(self.mask, 0)

            if SHOW_MASK:
                xx, yy = np.transpose(self.mask)
                img = np.zeros(self.window.imageDimensions())
                img[xx, yy] = 1
                self.window.imageview.setImage(img)

    def getTrace(self, bounds=None, pts=None):
        xx, yy = self.mask.T
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
            self.addSegment(pg.Point(int(x), int(y)), connectTo=self.lines[-1].handles[1]['item'])
        else:
            self.lines[-1].handles[-1]['item'].movePoint(self.window.imageview.getImageItem().mapToScene(pg.Point(x, y))) 

    def extendFinished(self):
        self.extending = False
        self.extendHandle = None

    def getHandleTuples(self):
        pos = []
        for l in self.lines:
            pts=[self.window.imageview.getImageItem().mapFromScene(l.getSceneHandlePositions(i)[1]) for i in range(2)]
            for handle in l.handles:
                if handle['type'] == 'sr':
                    pos.append((l, handle['item'], l.mapToParent(handle['item'].pos())))
        return pos

    def update_kymograph(self):
        tif=self.window.image
        mt=tif.shape[0]
        xx, yy = self.mask.T
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
    def __init__(self, window, pos, size, *args, **kargs):
        self.init_args.update(kargs)
        self.window = window
        pg.ROI.__init__(self, pos, size, *args, **self.init_args)
        self.addScaleHandle([0, 1], [1, 0])
        self.addScaleHandle([1, 0], [0, 1])
        self.addScaleHandle([0, 0], [1, 1])
        self.addScaleHandle([1, 1], [0, 0])
        self.cropAction = QAction('&Crop', self, triggered=self.crop)
        ROI_Wrapper.__init__(self)

    def setPoints(self, pts):
        self.setPos(pts[0], finish=False)
        self.setSize(pts[1], finish=False)

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

        self.pts = [[self.state['pos'].x(), self.state['pos'].y()], [self.state['size'].x(), self.state['size'].y()]]
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
        if len(self.mask) > 0:
            self.minn = np.min(self.mask, 0)
            if SHOW_MASK:
                self.window.imageview.setImage(mask)

    def __repr__(self):
        s = self.kind + '\n'
        s += '%d %d\n' % (self.state['pos'][0], self.state['pos'][1])
        s += '%d %d\n' % (self.state['size'][0], self.state['size'][1])
        return s

class ROI_Polygon(ROI_Wrapper, pg.ROI):
    kind = 'freehand'
    plotSignal = Signal()
    def __init__(self, window, pts, *args, **kargs):
        self.init_args.update(kargs)
        self.window = window
        self.pts = [pg.Point(pt[0], pt[1]) for pt in pts]
        w, h = np.ptp(self.pts, 0)
        pg.ROI.__init__(self, (0, 0), (w, h), *args, **self.init_args)
        ROI_Wrapper.__init__(self)

    def setPoints(self, pts):
        self.pts = pts
        self.getMask()

    def boundingRect(self):
        r = pg.ROI.boundingRect(self)
        r.translate(*np.min(self.pts, 0))
        return r

    def contains(self, *pos):
        if len(pos) == 2:
            pos = [pg.Point(*pos)]
        p = QPainterPath()

        p.moveTo(self.pts[0])
        for i in range(len(self.pts)):
            p.lineTo(self.pts[i])
        return p.contains(*pos)

    def __repr__(self):
        s = self.kind + '\n'
        for x, y in self.pts:
            s += '%d %d\n' % (x, y)
        return s

    def paint(self, p, *args):
        p.setPen(self.currentPen)
        for i in range(len(self.pts)):
            p.drawLine(self.pts[i], self.pts[i-1])

    def getMask(self):
        if self.mask is not None:
            xx, yy = np.transpose(self._mask)
        else:
            self.minn = np.min(self.pts, 0)
            x, y = np.transpose(self.pts - self.minn)
            mask=np.zeros(self.window.imageDimensions())
            
            xx,yy=polygon(x,y,shape=mask.shape)
            self._mask = np.transpose([xx, yy])

        w, h = self.window.imageDimensions()
        rect = QRect(0, 0, w, h)
        self.minn = self.state['pos'] + np.min(self.pts, 0)
        self.mask = np.array([p for p in np.transpose([xx, yy]) + self.minn if rect.contains(p[0], p[1])], dtype=int)

        img = np.zeros(self.window.imageDimensions())
        if len(self.mask) > 0:
            xx, yy = self.mask.T.astype(int)
            img[xx, yy] = 1
            if SHOW_MASK:
                self.window.imageview.setImage(img)

    def getTrace(self,bounds=None,pts=None):
        ''' bounds are two points in time.  If bounds is not None, we only calculate values between the bounds '''
        tif=self.window.imageArray()
        mt, mx, my = tif.shape
        pts=self.mask
        if len(pts) == 0:
            return np.zeros([bounds[1]-bounds[0]])

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

        if len(xx) == 0:
            return np.zeros([bounds[1]-bounds[0]])
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
        roi=ROI_Rect(window,pts[0], pts[1])
    elif kind=='line':
        roi=ROI_Line(window, pos=(pts))
    elif kind == 'rect_line':
        roi = ROI_Rect_Line(window, pts)
        #for p in pts[3:]:
        #    roi.extend(p[0], p[1])
        #    roi.extendFinished()

    else:
        print("ERROR: THIS TYPE OF ROI COULD NOT BE FOUND: {}".format(kind))
        return None

    roi.drawFinished()    
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
        elif text_line=='':
            makeROI(kind,pts)
            kind=None
            pts=None
        else:
            pts.append(tuple(int(float(i)) for i in text_line.split()))