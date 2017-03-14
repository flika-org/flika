# -*- coding: utf-8 -*-
"""
Flika
@author: Kyle Ellefsen
@author: Brett Settle
@license: MIT
"""
from qtpy import QtGui, QtCore, QtWidgets
import pyqtgraph as pg
from pyqtgraph.graphicsItems.ROI import Handle
from skimage.draw import polygon, line
import numpy as np
import os
from scipy.ndimage.interpolation import rotate
from . import global_vars as g
from .utils.misc import random_color, save_file_gui
from .tracefig import roiPlot

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
        self.color = QtGui.QColor(g.settings['roi_color']) if g.settings['roi_color'] != 'random' else random_color()
        

    def cancel(self):
        g.currentWindow.imageview.removeItem(self)
        g.currentWindow.currentROI = None

    def extendRectLine(self):
        for roi in self.window.rois:
            if isinstance(roi, ROI_rect_line):
                a = roi.getNearestHandle(self.pts[0])
                if a:
                    roi.extendHandle = a
                    self.extend = roi.extend
                    self.drawFinished = roi.extendFinished
                    #self.__dict__.update(roi.__dict__)
                    self.boundingRect = roi.boundingRect
                    return True
        return False

    def extend(self, x, y):
        new_pt = pg.Point(round(x), round(y))
        if self.type == 'freehand':
            if self.pts[-1] != new_pt:
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
        pen = QtGui.QPen(self.color)
        pen.setWidth(0)
        p.setPen(pen)
        if self.type == 'freehand':
            p.drawPolyline(*self.pts)
        elif self.type == 'rectangle':
            p.drawRect(self.boundingRect())
        elif self.type in ('rect_line', 'line'):
            p.drawLine(*self.pts)

    def drawFinished(self):
        self.window.imageview.removeItem(self)
        if self.type == 'freehand':
            if len(self.pts) < 4:
                return None
            r = ROI(self.window, self.pts)
        elif self.type == 'rectangle':
            r = ROI_rectangle(self.window, self.state['pos'], self.state['size'])
        elif self.type == 'line':
            r = ROI_line(self.window, self.pts)
        elif self.type == 'rect_line':
            r = ROI_rect_line(self.window, self.pts)

        r.drawFinished()
        pen = QtGui.QPen(self.color)
        pen.setWidth(0)
        r.setPen(pen)
        return r

    def contains(self, *args):
        if len(args) == 2:
            args = [pg.Point(*args)]
        return pg.GraphicsObject.contains(self, *args)

    def boundingRect(self):
        return QtCore.QRectF(self.state['pos'].x(), self.state['pos'].y(), self.state['size'].x(), self.state['size'].y())

