
from qtpy import QtGui, QtCore, QtWidgets
import flika.global_vars as g
from flika.utils import random_color, getSaveFileName
import pyqtgraph as pg
from skimage.draw import polygon, line
import numpy as np
from flika.tracefig import roiPlot
import os
from scipy.ndimage.interpolation import rotate


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
        g.m.currentWindow.imageview.removeItem(self)
        g.m.currentWindow.currentROI = None

    def extendRectLine(self):
        for roi in self.window.rois:
            if isinstance(roi, ROI_rect_line):
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
        getTrace(bounds=None)
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
        self.sigRegionChanged.connect(lambda a: print("CHANGE"))
        self.sigRegionChangeFinished.connect(lambda a: print("CHANGE FINISH"))
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
        if self.window.image.ndim == 2:
            g.alert("Cannot get the trace of an ROI on a 2D image.")
            return
        s1, s2 = self.getMask()
        if np.size(s1) == 0 or np.size(s2) == 0:
            trace = np.zeros(self.window.image.shape[0])
        else:
            trace = self.window.image[:, s1, s2]
            while trace.ndim > 1:
                trace = np.average(trace, 1)

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
        self.traceWindow.indexChanged.connect(self.window.setIndex)
        self.plotSignal.emit()
        return self.traceWindow

    def changeColor(self):
        self.colorDialog.open()
        
    def colorSelected(self, color):
        if color.isValid():
            self.setPen(QtGui.QColor(color.name()))
            self.sigRegionChangeFinished.emit(self)
            self.color = color

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
        plotAct = QtWidgets.QAction("&Plot", self, triggered=lambda : self.plot() if plotAct.text() == "&Plot" else self.unplot())
        colorAct = QtWidgets.QAction("&Change Color",self,triggered=self.changeColor)
        copyAct = QtWidgets.QAction("&Copy", self, triggered=self.copy)
        remAct = QtWidgets.QAction("&Delete", self, triggered=self.delete)
        self.menu = QtWidgets.QMenu("ROI Menu")

        def updateMenu():
            plotAct.setEnabled(self.window.image.ndim > 2)
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
        from flika.window import Window
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
        self.INITIAL_ARGS.update(kargs)
        pg.LineSegmentROI.__init__(self, positions=positions, **self.INITIAL_ARGS)
        self.kymograph = None
        self.kymographAct = QtWidgets.QAction("&Kymograph", self, triggered=self.update_kymograph)
        ROI_Wrapper.__init__(self, window, positions)

    def resetSignals(self):
        ROI_Wrapper.resetSignals(self)
        self.sigRegionChanged.connect(self.snapPoints)

    def snapPoints(self):
        fix = False
        self.blockSignals(True)
        for handle in self.handles:
            pos = handle['pos']
            pos_round = pg.Point(round(pos.x()), round(pos.y()))
            if not (pos == pos_round):
                handle['item'].setPos(pos_round)
                handle['pos'] = pos_round
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

    def getMask(self):
        x=np.array([p[0] for p in self.pts], dtype=int)
        y=np.array([p[1] for p in self.pts], dtype=int)
        xx, yy = line(x[0],y[0],x[1],y[1])
        xx = xx[xx < self.window.imageview.getImageItem().image.shape[0]]
        yy = yy[yy < self.window.imageview.getImageItem().image.shape[1]]
        return xx, yy

    def getPoints(self):
        return np.array([handle['pos'] + self.state['pos'] for handle in self.handles])

    def makeMenu(self):
        ROI_Wrapper.makeMenu(self)
        self.menu.addAction(self.kymographAct)

    def update_kymograph(self):
        tif=self.window.image
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
        from flika.window import Window
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
        self.INITIAL_ARGS.update(kargs)
        pos = np.array(pos, dtype=int)
        size = np.array(size, dtype=int)

        pg.ROI.__init__(self, pos, size, **self.INITIAL_ARGS)
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
        ii = self.window.imageview.getImageItem()
        x, y = self.state['pos']
        w, h = self.state['size']

        mx, my = ii.image.shape
        xmin = max(x, 0)
        ymin = max(y, 0)
        xmax = min(x+w, mx)
        ymax = min(y+h, my)

        return np.meshgrid(np.arange(xmin, xmax, dtype=int), np.arange(ymin, ymax, dtype=int))

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
        from flika.window import Window
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
            
        return Window(newtif,self.window.name+' Cropped',metadata=self.window.metadata)

class ROI(ROI_Wrapper, pg.PolyLineROI):
    kind = 'freehand'
    plotSignal = QtCore.Signal()
    def __init__(self, window, pts, **kargs):
        self.INITIAL_ARGS.update(kargs)
        self.INITIAL_ARGS['closed'] = True
        pg.PolyLineROI.__init__(self, pts, **self.INITIAL_ARGS)
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


        pos = np.round(pos) 
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

