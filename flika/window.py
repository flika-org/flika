# -*- coding: utf-8 -*-
from qtpy import QtCore, QtGui, QtWidgets
import pyqtgraph as pg
import os, time
import numpy as np
from .tracefig import TraceFig
from . import global_vars as g
from .roi import *
from .utils.misc import save_file_gui
pg.setConfigOptions(useWeave=False)


class Window(QtWidgets.QWidget):
    """
    Window objects are the central objects in flika. Almost all functions in the 
    :mod:`process <flika.process>` module are performed on Window objects and 
    output Window objects. 

    """
    closeSignal = QtCore.Signal()
    keyPressSignal = QtCore.Signal(QtCore.QEvent)
    sigTimeChanged = QtCore.Signal(int)
    gainedFocusSignal = QtCore.Signal()
    lostFocusSignal = QtCore.Signal()

    def __init__(self, tif, name='flika', filename='', commands=[], metadata=dict()):
        QtWidgets.QWidget.__init__(self)
        self.commands = commands #commands is a list of the commands used to create this window, starting with loading the file
        self.metadata = metadata
        if 'is_rgb' not in metadata.keys():
            metadata['is_rgb'] = tif.ndim == 4
        if g.currentWindow is None:
            if 'window_settings' not in g.settings:
                g.settings['window_settings'] = dict()
            if 'coords' in g.settings['window_settings']:
                geometry = QtCore.QRect(*g.settings['window_settings']['coords'])
            else:
                width = 684
                height = 585
                nwindows = len(g.windows)
                x = 10 + 10 * nwindows
                y = 300 + 10 * nwindows
                geometry = QtCore.QRect(x, y, width, height)
                g.settings['window_settings']['coords'] = geometry.getRect()
        else:
            geometry = g.currentWindow.geometry()
            geometry.setX(geometry.x()+10)
            geometry.setY(geometry.y() + 10)

        self.resizeEvent = self.onResize
        self.moveEvent = self.onMove
        self.name = name
        self.filename = filename
        self.setAsCurrentWindow()
        self.setWindowTitle(name)
        self.imageview = pg.ImageView(self)
        self.imageview.setMouseTracking(True)
        self.imageview.installEventFilter(self)
        self.imageview.ui.menuBtn.setParent(None)
        self.imageview.ui.roiBtn.setParent(None) # gets rid of 'roi' button that comes with ImageView
        self.imageview.ui.normLUTbtn = QtWidgets.QPushButton(self.imageview.ui.layoutWidget)
        self.imageview.ui.normLUTbtn.setObjectName("LUT norm")
        self.imageview.ui.normLUTbtn.setText("LUT norm")
        self.imageview.ui.gridLayout.addWidget(self.imageview.ui.normLUTbtn, 1, 1, 1, 1)
        self.imageview.ui.normLUTbtn.pressed.connect(self.normLUT)
        rp = self.imageview.ui.roiPlot.getPlotItem()
        self.linkMenu = QtWidgets.QMenu("Link frame")
        rp.ctrlMenu = self.linkMenu
        self.linkMenu.aboutToShow.connect(self.make_link_menu)

        if np.any(np.isinf(tif)):
            tif[np.isinf(tif)] = 0
            g.alert('Some array values were inf. Setting those values to 0')

        self.imageview.setImage(tif)
        self.image = tif
        self.volume = None  # When attaching a 4D array to this Window object, where self.image is a 3D slice of this volume, attach it here. This will remain None for all 3D Windows
        self.nDims = len(np.shape(self.image))
        dimensions_txt = ""
        mx = 0
        my = 0
        mt = 0
        if self.nDims == 3:
            if metadata['is_rgb']:
                mx,my,mc = tif.shape
                mt = 1
                dimensions_txt = "{}x{} pixels; {} colors; ".format(mx,my,mc)
            else:
                mt, mx, my = tif.shape
                dimensions_txt = "{} frames; {}x{} pixels; ".format(mt, mx, my)
        elif self.nDims == 4:
            mt,mx,my,mc = tif.shape
            dimensions_txt = "{} frames; {}x{} pixels; {} colors; ".format(mt, mx, my, mc)
        elif self.nDims == 2:
            mt = 1
            mx, my = tif.shape
            dimensions_txt = "{}x{} pixels; ".format(mx, my)
        self.mx = mx
        self.my = my
        self.mt = mt
        dtype = self.image.dtype
        dimensions_txt += 'dtype=' + str(dtype)
        if 'timestamps' in self.metadata:
            ts = self.metadata['timestamps']
            self.framerate = (ts[-1] - ts[0]) / len(ts)
            dimensions_txt += '; {:.4f} {}/frame'.format(self.framerate, self.metadata['timestamp_units'])
        self.top_left_label = pg.LabelItem(dimensions_txt, justify='right')
        self.imageview.ui.graphicsView.addItem(self.top_left_label)
        self.imageview.timeLine.sigPositionChanged.connect(self.updateindex)
        self.currentIndex = self.imageview.currentIndex
        self.normLUT()
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addWidget(self.imageview)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setGeometry(geometry)
        self.imageview.scene.sigMouseMoved.connect(self.mouseMoved)
        self.imageview.view.mouseDragEvent = self.mouseDragEvent
        self.imageview.view.mouseClickEvent = self.mouseClickEvent
        self.rois = []
        self.currentROI = None
        self.creatingROI = False
        pointSize = g.settings['point_size']
        pointColor = QtGui.QColor(g.settings['point_color'])
        self.scatterPlot = pg.ScatterPlotItem(size=pointSize, pen=pg.mkPen([0, 0, 0, 255]), brush=pg.mkBrush(*pointColor.getRgb()))  #this is the plot that all the red points will be drawn on
        self.scatterPoints = [[] for _ in np.arange(mt)]
        self.scatterPlot.sigClicked.connect(self.clickedScatter)
        self.imageview.addItem(self.scatterPlot)
        self.pasteAct = QtWidgets.QAction("&Paste", self, triggered=self.paste)
        if g.settings['show_windows']:
            self.show()
            QtWidgets.qApp.processEvents()
        self.sigTimeChanged.connect(self.showFrame)
        if self not in g.windows:
            g.windows.append(self)
        self.closed=False

        from .process.measure import measure
        self.measure = measure
        def clicked(evt):
            self.measure.pointclicked(evt, window=self)
        self.imageview.scene.sigMouseClicked.connect(clicked)
        self.linkedWindows = set()
        self.makeMenu()

    def onResize(self, event):
        g.settings['window_settings']['coords'] = self.geometry().getRect()

    def onMove(self, event):
        g.settings['window_settings']['coords'] = self.geometry().getRect()

    def save(self, filename):
        from .process.file_ import save_file
        old_curr_win = g.currentWindow
        self.setAsCurrentWindow()
        save_file(filename)
        old_curr_win.setAsCurrentWindow()

    def normLUT(self):
        if self.nDims ==2:
            # if the image is binary (either all 0s or 0s and 1s)
            if np.min(self.image) == 0 and (np.max(self.image) == 0 or np.max(self.image) == 1):
                self.imageview.setLevels(-.01, 1.01)  # set levels from slightly below 0 to 1
        if self.nDims == 3 and not self.metadata['is_rgb']:
            if np.all(self.image[self.currentIndex] == 0):  # if the current frame is all zeros
                r = (np.min(self.image), np.max(self.image))  # set the levels to be just above and below the min and max of the entire tif
                r = (r[0] - (r[1] - r[0]) / 100, r[1] + (r[1] - r[0]) / 100)
                self.imageview.setLevels(r[0], r[1])
            else:
                r = (np.min(self.image[self.currentIndex]),
                     np.max(self.image[self.currentIndex]))  # set the levels to be just above and below the min and max of the first frame
                r = (r[0] - (r[1] - r[0]) / 100, r[1] + (r[1] - r[0]) / 100)
                self.imageview.setLevels(r[0], r[1])
        elif self.nDims == 4 and not self.metadata['is_rgb']:
            if np.min(self.image) == 0 and (np.max(self.image) == 0 or np.max(self.image) == 1):  # if the image is binary (either all 0s or 0s and 1s)
                self.imageview.setLevels(-.01, 1.01)  # set levels from slightly below 0 to 1
    
    def link(self, win):
        if win not in self.linkedWindows:
            self.sigTimeChanged.connect(win.imageview.setCurrentIndex)
            self.linkedWindows.add(win)
            win.link(self)

    def unlink(self, win):
        if win in self.linkedWindows:
            self.linkedWindows.remove(win)
            self.sigTimeChanged.disconnect(win.imageview.setCurrentIndex)
            win.unlink(self)

    def link_toggled(self, win):
        return lambda b: self.link(win) if b else self.unlink(win)

    def make_link_menu(self):
        self.linkMenu.clear()
        for win in g.windows:
            if win == self or not win.isVisible():
                continue
            win_action = QtWidgets.QAction("%s" % win.name, self.linkMenu, checkable=True)
            win_action.setChecked(win in self.linkedWindows)
            win_action.toggled.connect(self.link_toggled(win))
            self.linkMenu.addAction(win_action)
        
    def updateindex(self):
        if self.mt == 1:
            t = 0
        else:
            (idx, t) = self.imageview.timeIndex(self.imageview.timeLine)
            t = int(np.floor(t))
        if 0 <= t < self.mt:
            self.currentIndex = t
            if not g.settings['show_all_points']:
                pointSizes = [pt[3] for pt in self.scatterPoints[t]]
                brushes = [pg.mkBrush(*pt[2].getRgb()) for pt in self.scatterPoints[t]]
                self.scatterPlot.setPoints(pos=self.scatterPoints[t], size=pointSizes, brush=brushes)
            self.sigTimeChanged.emit(t)

    def setIndex(self,index):
        if hasattr(self, 'image') and self.image.ndim > 2 and 0 <= index < len(self.image):
            self.imageview.setCurrentIndex(index)

    def showFrame(self,index):
        if index>=0 and index<self.mt:
            msg = 'frame {}'.format(index)
            if 'timestamps' in self.metadata and self.metadata['timestamp_units']=='ms':
                ttime = self.metadata['timestamps'][index]
                if ttime < 1*1000:
                    msg += '; {:.4f} ms'.format(ttime)
                elif ttime < 60*1000:
                    seconds = ttime / 1000
                    msg += '; {:.4f} s'.format(seconds)
                elif ttime < 3600*1000:
                    minutes = int(np.floor(ttime / (60*1000)))
                    seconds = (ttime/1000) % 60
                    msg += '; {} m {:.4f} s'.format(minutes, seconds)
                else:
                    seconds = ttime/1000
                    hours = int(np.floor(seconds / 3600))
                    mminutes = seconds - hours * 3600
                    minutes = int(np.floor(mminutes / 60))
                    seconds = mminutes - minutes * 60
                    '; {} h {} m {:.4f} s'.format(hours, minutes, seconds)
            g.m.statusBar().showMessage(msg)

    def setName(self,name):
        name=str(name)
        self.name=name
        self.setWindowTitle(name)
        
    def reset(self):
        if not self.closed:
            currentIndex = int(self.currentIndex)
            self.imageview.setImage(self.image, autoLevels=True) #I had autoLevels=False before.  I changed it to adjust after boolean previews.
            if self.imageview.axes['t'] is not None:
                self.imageview.setCurrentIndex(currentIndex)
            g.m.statusBar().showMessage('')

    def closeEvent(self, event):
        if self.closed:
            print('Attempt to close window {} that was already closed'.format(self))
            event.accept()
        else:
            self.closeSignal.emit()
            for win in list(self.linkedWindows):
                self.unlink(win)
            if hasattr(self,'image'):
                del self.image
            self.imageview.setImage(np.zeros((2,2))) #clear the memory
            self.imageview.close()
            del self.imageview
            if g.currentWindow==self:
                g.currentWindow=None
            if self in g.windows:
                g.windows.remove(self)
            self.closed=True
            event.accept() # let the window close

    def imageArray(self):
        '''
        returns image as a 3d array, correcting for color or 2d image
        '''
        tif=self.image
        nDims=len(tif.shape)
        if nDims==4: #if this is an RGB image stack  #[t, x, y, colors]
            tif=np.mean(tif,3)
            mx,my=tif[0,:,:].shape
        elif nDims==3:
            if self.metadata['is_rgb']:  # [x, y, colors]
                tif=np.mean(tif,2)
                mx,my=tif.shape
                tif=tif[np.newaxis]
            else: 
                mx,my=tif[0,:,:].shape
        elif nDims==2:
            mx,my=tif.shape
            tif=tif[np.newaxis]
        return tif

    def imageDimensions(self):
        nDims=self.image.shape
        if len(nDims)==4: #if this is an RGB image stack
            return nDims[1:3]
        elif len(nDims)==3:
            if self.metadata['is_rgb']:  # [x, y, colors]
                return nDims[:2]
            else:                               # [t, x, y]
                return nDims[1:]
        if len(nDims)==2: #if this is a static image
            return nDims
        return nDims

    def resizeEvent(self, event):
        event.accept()
        self.imageview.resize(self.size())

    def paste(self):
        ''' This function pastes an ROI from one window into another.
        The ROIs will be linked so that when you translate one of them, the other one also moves'''
        def pasteROI(roi):
            if roi in self.rois:
                return None
            self.currentROI=makeROI(roi.kind,roi.pts,self)
            if roi in roi.window.rois:
                self.currentROI.link(roi)
            return self.currentROI

        if type(g.clipboard) == list:
            rois = []
            for roi in g.clipboard:
                rois.append(pasteROI(roi))
            return rois
        else:
            return pasteROI(g.clipboard)
        
    def mousePressEvent(self,ev):
        ev.accept()
        self.setAsCurrentWindow()

    def setAsCurrentWindow(self):
        if g.currentWindow is not None:
            g.currentWindow.setStyleSheet("border:1px solid rgb(0, 0, 0); ")
            g.currentWindow.lostFocusSignal.emit()
        g.currentWindow=self
        g.m.currentWindow = g.currentWindow
        g.m.setWindowTitle("flika - {}".format(self.name))
        self.setStyleSheet("border:1px solid rgb(0, 255, 0); ")
        g.m.setCurrentWindowSignal.sig.emit()
        self.gainedFocusSignal.emit()
    
    def clickedScatter(self, plot, points):
        p = points[0]
        x, y = p.pos()

        if g.settings['show_all_points']:
            pts = []
            for t in np.arange(self.mt):
                self.scatterPoints[t] = [p for p in self.scatterPoints[t] if not (x == p[0] and y == p[1])]
                pts.extend(self.scatterPoints[t])
            pointSizes = [pt[3] for pt in pts]
            brushes = [pg.mkBrush(*pt[2].getRgb()) for pt in pts]
            self.scatterPlot.setPoints(pos=pts, size=pointSizes, brush=brushes)
        else:
            t = self.currentIndex
            self.scatterPoints[t] = [p for p in self.scatterPoints[t] if not (x == p[0] and y == p[1])]
            pointSizes = [pt[3] for pt in self.scatterPoints[t]]
            brushes = [pg.mkBrush(*pt[2].getRgb()) for pt in self.scatterPoints[t]]
            self.scatterPlot.setPoints(pos=self.scatterPoints[t], size=pointSizes, brush=brushes)

    def getScatterPts(self):
        p_out=[]
        p_in=self.scatterPoints
        for t in np.arange(len(p_in)):
            for p in p_in[t]:
                p_out.append(np.array([t,p[0],p[1]]))
        p_out=np.array(p_out)
        return p_out
        
    def makeMenu(self):
        self.menu = QtWidgets.QMenu(self)

        def updateMenu():
            from .roi import ROI_Wrapper
            pasteAct.setEnabled(isinstance(g.clipboard, (list, ROI_Wrapper)))

        pasteAct = QtWidgets.QAction("&Paste", self, triggered=self.paste)
        plotAllAct = QtWidgets.QAction('&Plot All ROIs', self.menu, triggered=self.plotAllROIs )
        copyAll = QtWidgets.QAction("Copy All ROIs", self.menu, triggered = lambda a: setattr(g, 'clipboard', self.rois))
        removeAll = QtWidgets.QAction("Remove All ROIs", self.menu, triggered = self.removeAllROIs)
        saveAll = QtWidgets.QAction("&Save All ROIs",self, triggered=self.exportROIs)

        self.menu.addAction(pasteAct)
        self.menu.addAction(plotAllAct)
        self.menu.addAction(copyAll)
        self.menu.addAction(saveAll)
        self.menu.addAction(removeAll)
        self.menu.aboutToShow.connect(updateMenu)

    def plotAllROIs(self):
        for roi in self.rois:
            if roi.traceWindow == None:
                roi.plot()

    def removeAllROIs(self):
        for roi in self.rois[:]:
            roi.delete()

    def addPoint(self, p=None):
        if p is None:
            p = [self.currentIndex, self.x, self.y]
        elif len(p) != 3:
            raise Exception("addPoint takes a 3-tuple (t, x, y) as argument")

        t, x, y = p

        pointSize=g.m.settings['point_size']
        pointColor = QtGui.QColor(g.settings['point_color'])
        position=[x, y, pointColor, pointSize]
        self.scatterPoints[t].append(position)
        self.scatterPlot.addPoints(pos=[[x, y]], size=pointSize, brush=pg.mkBrush(*pointColor.getRgb()))

    def mouseClickEvent(self,ev):
        self.EEEE=ev
        if self.x is not None and self.y is not None and ev.button()==2 and not self.creatingROI:
            mm=g.settings['mousemode']
            if mm=='point':
                self.addPoint()
            elif mm == 'rectangle' and g.settings['default_roi_on_click']:
                    self.currentROI = ROI_Drawing(self, self.x - g.settings['rect_width']/2, self.y - g.settings['rect_height']/2, mm)
                    self.currentROI.extend(self.x + g.settings['rect_width']/2, self.y + g.settings['rect_height']/2)
                    self.currentROI.drawFinished()
            elif mm == 'freehand' and g.settings['default_roi_on_click']:
                # Before using this script to get the outlines of cells from a raw movie of fluorescence, you need to do some processing.
                # Get a good image of cells by averaging the movie using the zproject() function inside flika.
                # Then threshold the image and use a combination of binary dilation and binary erosion to clean it up (all functions inside flika)
                if not (np.all(self.image >= 0) and np.all(self.image <= 1)):
                    return
                from skimage import measure
                from roi import makeROI

                thresholded_image = np.squeeze(self.image[self.currentIndex] if self.image.ndim == 3 else self.image)
                labelled=measure.label(thresholded_image)

                outline_coords = measure.find_contours(labelled == labelled[int(self.x)][int(self.y)], 0.5)
                outline_coords = sorted(outline_coords, key=lambda a: -len(a))[0]
                new_roi = makeROI("freehand", outline_coords)
            else:
                self.menu.exec_(ev.screenPos().toQPoint())
        elif self.creatingROI:
            self.currentROI.cancel()
            self.creatingROI = None

    def exportROIs(self, filename=None):
        if not isinstance(filename, str):
            if filename is not None and os.path.isfile(filename):
                filename = os.path.splitext(g.settings['filename'])[0]
                filename = save_file_gui('Save ROI', filename, '*.txt')
            else:
                filename = save_file_gui('Save ROI', '', '*.txt')

        if filename != '' and isinstance(filename, str):
            reprs = [roi.str() for roi in self.rois]
            reprs = '\n'.join(reprs)
            open(filename, 'w').write(reprs)
        else:
            g.m.statusBar().showMessage('No File Selected')
    
    def keyPressEvent(self, ev):
        if ev.key() == QtCore.Qt.Key_Delete:
            i = 0
            while i < len(self.rois):
                if self.rois[i].mouseHovering:
                    self.rois[i].delete()
                else:
                    i += 1
        self.keyPressSignal.emit(ev)
        
    def mouseMoved(self,point):
        point=self.imageview.getImageItem().mapFromScene(point)
        self.point = point
        self.x = point.x()
        self.y = point.y()
        image=self.imageview.getImageItem().image
        if self.x < 0 or self.y < 0 or self.x >= image.shape[0] or self.y>=image.shape[1]:
            pass# if we are outside the image
        else:
            z=self.imageview.currentIndex
            value=image[int(self.x),int(self.y)]
            g.m.statusBar().showMessage('x={}, y={}, z={}, value={}'.format(int(self.x),int(self.y),z,value))
        

    def mouseDragEvent(self, ev):
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        if modifiers == QtCore.Qt.ShiftModifier:
            pass #This is how I detect that the shift key is held down.
        if ev.button() == QtCore.Qt.LeftButton:
            ev.accept()
            difference=self.imageview.getImageItem().mapFromScene(ev.lastScenePos())-self.imageview.getImageItem().mapFromScene(ev.scenePos())
            self.imageview.view.translateBy(difference)
        if ev.button() == QtCore.Qt.RightButton:
            ev.accept()
            mm = g.settings['mousemode']
            if mm in ('freehand', 'line', 'rectangle', 'rect_line'):
                if ev.isStart():
                    self.ev = ev
                    pt = self.imageview.getImageItem().mapFromScene(ev.buttonDownScenePos())
                    self.x = pt.x() # this sets x and y to the button down position, not the current position
                    self.y = pt.y()
                    self.creatingROI = True
                    self.currentROI = ROI_Drawing(self,self.x,self.y, mm)
                if ev.isFinish():
                    if self.creatingROI:   
                        if ev._buttons | QtCore.Qt.RightButton != ev._buttons:
                            self.currentROI = self.currentROI.drawFinished()
                            self.creatingROI = False
                        else:
                            self.currentROI.cancel()
                            self.creatingROI = False
                    else:
                        for r in self.currentROIs:
                            r.finish_translate()
                else: # if we are in the middle of the drag between starting and finishing
                    if self.creatingROI:
                        self.currentROI.extend(self.x, self.y)
    def updateTimeStampLabel(self,frame):
        label = self.timeStampLabel
        if self.framerate == 0:
            label.setHtml("<span style='font-size: 12pt;color:white;background-color:None;'>Frame rate is 0 Hz</span>" )
            return False
        ttime = frame/self.framerate
        
        if ttime<1:
            ttime = ttime*1000
            label.setHtml("<span style='font-size: 12pt;color:white;background-color:None;'>{:.0f} ms</span>".format(ttime))
        elif ttime<60:
            label.setHtml("<span style='font-size: 12pt;color:white;background-color:None;'>{:.3f} s</span>".format(ttime))
        elif ttime<3600:
            minutes=int(np.floor(ttime/60))
            seconds=ttime % 60
            label.setHtml("<span style='font-size: 12pt;color:white;background-color:None;'>{}m {:.3f} s</span>".format(minutes,seconds))
        else:
            hours = int(np.floor(ttime/3600))
            mminutes = ttime-hours*3600
            minutes = int(np.floor(mminutes/60))
            seconds = mminutes-minutes*60
            label.setHtml("<span style='font-size: 12pt;color:white;background-color:None;'>{}h {}m {:.3f} s</span>".format(hours,minutes,seconds))