class ROI_Wrapper():
    ''' ROI wrapper interface for all ROI types, template class for duplicate functions and functions to override
        connect window closeEvent to ROI delete
        set the window currentROI to self

    Attributes:
        colorDialog: dialog for selecting the color of the ROI and its trace
        traceWindow: the tracewindow that this ROI is plotted to, or None
        mask: array of XY values that are contained within the ROI
        pts: array of XY values used to copy the ROI
        linkedROIs: set of rois that act as one ROI

    Not Implemented Functions:
        getMask()
        getPoints()

    Functions:
        plot():
            run the roiPlot function and link this window to the traceWindow
            Returns the traceWindow
        unplot():
            Remove the roi from its traceWindow
        link(roi):
            add an roi to the linkedROIs set, so they translate together
        colorSelected(QColor):
            set the color of the roi
        copy():
            store the roi in the clipboard
        paste():
            Create an roi from the clipboard ROI using roi.getPoints()
        delete():
            unplot the ROI, remove the ROI from the window, clear it from the clipboard if it was copied, disconnect all signals
        drawFinished():
            add the ROI to the window, called by ROI_Drawing
        str():
            return type and self.pts for recreating the ROI
    '''
    INITIAL_ARGS = {'translateSnap': True, 'removable': True, 'snapSize': 1, 'scaleSnap': True}
    def __init__(self, window, pts):
        self.window = window
        self.colorDialog=QtWidgets.QColorDialog()
        self.colorDialog.colorSelected.connect(self.colorSelected)
        self.window.closeSignal.connect(self.delete)
        self.window.currentROI = self
        self.traceWindow = None  # To test if roi is plotted, check if traceWindow is None
        self.pts = np.array(pts)
        self.linkedROIs = set()
        self.resetSignals()
        self.makeMenu()

    def resetSignals(self):
        try:
            self.sigRegionChanged.disconnect()
        except:
            pass
        try:
            self.sigRegionChangeFinished.disconnect()
        except:
            pass
        self.sigRegionChanged.connect(self.onRegionChange)
        self.sigRegionChangeFinished.connect(self.onRegionChangeFinished)

    def updateLinkedROIs(self, finish=False):
        for roi in self.linkedROIs:
            roi.blockSignals(True)
            roi.draw_from_points(self.pts, finish=False)
            if roi.traceWindow != None:
                if not finish:
                    roi.traceWindow.translated(roi)
                else:
                    roi.traceWindow.translateFinished(roi)
            roi.blockSignals(False)

    def getSnapPosition(self, *args, **kargs):
        shift = pg.Point(.5, .5) if isinstance(self, (ROI_rect_line, )) else pg.Point(0, 0)
        return pg.ROI.getSnapPosition(self, *args, **kargs) + shift

    def onRegionChange(self):
        self.pts = self.getPoints()
        self.updateLinkedROIs(finish=False)
        
    def onRegionChangeFinished(self):
        self.pts = self.getPoints()
        self.updateLinkedROIs(finish=True)

    def link(self,roi):
        '''This function links this roi to another, so a translation of one will cause a translation of the other'''
        if not isinstance(roi, type(self)):
            return
        join = self.linkedROIs | roi.linkedROIs | {self, roi}
        self.linkedROIs = join - {self}
        roi.linkedROIs = join - {roi}

    def getMask(self):
        '''
        Returns the list of integer points contained within the ROI
        '''
        raise NotImplementedError()

    def getTrace(self, bounds=None):
        '''
        Compute the average of the pixels within this ROI for the window of this ROI, return an array of average values, cropped by bounds
        '''
        trace = None
        if self.window.image.ndim == 4 or self.window.metadata['is_rgb']:
            g.alert("Plotting trace of RGB movies is not supported. Try splitting the channels.")
            return None
        s1, s2 = self.getMask()
        if np.size(s1) == 0 or np.size(s2) == 0:
            trace = np.zeros(self.window.mt)

        elif self.window.image.ndim == 3:
            trace = self.window.image[:, s1, s2]
            while trace.ndim > 1:
                trace = np.average(trace, 1)
        elif self.window.image.ndim == 2:
            trace = self.window.image[s1, s2]
            trace = [np.average(trace)]

        if bounds:
            trace = trace[bounds[0]:bounds[1]]
        return trace

    def getPoints(self):
        '''
        return the points that represent this ROI. Used for exporting
        '''
        raise NotImplementedError()

    def draw_from_points(self, pts, finish=True):
        '''
        Redraw the ROI from the given points, used on linked ROIs
        '''
        raise NotImplementedError()

    def setMouseHover(self, hover):
        ## Inform the ROI that the mouse is(not) hovering over it
        if self.mouseHovering == hover:
            return
        self.mouseHovering = hover
        if hover:
            self.currentPen = pg.mkPen(QtGui.QColor(255, 0, 0))
        else:
            self.currentPen = self.pen

        self.update()

    def plot(self):
        self.traceWindow = roiPlot(self)
        if self.traceWindow == None:
            return
        self.traceWindow.indexChanged.connect(self.window.setIndex)
        self.plotSignal.emit()
        return self.traceWindow

    def changeColor(self):
        self.colorDialog.open()
        
    def colorSelected(self, color):
        if color.isValid():
            self.setPen(QtGui.QColor(color.name()))
            self.sigRegionChangeFinished.emit(self)

    def unplot(self):
        try:
            self.traceWindow.indexChanged.disconnect(self.window.setIndex)
        except:
            # sometimes errors, says signals not connected
            pass
        if self.traceWindow != None:
            self.traceWindow.removeROI(self)
            self.traceWindow = None

    def copy(self):
        g.clipboard=self

    def raiseContextMenu(self, ev):
        pos = ev.screenPos()
        self.menu.addSeparator()
        self.menu.addActions(self.window.menu.actions())
        self.menu.popup(QtCore.QPoint(pos.x(), pos.y()))
    
    def makeMenu(self):
        def plotPressed():
            if plotAct.text() == "&Plot":
                self.plot()
            else:
                self.unplot()

        plotAct = QtWidgets.QAction("&Plot", self, triggered=plotPressed)
        colorAct = QtWidgets.QAction("&Change Color",self,triggered=self.changeColor)
        copyAct = QtWidgets.QAction("&Copy", self, triggered=self.copy)
        remAct = QtWidgets.QAction("&Delete", self, triggered=self.delete)
        self.menu = QtWidgets.QMenu("ROI Menu")

        def updateMenu():
            #plotAct.setEnabled(self.window.image.ndim > 2)
            plotAct.setText("&Plot" if self.traceWindow == None else "&Unplot")
            self.window.menu.aboutToShow.emit()

        self.menu.addAction(plotAct)
        self.menu.addAction(colorAct)
        self.menu.addAction(copyAct)
        self.menu.addAction(remAct)
        self.menu.aboutToShow.connect(updateMenu)


    def delete(self):
        self.unplot()
        for roi in self.linkedROIs:
            if self in roi.linkedROIs:
                roi.linkedROIs.remove(self)
        if self in self.window.rois:
            self.window.rois.remove(self)
        self.window.currentROI=None
        self.window.imageview.removeItem(self)
        self.window.closeSignal.disconnect(self.delete)
        if g.clipboard == self:
            g.clipboard = None

    def drawFinished(self):
        self.window.imageview.addItem(self)
        self.window.rois.append(self)
        self.window.currentROI = self

    def str(self):
        s = self.kind + '\n'
        for x, y in self.pts:
            s += '%d %d\n' % (x, y)
        return s

    def showMask(self):
        from .window import Window
        im = np.zeros_like(self.window.imageview.getImageItem().image)
        s1, s2 = self.getMask()
        im[s1, s2] = 1
        return Window(im)