class ROI_rect_line(ROI_Wrapper, pg.MultiRectROI):
    kind = 'rect_line'
    plotSignal = QtCore.Signal()
    def __init__(self, window, pts, width=1, **kargs):
        self.INITIAL_ARGS.update(kargs)
        pg.MultiRectROI.__init__(self, points=pts, width=width, **self.INITIAL_ARGS)
        self.kymographAct = QtWidgets.QAction("&Kymograph", self, triggered=self.update_kymograph)
        ROI_Wrapper.__init__(self, window, pts)
        self.maskProxy = pg.SignalProxy(self.sigRegionChanged, rateLimit=5, slot=self.onRegionChange) #This will only update 3 Hz
        self.kymograph = None
        self.extending = False
        self.extendHandle = None
        w, h = self.lines[0].size()
        self.lines[0].scale([1.0, width/5.0], center=[0.5,0.5], finish=False)
        self.currentLine = None

    def hoverEvent(self, l, ev):
        self.currentLine = l
        if ev.enter:
            pen = QtGui.QPen(HOVER_COLOR)
            pen.setWidth(0)
            self.setCurrentPen(pen)
        elif ev.exit:
            self.setCurrentPen(l.pen)

    def drawFinished(self):
        ROI_Wrapper.drawFinished(self)
        self.lines[0].removeHandle(2)

    def draw_from_points(self, pts, finish=False):
        self.blockSignals(True)
        self.lines[0].movePoint(self.lines[0].handles[0]['item'], pts[0], finish=False)
        for i in range(1, len(self.lines)):
            self.lines[i-1].movePoint(self.lines[i-1].handles[1]['item'], pts[i], finish=False)
            self.lines[i].movePoint(self.lines[i].handles[0]['item'], pts[i], finish=False)
        self.lines[-1].movePoint(self.lines[-1].handles[-1]['item'], pts[-1])
        self.blockSignals(False)
        self.pts = pts

    def makeMenu(self):
        ROI_Wrapper.makeMenu(self)
        removeLinkAction = QtWidgets.QAction('Remove Link', self, triggered=self.removeLink)
        setWidthAction = QtWidgets.QAction("Set Width", self, triggered=lambda: self.setWidth())
        self.menu.addAction(removeLinkAction)
        self.menu.addAction(setWidthAction)
        self.menu.addAction(self.kymographAct)

    def setPen(self, pen):
        self.pen = pen
        for l in self.lines:
            l.setPen(pen)

    def getMask(self):
        region = self.getArrayRegion(self.window.imageview.getImageItem().image, self.window.imageview.getImageItem(), (0, 1))
        mask = self.renderShapeMask(region.shape[0], region.shape[1])
        return np.where(mask)

    def getRegion(self):
        return self.getArrayRegion(self.window.imageview.image, self.window.imageview.getImageItem(), (1, 2))

    def removeLink(self):
        ind = self.lines.index(self.currentLine)
        if ind == 0:
            self.delete()
            return
        for i in range(len(self.lines)-1, ind-1, -1):
            self.removeSegment(i)
        self.sigRegionChangeFinished.emit(self)

    def setWidth(self, newWidth=None):
        s = True
        if newWidth == None:
            newWidth, s = QtWidgets.QInputDialog.getInt(None, "Enter a width value", 'Float Value', value = self.width)
        if not s:
            return
        self.lines[0].scale([1.0, newWidth/self.width], center=[0.5,0.5])
        self.width = newWidth
        self.sigRegionChangeFinished.emit(self)

    def extend(self, x, y):
        if not self.extending:
            self.extending = True
            self.addSegment(pg.Point(int(x), int(y)), connectTo=self.lines[-1].handles[1]['item'])
        else:
            self.lines[-1].handles[-1]['item'].movePoint(self.window.imageview.getImageItem().mapToScene(pg.Point(x, y)))
        self.sigRegionChanged.emit(self)

    def extendFinished(self):
        self.extending = False
        self.extendHandle = None
        self.sigRegionChangeFinished.emit(self)

    def update_kymograph(self):
        tif=self.window.image
        
        if self.width == 1:
            w, h = self.window.imageDimensions()
            r = QtCore.QRect(0, 0, w, h)
            xx, yy = self.getMask()
            mn = tif[:, xx, yy].T
        else:
            kyms = []
            for i in range(len(self.pts)-1):
                pts = self.pts[i:i+2]
                x, y = np.min(pts, 0)
                x, y = int(x), int(y)
                x2, y2 = np.max(pts, 0)
                x2, y2 = int(x2), int(y2)
                rect = rotate(tif[:, x-self.width:x2+self.width, y-self.width:y2+self.width], -self.lines[i].angle(), (2, 1), reshape=False)
                t, w, h = np.shape(rect)
                h = h // 2  - self.width // 2
                rect = rect[:, :, h:h+self.width]
                kyms.append(np.mean(rect, 2))
            mn = np.hstack(kyms).T

        if self.kymograph is None:
            self.createKymograph(mn)
        else:
            self.kymograph.imageview.setImage(mn,autoLevels=False,autoRange=False)
            #self.kymograph.imageview.view.setAspectLocked(lock=True,ratio=mn.shape[1]/mn.shape[0])


    def createKymograph(self,mn):
        from flika.window import Window
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

def load_rois(filename):
    text = open(filename, 'r').read()
    rois = []
    kind=None
    pts=None
    for text_line in text.split('\n'):
        if kind is None:
            kind=text_line
            pts=[]
        elif text_line=='':
            roi = makeROI(kind,pts)
            rois.append(roi)
            kind=None
            pts=None
        else:
            pts.append(tuple(int(float(i)) for i in text_line.split()))

    return rois
