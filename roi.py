from qtpy.QtWidgets import QAction, QMenu
from qtpy.QtGui import QColor
from qtpy.QtCore import Signal
import global_vars as g
import pyqtgraph as pg
from skimage.draw import polygon, line
import numpy as np
from tracefig import roiPlot
import os
import threading
from scipy.ndimage.interpolation import rotate
import process

SHOW_MASK = False

ROI_COLOR = QColor(255, 255, 0)
HOVER_COLOR = QColor(255, 0, 0)

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
            r = ROI(self.window, self.pts)
        elif self.type == 'rectangle':
            r = ROI_rectangle(self.window, self.state['pos'], self.state['size'])
        elif self.type == 'line':
            r = ROI_line(self.window, self.pts)
        elif self.type == 'rect_line':
            r = ROI_rect_line(self.window, self.pts)

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
        self.window.currentROI = self
        self.traceWindow = None  # To test if roi is plotted, check if traceWindow is None
        self.mask=None
        self.linkedROIs = set()
        self.sigRegionChanged.connect(self.onRegionChange)
        self.sigRegionChangeFinished.connect(self.finish_translate)
        if isinstance(self.pen, QColor):
            self.color = self.pen
        else:
            #self.pen.setWidth(2)
            self.color = self.pen.color()


    def finish_translate(self):
        pts=self.getPoints(round=True)
        for roi in self.linkedROIs:
            roi.draw_from_points(pts)
            roi.translate_done.emit()
        #self.draw_from_points(pts)
        self.translate_done.emit()

    def setMouseHover(self, hover):
        ## Inform the ROI that the mouse is(not) hovering over it
        if self.mouseHovering == hover:
            return
        self.mouseHovering = hover
        if hover:
            self.currentPen = pg.mkPen(HOVER_COLOR)
        else:
            self.currentPen = self.pen

        self.update()
        
    def onRegionChange(self):
        self.getMask()
        pts = self.pts
        for roi in self.linkedROIs:
            roi.blockSignals(True)
            roi.draw_from_points(pts)
            if isinstance(roi, ROI):
                roi.state['pos'] = self.state['pos']
            roi.blockSignals(False)
            if roi.traceWindow != None:
                roi.traceWindow.translated(roi)
            roi.getMask()
        self.translated.emit()

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
            self.translate_done.emit()
        self.color = color

    def save_gui(self):
        filename=g.settings['filename'].split('.')[0]
        if filename is not None and os.path.isfile(filename):
            filename= QFileDialog.getSaveFileName(g.m, 'Save ROI', filename, "Text Files (*.txt);;All Files (*.*)")
        else:
            filename= QFileDialog.getSaveFileName(g.m, 'Save ROI', '', "Text Files (*.txt);;All Files (*.*)")
        filename=str(filename)
        if filename != '':
            reprs = [roi.str() for roi in self.window.rois]
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
        if self.traceWindow != None:
            self.traceWindow.removeROI(self)
            self.traceWindow = None

    def copy(self):
        g.m.clipboard=self

    def link(self,roi):
        '''This function links this roi to another, so a translation of one will cause a translation of the other'''
        join = self.linkedROIs | roi.linkedROIs | {self, roi}
        self.linkedROIs = join - {self}
        roi.linkedROIs = join - {roi}

    def raiseContextMenu(self, ev):
        pos = ev.screenPos()
        self.plotAct.setText("&Plot" if self.traceWindow == None else "&Unplot")
        self.menu.popup(QPoint(pos.x(), pos.y()))
    
    def getMenu(self):
        self.plotAct = QAction("&Plot", self, triggered=lambda : self.plot() if self.plotAct.text() == "&Plot" else self.unplot())
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

    def getTrace(self, bounds=None, pts=None):
        tif = self.window.imageArray()
        t, w, h = np.shape(tif)
        pts_in = [[x, y] for x, y in self.mask if x >= 0 and y >= 0 and x < w and y < h]
        if len(pts_in) == 0 or len(self.mask) == 0:
            vals = np.zeros(t)
        else:
            xx, yy = np.transpose(pts_in)
            self.minn = np.min(self.mask, 0)
            vals = np.average(tif[:, xx, yy], 1)
            if vals[0] != np.average(tif[0, xx, yy]):
                if vals[0] - np.average(tif[0, xx, yy]) > 10**-10: # This number was chosen because it's really small, not for some clever computational reason
                    if tif.dtype == np.float16:  # There is probably a float 16 overflow going on.
                        vals = np.average(tif[:, xx, yy].astype(np.float), 1)
                    elif tif.dtype ==np.float32:
                        vals = np.average(tif[:, xx, yy].astype(np.float), 1)
                    else:
                        assert vals[0] == np.average(tif[0, xx, yy])  # Deal with this issue if it happens.
            if SHOW_MASK:
                img = np.zeros((w, h))
                img[xx, yy] = 1
                self.window.imageview.setImage(img, autoRange=False)
        
        if bounds:
            vals = vals[bounds[0]:bounds[1]]
        return vals

    def str(self):
        s = self.kind + '\n'
        for x, y in self.pts:
            s += '%d %d\n' % (x, y)
        return s