class ROI_line(ROI_Wrapper, pg.LineSegmentROI):
    '''
    ROI Line class for selecting a straight line of pixels between two points
        Extends from the ROI_Wrapper class and pyqtgraph ROI.LineSegmentROI
    '''
    kind = 'line'
    plotSignal = QtCore.Signal()
    
    def __init__(self, window, positions, **kargs):
        roiArgs = self.INITIAL_ARGS.copy()
        roiArgs.update(kargs)
        pg.LineSegmentROI.__init__(self, positions=positions, **roiArgs)
        self.kymograph = None
        self.kymographAct = QtWidgets.QAction("&Kymograph", self, triggered=self.update_kymograph)
        ROI_Wrapper.__init__(self, window, positions)

    def paint(self, p, *args):
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setPen(self.currentPen)
        h1 = self.handles[0]['item'].pos()
        h2 = self.handles[1]['item'].pos()
        p.drawLine(h1, h2)

    def resetSignals(self):
        ROI_Wrapper.resetSignals(self)
        self.sigRegionChanged.connect(self.snapPoints)

    def snapPoints(self):
        fix = False
        self.blockSignals(True)
        for handle in self.handles:
            pos = handle['pos']
            pos_snap = self.getSnapPosition(pg.Point(pos))# + pg.Point(.5, .5)
            if not (pos == pos_snap):
                handle['item'].setPos(pos_snap)
                handle['pos'] = pos_snap
                fix = True

        self.blockSignals(False)
        #if fix:
        #    self.sigRegionChanged.emit(self)

    def draw_from_points(self, pts, finish=True):
        self.blockSignals(True)
        self.movePoint(self.handles[0]['item'], pts[0], finish=False)
        self.movePoint(self.handles[1]['item'], pts[1], finish=False)
        self.pts = pts
        self.blockSignals(False)
        if finish:
            self.sigRegionChangeFinished.emit(self)

    def delete(self):
        ROI_Wrapper.delete(self)
        if self.kymograph:
            self.deleteKymograph()

    def getMask(self):
        x=np.array([p[0] for p in self.pts], dtype=int)
        y=np.array([p[1] for p in self.pts], dtype=int)
        xx, yy = line(x[0],y[0],x[1],y[1])
        xx = xx[xx < self.window.mx]
        yy = yy[yy < self.window.my]
        return xx, yy

    def getPoints(self):
        return np.array([handle['pos'] + self.state['pos'] for handle in self.handles])

    def makeMenu(self):
        ROI_Wrapper.makeMenu(self)
        self.menu.addAction(self.kymographAct)
        self.kymographAct.setEnabled(self.window.image.ndim == 3 and not self.window.metadata['is_rgb'])

    def update_kymograph(self):
        tif=self.window.image
        if tif.ndim != 3:
            g.alert("Can only kymograph a 3d movie")
            return

        xx, yy = self.getMask()
        mt = len(tif)
        if len(xx) == 0:
            return
        idx_to_keep = np.logical_not( (xx>=self.window.mx) | (xx<0) | (yy>=self.window.my) | (yy<0))
        xx = xx[idx_to_keep]
        yy = yy[idx_to_keep]
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
        from .window import Window
        oldwindow=g.currentWindow
        name=oldwindow.name+' - Kymograph'
        self.kymograph=Window(mn,name,metadata=self.window.metadata)
        self.sigRegionChanged.connect(self.update_kymograph)
        self.kymograph.closeSignal.connect(self.deleteKymograph)
        self.sigRemoveRequested.connect(self.deleteKymograph)

    def deleteKymograph(self):
        self.kymograph.closeSignal.disconnect(self.deleteKymograph)
        self.kymograph=None