class ROI_line(ROI_Wrapper, pg.LineSegmentROI):
    kind = 'line'
    plotSignal = Signal()
    translated = Signal()
    translate_done = Signal()
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

    def getPoints(self, round=False):
        return self.pts

    def getMask(self):
        self.pts = [h['item'].pos() + self.pos() for h in self.handles]
        x=np.array([p[0] for p in self.pts], dtype=int)
        y=np.array([p[1] for p in self.pts], dtype=int)
        xx,yy=line(x[0],y[0],x[1],y[1])
        self.mask = np.transpose([xx, yy])
        self.minn = np.min(self.mask)

    def draw_from_points(self, pts):
        self.blockSignals(True)
        self.movePoint(self.handles[0]['item'], pts[0], finish=False)
        self.movePoint(self.handles[1]['item'], pts[1], finish=False)
        self.blockSignals(False)

    def update_kymograph(self):
        tif=self.window.image
        xx, yy = self.mask.T
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
        from window import Window
        oldwindow=g.m.currentWindow
        name=oldwindow.name+' - Kymograph'
        self.kymograph=Window(mn,name,metadata=self.window.metadata)
        
        self.translated.connect(self.update_kymograph)
        self.kymograph.closeSignal.connect(self.deleteKymograph)
        self.sigRemoveRequested.connect(self.deleteKymograph)

    def deleteKymograph(self):
        self.kymograph.closeSignal.disconnect(self.deleteKymograph)
        self.kymograph=None