class ROI_rectangle(ROI_Wrapper, pg.ROI):
    '''
    ROI rectangle class for selecting a set width and height group of pixels on an image
        Extends from pyqtgraph ROI and ROI_Wrapper

    Parameters:
        window: parent window to draw the ROI in
        pos: XY coordinate of the upper left corner of the rectangle
        size: (width, height) tuple of the ROI
        resizable: scale handles will be drawn on each corner if this is True
        See pg.ROI for other parameters

    Functions:
        crop():
            create a new window with the original image cropped within this ROI
    '''
    kind = 'rectangle'
    plotSignal = QtCore.Signal()

    def __init__(self, window, pos, size, resizable=True, **kargs):
        roiArgs = self.INITIAL_ARGS.copy()
        roiArgs.update(kargs)
        pos = np.array(pos, dtype=int)
        size = np.array(size, dtype=int)

        pg.ROI.__init__(self, pos, size, **roiArgs)
        if resizable:
            self.addScaleHandle([0, 1], [1, 0])
            self.addScaleHandle([1, 0], [0, 1])
            self.addScaleHandle([0, 0], [1, 1])
            self.addScaleHandle([1, 1], [0, 0])
        self.cropAction = QtWidgets.QAction('&Crop', self, triggered=self.crop)
        ROI_Wrapper.__init__(self, window, [pos, size])

    def getPoints(self):
        return np.array([self.state['pos'], self.state['size']], dtype=int)

    def getMask(self):
        x, y = self.state['pos']
        w, h = self.state['size']

        xmin = max(x, 0)
        ymin = max(y, 0)
        xmax = min(x+w, self.window.mx)
        ymax = min(y+h, self.window.my)

        xx, yy = np.meshgrid(np.arange(xmin, xmax, dtype=int), np.arange(ymin, ymax, dtype=int))

        return xx.flatten(), yy.flatten()

    def draw_from_points(self, pts, finish=True):
        self.setPos(pts[0], finish=False)
        self.setSize(pts[1], finish=False)
        self.pts = np.array(pts)
        if finish:
            self.sigRegionChangeFinished.emit(self)

    def makeMenu(self):
        ROI_Wrapper.makeMenu(self)
        self.menu.addAction(self.cropAction)

    def crop(self):
        from .window import Window
        r = self.boundingRect()
        p1 = r.topLeft() + self.state['pos']
        p2 = r.bottomRight() + self.state['pos']
        x1, y1 = int(p1.x()), int(p1.y())
        x2, y2 = int(p2.x()), int(p2.y())

        tif=self.window.image
        if tif.ndim==3:
            mt,mx,my=tif.shape
            if x1<0: x1=0
            if y1<0: y1=0
            if x2>=mx: x2=mx-1
            if y2>=my: y2=my-1
            newtif=tif[:,x1:x2,y1:y2]
        elif tif.ndim==2:
            mx,my=tif.shape
            if x1<0: x1=0
            if y1<0: y1=0
            if x2>=mx: x2=mx-1
            if y2>=my: y2=my-1
            mx,my=tif.shape
            newtif=tif[x1:x2,y1:y2]
        elif tif.ndim==4:
            mt,mx,my,mc=tif.shape
            if x1<0: x1=0
            if y1<0: y1=0
            if x2>=mx: x2=mx-1
            if y2>=my: y2=my-1
            newtif=tif[:,x1:x2,y1:y2]
        else:
            g.alert("Image dimensions not understood")
            return None
        return Window(newtif,self.window.name+' Cropped',metadata=self.window.metadata)

class ROI(ROI_Wrapper, pg.PolyLineROI):
    kind = 'freehand'
    plotSignal = QtCore.Signal()
    def __init__(self, window, pts, **kargs):
        roiArgs = self.INITIAL_ARGS.copy()
        roiArgs.update(kargs)
        roiArgs['closed'] = True
        pg.PolyLineROI.__init__(self, pts, **roiArgs)
        ROI_Wrapper.__init__(self, window, pts)
        self._untranslated_mask = None

    def draw_from_points(self, pts, finish=False):
        return
        self.blockSignals(True)
        self.setPoints([pg.Point(p) for p in pts], closed=True)
        self.blockSignals(False)

    def setMouseHover(self, hover):
        for seg in self.segments:
            seg.setPen(QtGui.QColor(255, 0, 0) if hover else self.currentPen)

    def translate(self, pos, y=None, *args, **kargs):
        if y is None:
            pos = pg.Point(pos)
        else:
            # avoid ambiguity where update is provided as a positional argument
            if isinstance(y, bool):
                raise TypeError("Positional arguments to setPos() must be numerical.")
            pos = pg.Point(pos, y)


        pos = self.getSnapPosition(pos) 
        pg.PolyLineROI.translate(self, pos, *args, **kargs)
        for roi in self.linkedROIs:
            roi.blockSignals(True)
            roi.setPos(roi.state['pos'] + pos)
            roi.pts = roi.getPoints()
            roi.blockSignals(False)

    def getPoints(self):
        return np.array([h.pos() + self.state['pos'] for h in self.getHandles()], dtype=int)

    def removeSegment(self, seg):
        for handle in seg.handles[:]:
            seg.removeHandle(handle['item'])
        self.segments.remove(seg)
        self.scene().removeItem(seg)

    def addSegment(self, h1, h2, index=None):
        seg = pg.LineSegmentROI(handles=(h1, h2), pen=self.pen, parent=self, movable=False)
        if index is None:
            self.segments.append(seg)
        else:
            self.segments.insert(index, seg)
        seg.setAcceptedMouseButtons(QtCore.Qt.LeftButton)
        seg.setZValue(self.zValue()+1)
        seg.setMouseHover = self.setMouseHover
        for h in seg.handles:
            h['item'].setAcceptedMouseButtons(h['item'].acceptedMouseButtons() | QtCore.Qt.LeftButton) ## have these handles take left clicks too, so that handles cannot be added on top of other handles
            h['item'].setOpacity(0)

    def getMask(self):
        if self._untranslated_mask is not None:
            xx = self._untranslated_mask[0] + int(self.state['pos'][0])
            yy = self._untranslated_mask[1] + int(self.state['pos'][1])
        else:
            x, y = np.transpose(self.pts)
            mask=np.zeros(self.window.imageDimensions())
            xx,yy=polygon(x,y,shape=mask.shape)
            self._untranslated_mask = xx, yy
        return xx, yy