class ROI_rect_line(ROI_Wrapper, pg.MultiRectROI):
    kind = 'rect_line'
    plotSignal = Signal()
    translated = Signal()
    translate_done = Signal()
    def __init__(self, window, pts, width=1, *args, **kargs):
        self.init_args.update(kargs)
        self.window = window
        self.width = width
        self.pts = pts
        pg.MultiRectROI.__init__(self, pts, width, *args, **self.init_args)
        self.blockSignals(True)
        self.kymographAct = QAction("&Kymograph", self, triggered=self.update_kymograph)
        ROI_Wrapper.__init__(self)
        self.maskProxy = pg.SignalProxy(self.sigRegionChanged, rateLimit=5, slot=self.onRegionChange) #This will only update 3 Hz
        self.kymograph = None
        self.extending = False
        self.extendHandle = None
        w, h = self.lines[0].size()
        self.lines[0].scale([1.0, width/5.0], center=[0.5,0.5], finish=False)
        self.width = width
        self.currentLine = None
        self.blockSignals(False)

    def drawFinished(self):
        ROI_Wrapper.drawFinished(self)
        self.lines[0].removeHandle(2)
    
    def draw_from_points(self, pts):
        self.blockSignals(True)
        self.lines[0].movePoint(self.lines[0].handles[0]['item'], pts[0], finish=False)
        for i in range(1, len(self.lines)):
            self.lines[i-1].movePoint(self.lines[i-1].handles[1]['item'], pts[i], finish=False)
            self.lines[i].movePoint(self.lines[i].handles[0]['item'], pts[i], finish=False)
        self.lines[-1].movePoint(self.lines[-1].handles[-1]['item'], pts[-1])
        self.blockSignals(False)
        
    def setCurrentPen(self, pen):
        for l in self.lines:
            l.currentPen = pen
            l.update()

    def hoverEvent(self, l, ev):
        self.currentLine = l
        if ev.enter:
            self.setCurrentPen(QPen(HOVER_COLOR))
        elif ev.exit:
            self.setCurrentPen(l.pen)

    def removeLink(self):
        ind = self.lines.index(self.currentLine)
        if ind == 0:
            self.delete()
            return
        for i in range(len(self.lines)-1, ind-1, -1):
            self.removeSegment(i)
        self.translate_done.emit()

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
        self.translate_done.emit()

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
        l.raiseContextMenu = self.raiseContextMenu
        l.getMenu = self.getMenu
        l.hoverEvent = lambda ev: self.hoverEvent(l, ev)
        def boundingRect():
            w = max(8, self.width)
            return QRectF(0, -w / 2, l.state['size'][0], w)
        def contains(pos):
            return l.boundingRect().contains(pos)
        l.boundingRect = boundingRect
        l.contains = contains

    def getPoints(self, round=False):
        return self.pts

    def getMask(self):
        self.pts = [pg.Point(self.window.imageview.getImageItem().mapFromScene(self.lines[0].getSceneHandlePositions(0)[1]))]
        for l in self.lines:
            self.pts.append(pg.Point(self.window.imageview.getImageItem().mapFromScene(l.getSceneHandlePositions(1)[1])))

        xx = []
        yy = []
        for i in range(1, len(self.pts)):
            p1, p2=[self.pts[i-1], self.pts[i]]
            xs,ys=line(*[int(a) for a in (p1.x(),p1.y(),p2.x(),p2.y())])
            xx.append(xs)
            yy.append(ys)
        xx = np.concatenate(xx)
        yy = np.concatenate(yy)

        self.mask = np.transpose([xx, yy])
        if self.mask.size != 0:
            self.minn = np.min(self.mask, 0)


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
        self.translated.emit()

    def extendFinished(self):
        self.extending = False
        self.extendHandle = None
        self.translate_done.emit()

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
        from window import Window
        if self.width == 1:
            w, h = self.window.imageDimensions()
            r = QRect(0, 0, w, h)
            xx, yy = np.transpose([p for p in self.mask if r.contains(p[0], p[1])])
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
        from window import Window
        oldwindow=g.m.currentWindow
        name=oldwindow.name+' - Kymograph'
        self.kymograph=Window(mn,name,metadata=self.window.metadata)
        self.kymographproxy = pg.SignalProxy(self.sigRegionChanged, rateLimit=1, slot=self.update_kymograph) #This will only update 3 Hz
        self.translated.connect(self.update_kymograph)
        self.kymograph.closeSignal.connect(self.deleteKymograph)

    def deleteKymograph(self):
        self.kymographproxy.disconnect()
        self.kymograph.closeSignal.disconnect(self.deleteKymograph)
        self.kymograph=None