class ROI_rect_line(ROI_Wrapper, QtWidgets.QGraphicsObject):
    kind = 'rect_line'
    plotSignal = QtCore.Signal()
    sigRegionChanged = QtCore.Signal(object)
    sigRegionChangeFinished = QtCore.Signal(object)

    def __init__(self, window, pts, width=1, **kargs):
        self.roiArgs = self.INITIAL_ARGS.copy()
        self.roiArgs.update(kargs)
        self.roiArgs['scaleSnap'] = False
        self.width = width
        self.currentLine = None
        self.kymograph = None
        QtWidgets.QGraphicsObject.__init__(self)
        self.kymographAct = QtWidgets.QAction("&Kymograph", self, triggered=self.update_kymograph)
        self.removeLinkAction = QtWidgets.QAction('Remove Last Link', self, triggered=self.removeSegment)
        self.setWidthAction = QtWidgets.QAction("Set Width", self, triggered=lambda: self.setWidth())
        ROI_Wrapper.__init__(self, window, pts)
        self.getPoints = self.getHandlePositions
        self.pen = QtGui.QPen(QtGui.QColor(255, 255, 0))
        self.pen.setWidth(0)
        self.lines = []
        if len(pts) < 2:
            raise Exception("Must start with at least 2 points")
        self.addSegment(pts[1], connectTo=pts[0])
        for p in pts[2:]:
            self.addSegment(p)
        self.extending = False

    def delete(self):
        ROI_Wrapper.delete(self)
        if self.kymograph:
            self.deleteKymograph()

    def draw_from_points(self, pts, finish=False):
        while len(self.lines) > 1:
            self.removeSegment(self.lines[-1])

        self.lines[0].movePoint(0, pts[0])
        self.lines[0].movePoint(1, pts[1])
        for p in pts[2:]:
            self.addSegment(p)

        if finish:
            self.sigRegionChangeFinished.emit(self)
        self.pts = pts

    def getTrace(self, bounds=None):
        if self.window.image.ndim > 3 or self.window.metadata['is_rgb']:
            g.alert("Plotting trace of RGB movies is not supported. Try splitting the channels.")
            return None
        if self.window.image.ndim == 3:
            region = self.getArrayRegion(self.window.imageview.image, self.window.imageview.getImageItem(), (1, 2))
            while region.ndim > 1:
                region = np.average(region, 1)
        elif self.window.image.ndim == 2:
            region = self.getArrayRegion(self.window.imageview.image, self.window.imageview.getImageItem(), (0, 1))
            region = np.average(region)

        if bounds:
            region = region[bounds[0]:bounds[1]]
        return region

    def preview(self):
        im = self.getArrayRegion(self.window.imageview.getImageItem().image, self.window.imageview.getImageItem(), (0, 1))
        if not hasattr(self, 'prev'):
            from .window import Window
            self.prev = Window(im)
            self.sigRegionChanged.connect(lambda a: self.preview())
        else:
            self.prev.imageview.setImage(im)

    def lineRegionChange(self, line):
        line.blockSignals(True)
        for i in range(2):
            p = self.mapFromScene(line.getHandles()[i].scenePos())
            p = line.getSnapPosition([p.x(), p.y()])
            if line.getHandles()[i].isMoving:
                line.movePoint(i, p)
        line.blockSignals(False)
        self.pts = self.getPoints()
        self.sigRegionChanged.emit(self)

    def getHandlePositions(self):
        """Return the positions of all handles in local coordinates."""
        p = self.mapFromScene(self.lines[0].getHandles()[0].scenePos())
        p = self.lines[0].getSnapPosition([p.x(), p.y()])
        pos = [p]
        for l in self.lines:
            p = self.mapFromScene(l.getHandles()[1].scenePos())
            p = l.getSnapPosition([p.x(), p.y()])
            pos.append(p)
        self.pts = pos
        return self.pts
        
    def getArrayRegion(self, arr, img=None, axes=(0,1), **kwds):
        rgns = []
        for l in self.lines:
            rgn = l.getArrayRegion(arr, img, axes=axes, **kwds)
            if rgn is None:
                continue
                #return None
            rgns.append(rgn)
            #print l.state['size']
            
        ## make sure orthogonal axis is the same size
        ## (sometimes fp errors cause differences)
        if img.axisOrder == 'row-major':
            axes = axes[::-1]
        ms = min([r.shape[axes[1]] for r in rgns])
        sl = [slice(None)] * rgns[0].ndim
        sl[axes[1]] = slice(0,ms)
        rgns = [r[sl] for r in rgns]
        #print [r.shape for r in rgns], axes
        
        return np.concatenate(rgns, axis=axes[0])
        
    def addSegment(self, pos=(0,0), connectTo=None):
        """
        Add a new segment to the ROI connecting from the previous endpoint to *pos*.
        (pos is specified in the parent coordinate system of the MultiRectROI)
        """
        ## by default, connect to the previous endpoint
        if connectTo is None:
            connectTo = self.lines[-1].getHandles()[1]
            
        ## create new ROI
        newRoi = pg.ROI((0,0), [1, self.width], parent=self, pen=self.pen, **self.roiArgs)
        self.lines.append(newRoi)
        
        ## Add first SR handle
        if isinstance(connectTo, Handle):
            h = self.lines[-1].addScaleRotateHandle([0, 0.5], [1, 0.5], item=connectTo)
            newRoi.movePoint(connectTo, connectTo.scenePos(), coords='scene')
        else:
            h = self.lines[-1].addScaleRotateHandle([0, 0.5], [1, 0.5])
            newRoi.movePoint(h, connectTo, coords='scene')
            
        ## add second SR handle
        h = self.lines[-1].addScaleRotateHandle([1, 0.5], [0, 0.5]) 
        newRoi.movePoint(h, pos)
            
        newRoi.translatable = False
        newRoi.hoverEvent = lambda e: self.hoverEvent(newRoi, e)
        newRoi.sigRegionChanged.connect(self.lineRegionChange)
        newRoi.raiseContextMenu = self.raiseContextMenu
        #newRoi.sigRegionChangeStarted.connect(self.roiChangeStartedEvent) 
        newRoi.sigRegionChangeFinished.connect( lambda a: self.sigRegionChangeFinished.emit(self))
        self.sigRegionChanged.emit(self)

    def getNearestHandle(self, pos, max_distance=None):
        h = None
        d = max_distance
        for l in self.lines:
            for i in range(2):
                p = self.window.imageview.getImageItem().mapFromScene(l.getSceneHandlePositions(i)[1])
                d = pg.Point(p - pos).manhattanLength()
                if max_distance == None:
                    if h == None or d < dist:
                        h = l.handles[i]['item']
                        dist = d
                else:
                    if d <= dist:
                        h = l.handles[i]['item']
                        dist = d
        return h
    

    def removeSegment(self, segment=None): 
        """Remove a segment from the ROI."""
        if segment == None:
            segment = self.currentLine
        self.lines.remove(segment)
        for h in segment.getHandles():
            h.disconnectROI(segment)

        self.scene().removeItem(segment)
        segment.sigRegionChanged.disconnect() 
        segment.sigRegionChangeFinished.disconnect()
        if len(self.lines) == 0:
            self.delete()
        else:
            self.sigRegionChanged.emit(self)

    def extend(self, x, y, finish=True):
        point = self.lines[0].getSnapPosition([x, y])
        if not self.extending:
            h = self.getNearestHandle(pg.Point(x, y))
            if h != None and len(h.rois) > 1:
                return
            self.extending = True
            self.addSegment(point, connectTo=h)
        else:
            self.lines[-1].handles[-1]['item'].movePoint(self.window.imageview.getImageItem().mapToScene(point))
        self.sigRegionChanged.emit(self)
        if finish:
            self.sigRegionChangeFinished.emit(self)

    def extendFinished(self):
        self.extending = False
        self.extendHandle = None
        self.sigRegionChangeFinished.emit(self)
        if self.lines[0].getHandles()[0] in self.lines[-1].getHandles():
            self.lines.insert(0, self.lines[-1])
            self.lines = self.lines[:-1]
            self.lines[0].handles = self.lines[0].handles[::-1]

    def hoverEvent(self, l, ev):
        self.currentLine = l
        if ev.enter:
            pen = QtGui.QPen(QtGui.QColor(255, 0, 0))
            pen.setWidth(0)
            self.setCurrentPen(pen)
        elif ev.exit:
            self.setCurrentPen(self.pen)

    def getMask(self):
        xxs = []
        yys = []
        for i in range(len(self.pts)-1):
            p1, p2 = self.pts[i], self.pts[i+1]
            xx, yy = line(int(p1[0]), int(p1[1]), int(p2[0]), int(p2[1]))
            xx = xx[xx < self.window.mx]
            yy = yy[yy < self.window.my]
            xxs.extend(xx)
            yys.extend(yy)

        return np.array(xxs, dtype=int), np.array(yys, dtype=int)

    def makeMenu(self):
        ROI_Wrapper.makeMenu(self)
        self.menu.addAction(self.removeLinkAction)
        self.menu.addAction(self.setWidthAction)
        self.menu.addAction(self.kymographAct)
        self.kymographAct.setEnabled(self.window.image.ndim > 2)

    def raiseContextMenu(self, ev):
        if np.any([len(i.rois)<2 for i in self.currentLine.getHandles()]):
            self.removeLinkAction.setText("Remove Link")
            self.removeLinkAction.setVisible(True)
        else:
            self.removeLinkAction.setVisible(False)
        
        ROI_Wrapper.raiseContextMenu(self, ev)

    def boundingRect(self):
        return QtCore.QRectF()

    def paint(self, p, *args):
        pass

    def setPen(self, pen):
        pen = QtGui.QPen(pen)
        pen.setWidth(0)
        self.pen = pen
        self.setCurrentPen(pen)

    def setCurrentPen(self, pen):
        pen = QtGui.QPen(pen)
        pen.setWidth(0)
        for l in self.lines:
            l.currentPen = pen
            l.update()

    def update_kymograph(self):
        tif=self.window.image
        if tif.ndim != 3:
            g.alert("Can only kymograph on 3D movies")
            return
        
        if self.width == 1:
            w, h = self.window.imageDimensions()
            r = QtCore.QRect(0, 0, w, h)
            xx, yy = self.getMask()
            mn = tif[:, xx, yy].T
        else:
            region = self.getArrayRegion(self.window.imageview.image, self.window.imageview.getImageItem(), (1, 2))
            mn = np.average(region, 2).T


        if self.kymograph is None:
            self.createKymograph(mn)
        else:
            self.kymograph.imageview.setImage(mn,autoLevels=False,autoRange=False)
            #self.kymograph.imageview.view.setAspectLocked(lock=True,ratio=mn.shape[1]/mn.shape[0])

    def setWidth(self, newWidth=None):
        s = True
        if newWidth == None:
            newWidth, s = QtWidgets.QInputDialog.getInt(None, "Enter a width value", 'Float Value', value = self.width)
        if not s or s == 0:
            return
        for l in self.lines:
            l.scale([1.0, newWidth/self.width], center=[0.5,0.5])
        self.width = newWidth
        self.sigRegionChangeFinished.emit(self)

    def createKymograph(self,mn):
        from .window import Window
        oldwindow=g.currentWindow
        name=oldwindow.name+' - Kymograph'
        self.kymograph=Window(mn,name,metadata=self.window.metadata)
        self.kymographproxy = pg.SignalProxy(self.sigRegionChanged, rateLimit=1, slot=self.update_kymograph) #This will only update 3 Hz
        self.sigRegionChanged.connect(self.update_kymograph)
        self.kymograph.closeSignal.connect(self.deleteKymograph)

    def deleteKymograph(self):
        self.kymographproxy.disconnect()
        self.kymograph.closeSignal.disconnect(self.deleteKymograph)
        self.kymograph=None