class ROI_rectangle(ROI_Wrapper, pg.ROI):
    kind = 'rectangle'
    plotSignal = Signal()
    translated = Signal()
    translate_done = Signal()
    def __init__(self, window, pos, size=(1, 1), resizable=True, *args, **kargs):
        self.init_args.update(kargs)
        self.window = window
        pg.ROI.__init__(self, pos, size, *args, **self.init_args)
        if resizable:
            self.addScaleHandle([0, 1], [1, 0])
            self.addScaleHandle([1, 0], [0, 1])
            self.addScaleHandle([0, 0], [1, 1])
            self.addScaleHandle([1, 1], [0, 0])
        self.cropAction = QAction('&Crop', self, triggered=self.crop)
        ROI_Wrapper.__init__(self)

    def draw_from_points(self, pts):
        self.blockSignals(True)
        self.setPos(np.min(pts, 0), finish=False)
        if len(pts) == 2:
            self.setSize(pts[1], finish=False)
        elif len(pts) > 2:
            size = np.ptp(pts, 0)
            self.setSize(size, finish=False)
        self.blockSignals(False)

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

    def getPoints(self, round=False):
        handles = self.getHandles()
        if round:
            x, y = self.pos()
            offset = [np.round(x) - x, np.round(y) - y]
            if offset != [0, 0]:
                self.translate(offset, finish=False)
            handle_pos = [h.pos() for h in handles]
            w, h = np.round(np.ptp(handle_pos, 0))
            old_size = self.size()
            if w != old_size[0] or h != old_size[1]:
                self.setSize([w, h], finish=False)

        # go around the rectangle from top left handle, clockwise
        r = self.boundingRect()
        p1 = r.topLeft() + self.state['pos']
        p2 = r.bottomRight() + self.state['pos']
        x1, y1 = p1.x(), p1.y()
        x2, y2 = p2.x(), p2.y()
        self.pts = [pg.Point(x1, y1),
                    pg.Point(x2, y1),
                    pg.Point(x2, y2),
                    pg.Point(x1, y2)]
        return self.pts

    def getMask(self):
        w, h = self.window.imageDimensions()
        mask = np.zeros((w, h))
        
        x, y = np.array(self.state['pos'], dtype=int)
        w, h = np.array(self.state['size'], dtype=int)
        self.pts = self.getPoints()

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
            
    def contains(self, *pos, **kwargs):  # pyqtgraph ROI uses this function for mouse interaction. Set corrected=False to use
        corrected = kwargs.pop('corrected',True)
        if isinstance(pos[0], QPointF):
            pos = pos[0]
        elif len(pos) == 2:
            pos = QPointF(pos[0], pos[1])
        if not corrected:  # 'corrected' means relative to the top left corner of the ROI. 'Not corrected' means relative to the top left corner of the image.
            top_left = QPointF(self.pos())
            bottom_right = QPointF(*np.ptp(self.pts, 0)+np.array(self.pos()))
            return QRectF(top_left, bottom_right).contains(pos)
        else:
            return pg.ROI.contains(self, pos)


class ROI(ROI_Wrapper, pg.ROI):
    kind = 'freehand'
    plotSignal = Signal()
    translated = Signal()
    translate_done = Signal()
    def __init__(self, window, pts, *args, **kargs):
        self.init_args.update(kargs)
        self.window = window
        self.pts = [pg.Point(pt[0], pt[1]) for pt in pts]
        w, h = np.ptp(self.pts, 0)
        pg.ROI.__init__(self, (0, 0), (w, h), *args, **self.init_args)
        ROI_Wrapper.__init__(self)

    def draw_from_points(self, pts):
        self.blockSignals(True)
        self.setPos(pts[0], finish=False)
        self.pts = pts[1]
        self.blockSignals(False)

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

    def paint(self, p, *args):
        p.setPen(self.currentPen)
        for i in range(len(self.pts)):
            p.drawLine(self.pts[i], self.pts[i-1])

    def getPoints(self, round=False):
        return self.state['pos'], self.pts

    def getMask(self):
        if self.mask is not None:
            xx, yy = np.transpose(self._mask + self.state['pos'])

        else:
            self.minn = np.min(self.pts, 0)
            x, y = np.transpose(self.pts)
            mask=np.zeros(self.window.imageDimensions())
            
            xx,yy=polygon(x,y,shape=mask.shape)
            self._mask = np.transpose([xx, yy])
        
        self.mask = np.transpose([xx, yy]).astype(int)
        if len(self.mask) > 0:
            self.minn = np.min(self.mask, 0)


def makeROI(kind, pts, window=None, **kargs):
    if window is None:
        window=g.m.currentWindow

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
        roi=ROI_line(window, pos=(pts), **kargs)
    elif kind == 'rect_line':
        roi = ROI_rect_line(window, pts, **kargs)

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