def makeROI(kind, pts, window=None, **kargs):
    if window is None:
        window=g.currentWindow

    if kind=='freehand':
        roi=ROI(window, pts, **kargs)
    elif kind=='rectangle':
        if len(pts) > 2:
            size = np.ptp(pts,0)
            top_left = np.min(pts,0)
        else:
            size = pts[1]
            top_left = pts[0]
        roi=ROI_rectangle(window, top_left, size, **kargs)
    elif kind=='line':
        roi=ROI_line(window, (pts), **kargs)
    elif kind == 'rect_line':
        roi = ROI_rect_line(window, pts, **kargs)
    else:
        g.alert("ERROR: THIS TYPE OF ROI COULD NOT BE FOUND: {}".format(kind))
        return None

    pen = QtGui.QPen(QtGui.QColor(g.settings['roi_color']) if g.settings['roi_color'] != 'random' else random_color())
    pen.setWidth(0)

    roi.drawFinished()
    roi.setPen(pen)
    return roi

def load_rois(filename=None):
    if filename is None:
        filetypes = '*.txt'
        prompt = 'Load ROIs from file'
        filename = save_file_gui(prompt, filetypes=filetypes)
        if filename is None:
            return None
    text = open(filename, 'r').read()
    rois = []
    kind = None
    pts = None
    for text_line in text.split('\n'):
        if kind is None:
            kind=text_line
            pts=[]
        elif text_line == '':
            roi = makeROI(kind,pts)
            rois.append(roi)
            kind = None
            pts = None
        else:
            pts.append(tuple(int(float(i)) for i in text_line.split()))

    return rois
