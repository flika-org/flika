# -*- coding: utf-8 -*-
from .logger import logger
logger.debug("Started 'reading window.py'")
from qtpy import QtCore, QtGui, QtWidgets
import pyqtgraph as pg
import os, time
import numpy as np
from . import global_vars as g
from .roi import *
from .utils.misc import save_file_gui
from .utils.BaseProcess import WindowSelector, SliderLabel

pg.setConfigOptions(useWeave=False)


class Bg_im_dialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self)
        self.parent = parent
        self.setWindowTitle("Select background image")
        self.window_selector = WindowSelector()
        self.window_selector.valueChanged.connect(self.bg_win_changed)
        self.alpha_slider = SliderLabel(3)
        self.alpha_slider.setRange(0,1)
        self.alpha_slider.setValue(.5)
        self.alpha_slider.valueChanged.connect(self.alpha_changed)
        self.formlayout = QtWidgets.QFormLayout()
        self.formlayout.setLabelAlignment(QtCore.Qt.AlignRight)
        self.formlayout.addRow("Select window with background image", self.window_selector)
        self.formlayout.addRow("Set background opacity", self.alpha_slider)
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addLayout(self.formlayout)
        self.setLayout(self.layout)

    def alpha_changed(self, value):
        self.parent.bg_im.setOpacity(value)

    def bg_win_changed(self):
        if self.parent.bg_im is not None:
            self.parent.imageview.view.removeItem(self.parent.bg_im)
            self.bg_im = None
        self.parent.bg_im = pg.ImageItem(self.window_selector.window.imageview.imageItem.image)
        self.parent.bg_im.setOpacity(self.alpha_slider.value())
        self.parent.imageview.view.addItem(self.parent.bg_im)


    def closeEvent(self,ev):
        if self.parent.bg_im is not None:
            self.parent.imageview.view.removeItem(self.parent.bg_im)
            self.bg_im = None



class ImageView(pg.ImageView):
    def __init__(self, *args, **kargs):
        pg.ImageView.__init__(self, *args, **kargs)
        self.view.unregister()
        self.view.removeItem(self.roi)
        self.view.removeItem(self.normRoi)
        self.roi.setParent(None)
        self.normRoi.setParent(None)
        self.ui.menuBtn.setParent(None)
        self.ui.roiBtn.setParent(None) # gets rid of 'roi' button that comes with ImageView
        self.ui.normLUTbtn = QtWidgets.QPushButton(self.ui.layoutWidget)
        self.ui.normLUTbtn.setObjectName("LUT norm")
        self.ui.normLUTbtn.setText("LUT norm")
        self.ui.gridLayout.addWidget(self.ui.normLUTbtn, 1, 1, 1, 1)

        self.ui.bg_imbtn = QtWidgets.QPushButton(self.ui.layoutWidget)
        self.ui.bg_imbtn.setObjectName("bg im")
        self.ui.bg_imbtn.setText("bg im")
        self.ui.gridLayout.addWidget(self.ui.bg_imbtn, 1, 2, 1, 1)

        self.ui.roiPlot.setMaximumHeight(40)
        self.ui.roiPlot.getPlotItem().getViewBox().setMouseEnabled(False)
        self.ui.roiPlot.getPlotItem().hideButtons()

    def hasTimeAxis(self):
        return 't' in self.axes and not (self.axes['t'] is None or self.image.shape[self.axes['t']] == 1)

    def roiClicked(self):
        showRoiPlot = False
        if self.hasTimeAxis():
            showRoiPlot = True
            mn = self.tVals.min()
            mx = self.tVals.max() + .01
            self.ui.roiPlot.setXRange(mn, mx, padding=0.01)
            self.timeLine.show()
            self.timeLine.setBounds([mn, mx])
            self.ui.roiPlot.show()
            if not self.ui.roiBtn.isChecked():
                self.ui.splitter.setSizes([self.height()-35, 35])
        else:
            self.timeLine.hide()
            #self.ui.roiPlot.hide()
            
        self.ui.roiPlot.setVisible(showRoiPlot)

class Window(QtWidgets.QWidget):
    """
    Window objects are the central objects in flika. Almost all functions in the 
    :mod:`process <flika.process>` module are performed on Window objects and 
    output Window objects. 

    Args:
        tif (numpy.array): The image the window will store and display
        name (str): The name of the window.
        filename (str): The filename (including full path) of file this window's image orinated from.
        commands (list of str): a list of the commands used to create this window, starting with loading the file.
        metadata (dict): dict: a dictionary containing the original file's metadata.


    """
    closeSignal = QtCore.Signal()
    keyPressSignal = QtCore.Signal(QtCore.QEvent)
    sigTimeChanged = QtCore.Signal(int)
    gainedFocusSignal = QtCore.Signal()
    lostFocusSignal = QtCore.Signal()

    def __init__(self, tif, name='flika', filename='', commands=[], metadata=dict()):
        from .process.measure import measure
        QtWidgets.QWidget.__init__(self)
        self.name = name  #: str: The name of the window.
        self.filename = filename  #: str: The filename (including full path) of file this window's image orinated from.
        self.commands = commands  #: list of str: a list of the commands used to create this window, starting with loading the file.
        self.metadata = metadata  #: dict: a dictionary containing the original file's metadata.
        self.volume = None  # When attaching a 4D array to this Window object, where self.image is a 3D slice of this volume, attach it here. This will remain None for all 3D Windows
        self.scatterPlot = None
        self.closed = False  #: bool: True if the window has been closed, False otherwise.
        self.mx = 0  #: int: The number of pixels wide the image is in the x (left to right) dimension.
        self.my = 0  #: int: The number of pixels heigh the image is in the y (up to down) dimension.
        self.mt = 0  #: int: The number of frames in the image stack.
        self.framerate = None  #: float: The number of frames per second (Hz).
        self.image = tif
        self.dtype = tif.dtype  #: dtype: The datatype of the stored image, e.g. ``uint8``.
        self.top_left_label = None
        self.rois = []  #: list of ROIs: a list of all the :class:`ROIs <flika.roi.ROI_Base>` inside this window.
        self.currentROI = None  #: :class:`ROI <flika.roi.ROI_Base>`: When an ROI is clicked, it becomes the currentROI of that window and can be accessed via this variable.
        self.creatingROI = False
        self.imageview = None
        self.bg_im = None
        self.currentIndex = 0
        self.linkedWindows = set()
        self.measure = measure
        self.resizeEvent = self.onResize
        self.moveEvent = self.onMove
        self.pasteAct = QtWidgets.QAction("&Paste", self, triggered=self.paste)
        self.sigTimeChanged.connect(self.showFrame)
        self._check_for_infinities(tif)
        self._init_dimensions(tif)
        self._init_imageview(tif)
        self.setWindowTitle(name)
        self.normLUT(tif)
        self._init_scatterplot()
        self._init_menu()
        self._init_geometry()
        self.setAsCurrentWindow()

    def _init_geometry(self):
        assert g.win != self  # self.setAsCurrentWindow() must be called after this function
        if g.win is None:
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
            geometry = g.win.geometry()

        desktopGeom = QtWidgets.QDesktopWidget().screenGeometry()
        maxX = (desktopGeom.width() - geometry.width()) or 1
        maxY = (desktopGeom.height() - geometry.height()) or 1
        newX = (geometry.x() + 10) % maxX
        newY = ((geometry.y() + 10) % maxY) or 30
        
        geometry = QtCore.QRect(newX, newY, geometry.width(), geometry.height())
        self.setGeometry(geometry)
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addWidget(self.imageview)
        self.layout.setContentsMargins(0, 0, 0, 0)
        if g.settings['show_windows']:
            self.show()
            self.raise_()
            QtWidgets.qApp.processEvents()

    def _check_for_infinities(self, tif):
        try:
            if np.any(np.isinf(tif)):
                tif[np.isinf(tif)] = 0
                g.alert('Some array values were inf. Setting those values to 0')
        except MemoryError:
            pass

    def _init_imageview(self, tif):
        self.imageview = ImageView(self)
        self.imageview.setMouseTracking(True)
        self.imageview.installEventFilter(self)
        self.imageview.ui.normLUTbtn.pressed.connect(lambda: self.normLUT(self.image))
        self.imageview.ui.bg_imbtn.pressed.connect(self.set_bg_im)
        rp = self.imageview.ui.roiPlot.getPlotItem()
        self.linkMenu = QtWidgets.QMenu("Link frame")
        rp.ctrlMenu = self.linkMenu
        self.linkMenu.aboutToShow.connect(self.make_link_menu)
        self.imageview.setImage(tif)
        def clicked(evt):
            self.measure.pointclicked(evt, window=self)
        self.imageview.scene.sigMouseClicked.connect(clicked)
        self.imageview.timeLine.sigPositionChanged.connect(self.updateindex)
        self.currentIndex = self.imageview.currentIndex
        self.imageview.scene.sigMouseMoved.connect(self.mouseMoved)
        self.imageview.view.mouseDragEvent = self.mouseDragEvent
        self.imageview.view.mouseClickEvent = self.mouseClickEvent
        assert self.top_left_label is not None
        self.imageview.ui.graphicsView.addItem(self.top_left_label)

    def _init_dimensions(self, tif):
        if 'is_rgb' not in self.metadata.keys():
            self.metadata['is_rgb'] = tif.ndim == 4
        self.nDims = len(np.shape(tif))  #: int: The number of dimensions of the stored image.
        dimensions_txt = ""
        if self.nDims == 3:
            if self.metadata['is_rgb']:
                self.mx, self.my, mc = tif.shape
                self.mt = 1
                dimensions_txt = "{}x{} pixels; {} colors; ".format(self.mx, self.my, mc)
            else:
                self.mt, self.mx, self.my = tif.shape
                dimensions_txt = "{} frames; {}x{} pixels; ".format(self.mt, self.mx, self.my)
        elif self.nDims == 4:
            self.mt, self.mx ,self.my, mc = tif.shape
            dimensions_txt = "{} frames; {}x{} pixels; {} colors; ".format(self.mt, self.mx, self.my, mc)
        elif self.nDims == 2:
            self.mt = 1
            self.mx, self.my = tif.shape
            dimensions_txt = "{}x{} pixels; ".format(self.mx, self.my)
        dimensions_txt += 'dtype=' + str(self.dtype)
        if self.framerate is None:
            if 'timestamps' in self.metadata:
                ts = self.metadata['timestamps']
                self.framerate = (ts[-1] - ts[0]) / len(ts)
        if self.framerate is not None:
            dimensions_txt += '; {:.4f} {}/frame'.format(self.framerate, self.metadata['timestamp_units'])

        if self.top_left_label is not None and self.imageview is not None and self.top_left_label in self.imageview.ui.graphicsView.items():
            self.imageview.ui.graphicsView.removeItem(self.top_left_label)
        self.top_left_label = pg.LabelItem(dimensions_txt, justify='right')

    def _init_scatterplot(self):
        if self.scatterPlot in self.imageview.ui.graphicsView.items():
            self.imageview.ui.graphicsView.removeItem(self.scatterPlot)
        pointSize = g.settings['point_size']
        pointColor = QtGui.QColor(g.settings['point_color'])
        self.scatterPlot = pg.ScatterPlotItem(size=pointSize, pen=pg.mkPen([0, 0, 0, 255]), brush=pg.mkBrush(*pointColor.getRgb()))  #this is the plot that all the red points will be drawn on
        self.scatterPoints = [[] for _ in np.arange(self.mt)]
        self.scatterPlot.sigClicked.connect(self.clickedScatter)
        self.imageview.addItem(self.scatterPlot)

    def _init_menu(self):
        self.menu = QtWidgets.QMenu(self)

        def updateMenu():
            from .roi import ROI_Base
            pasteAct.setEnabled(isinstance(g.clipboard, (list, ROI_Base)))

        pasteAct = QtWidgets.QAction("&Paste", self, triggered=self.paste)
        plotAllAct = QtWidgets.QAction('&Plot All ROIs', self.menu, triggered=self.plotAllROIs )
        copyAll = QtWidgets.QAction("Copy All ROIs", self.menu, triggered = lambda a: setattr(g, 'clipboard', self.rois))
        removeAll = QtWidgets.QAction("Remove All ROIs", self.menu, triggered = self.removeAllROIs)
        self.menu.addAction(pasteAct)
        self.menu.addAction(plotAllAct)
        self.menu.addAction(copyAll)
        self.menu.addAction(removeAll)
        self.menu.aboutToShow.connect(updateMenu)

    def onResize(self, event):
        g.settings['window_settings']['coords'] = self.geometry().getRect()

    def onMove(self, event):
        g.settings['window_settings']['coords'] = self.geometry().getRect()

    def save(self, filename):
        """save(self, filename)
        Saves the current window to a specificed directory as a (.tif) file

        Args:
            filename (str): The filename, including the full path, where this (.tif) file will be saved.

        """
        from .process.file_ import save_file
        old_curr_win = g.win
        self.setAsCurrentWindow()
        save_file(filename)
        old_curr_win.setAsCurrentWindow()

    def normLUT(self, tif):
        if self.nDims == 2:
            # if the image is binary (either all 0s or 0s and 1s)
            if np.min(tif) == 0 and (np.max(tif) == 0 or np.max(tif) == 1):
                self.imageview.setLevels(-.01, 1.01)  # set levels from slightly below 0 to 1
            else:
                r = (np.min(tif), np.max(tif))  # set the levels to be just above and below the min and max of the image
                r = (r[0] - (r[1] - r[0]) / 100, r[1] + (r[1] - r[0]) / 100)
                self.imageview.setLevels(r[0], r[1])
        if self.nDims == 3 and not self.metadata['is_rgb']:
            if np.all(tif[self.currentIndex] == 0):  # if the current frame is all zeros
                r = (np.min(tif), np.max(tif))  # set the levels to be just above and below the min and max of the entire tif
                r = (r[0] - (r[1] - r[0]) / 100, r[1] + (r[1] - r[0]) / 100)
                self.imageview.setLevels(r[0], r[1])
            else:
                r = (np.min(tif[self.currentIndex]),
                     np.max(tif[self.currentIndex]))  # set the levels to be just above and below the min and max of the first frame
                r = (r[0] - (r[1] - r[0]) / 100, r[1] + (r[1] - r[0]) / 100)
                self.imageview.setLevels(r[0], r[1])
        elif self.nDims == 4 and not self.metadata['is_rgb']:
            if np.min(tif) == 0 and (np.max(tif) == 0 or np.max(tif) == 1):  # if the image is binary (either all 0s or 0s and 1s)
                self.imageview.setLevels(-.01, 1.01)  # set levels from slightly below 0 to 1

    def set_bg_im(self):
        self.bg_im_dialog = Bg_im_dialog(self)
        self.bg_im_dialog.show()

    def link(self, win):
        """link(self, win)
        Linking a window to another means when the current index of one changes, the index of the other will automatically change.

        Args:
            win (flika.window.Window): The window that will be linked with this one
        """
        if win not in self.linkedWindows:
            self.sigTimeChanged.connect(win.imageview.setCurrentIndex)
            self.linkedWindows.add(win)
            win.link(self)

    def unlink(self, win):
        """unlink(self, win)
        This unlinks a window from this one.

        Args:
            win (flika.window.Window): The window that will be unlinked from this one
        """
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

    def setIndex(self, index):
        """setIndex(self, index)
        This sets the index (frame) of this window. 

        Args:
            index (int): The index of the image this window will display
        """
        if hasattr(self, 'image') and self.image.ndim > 2 and 0 <= index < len(self.image):
            self.imageview.setCurrentIndex(index)

    def showFrame(self, index):
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
                    msg += '; {} h {} m {:.4f} s'.format(hours, minutes, seconds)
            g.m.statusBar().showMessage(msg)

    def setName(self,name):
        """setName(self,name)
        Set the name of this window.

        Args:
            name (str): the name for window to be set to
        """
        name = str(name)
        self.name = name
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
            if g.win==self:
                g.win=None
            if self in g.windows:
                g.windows.remove(self)
            self.closed=True
            event.accept() # let the window close

    def imageArray(self):
        """imageArray(self)

        Returns:
             Image as a 3d array, correcting for color or 2d image
        """
        tif = self.image
        nDims = len(tif.shape)
        if nDims == 4:  # If this is an RGB image stack  #[t, x, y, colors]
            tif = np.mean(tif,3)
            mx, my = tif[0, :, :].shape
        elif nDims == 3:
            if self.metadata['is_rgb']:  # [x, y, colors]
                tif = np.mean(tif,2)
                mx, my = tif.shape
                tif = tif[np.newaxis]
            else: 
                mx, my = tif[0,:,:].shape
        elif nDims == 2:
            mx, my = tif.shape
            tif = tif[np.newaxis]
        return tif

    def imageDimensions(self):
        nDims = self.image.shape
        if len(nDims) == 4: #if this is an RGB image stack
            return nDims[1:3]
        elif len(nDims) == 3:
            if self.metadata['is_rgb']:  # [x, y, colors]
                return nDims[:2]
            else:                               # [t, x, y]
                return nDims[1:]
        if len(nDims) == 2:  # If this is a static image
            return nDims
        return nDims

    def resizeEvent(self, event):
        event.accept()
        self.imageview.resize(self.size())

    def paste(self):
        """ paste(self)
        This function pastes a ROI from one window into another.
        The ROIs will be automatically linked using the link() fucntion so that when you alter one of them, the other will be altered in the same way.
        """
        def pasteROI(roi):
            if roi in self.rois:
                return None
            if roi.kind == 'rect_line':
                self.currentROI = makeROI(roi.kind, roi.pts, self, width=roi.width)
            else:
                self.currentROI = makeROI(roi.kind, roi.pts, self)
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
        """setAsCurrentWindow(self)
        This function sets this window as the current window. There is only one current window. All operations are performed on the
        current window. The current window can be accessed from the variable ``g.win``. 
        """

        if g.win is not None:
            g.win.setStyleSheet("border:1px solid rgb(0, 0, 0); ")
            g.win.lostFocusSignal.emit()
        g.win = self
        g.m.currentWindow = g.win
        g.currentWindow = g.win
        if self not in g.windows:
            g.windows.append(self)
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
        """getScatterPts(self)

        Returns:
            numpy array: an Nx3 array of scatter points, where N is the number of points. Col0 is frame, Col1 is x, Col2 is y. 
        """
        p_out=[]
        p_in=self.scatterPoints
        for t in np.arange(len(p_in)):
            for p in p_in[t]:
                p_out.append(np.array([t,p[0],p[1]]))
        p_out=np.array(p_out)
        return p_out

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
        ''''mouseClickevent(self, ev)
        Event handler for when the mouse is pressed in a flika window.
        '''
        self.EEEE = ev
        if self.x is not None and self.y is not None and ev.button() == 2 and not self.creatingROI:
            mm = g.settings['mousemode']
            if mm == 'point':
                self.addPoint()
            elif mm == 'rectangle' and g.settings['default_roi_on_click']:
                pts = [pg.Point(self.x - g.settings['rect_width']/2, self.y - g.settings['rect_height']/2), pg.Point(g.settings['rect_width'], g.settings['rect_height'])]
                self.currentROI = makeROI("rectangle", pts)
            else:
                self.menu.exec_(ev.screenPos().toQPoint())
        elif self.creatingROI:
            self.currentROI.cancel()
            self.creatingROI = None

    def save_rois(self, filename=None):
        """save_rois(self, filename=None)

        Args:
            filename (str): The filename, including the full path, where the ROI file will be saved.

        """
        if not isinstance(filename, str):
            if filename is not None and os.path.isfile(filename):
                filename = os.path.splitext(g.settings['filename'])[0]
                filename = save_file_gui('Save ROI', filename, '*.txt')
            else:
                filename = save_file_gui('Save ROI', '', '*.txt')

        if filename != '' and isinstance(filename, str):
            reprs = [roi._str() for roi in self.rois]
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
        '''mouseMoved(self,point)
        Event handler function for mouse movement.
        '''
        point=self.imageview.getImageItem().mapFromScene(point)
        self.point = point
        self.x = point.x()
        self.y = point.y()
        image=self.imageview.getImageItem().image
        if self.x < 0 or self.y < 0 or self.x >= image.shape[0] or self.y >= image.shape[1]:
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
            if g.settings['mousemode'] == 'pencil':
                if ev.isStart():
                    self.last_x = None
                    self.last_y = None
                else:
                    if self.x < 0 or self.y < 0 or self.x >= self.mx or self.y >= self.my:
                        self.last_x = None  # if we are outside the image
                        self.last_y = None
                    else:
                        x = int(self.x)
                        y = int(self.y)
                        if self.last_x == x and self.last_y == y:
                            pass
                        z = self.imageview.currentIndex
                        image = self.imageview.getImageItem().image
                        v = g.settings['pencil_value']
                        if self.last_x is None:
                            image[x, y] = v
                        else:
                            xs, ys = get_line(x, y, self.last_x, self.last_y).T
                            image[xs, ys] = v
                        self.imageview.imageItem.updateImage(image)
                        self.last_x = x
                        self.last_y = y
                        self.ev = ev
            else:
                difference=self.imageview.getImageItem().mapFromScene(ev.lastScenePos())-self.imageview.getImageItem().mapFromScene(ev.scenePos())
                self.imageview.view.translateBy(difference)
        if ev.button() == QtCore.Qt.RightButton:
            ev.accept()
            mm = g.settings['mousemode']
            if mm in ('freehand', 'line', 'rectangle', 'rect_line'):
                if ev.isStart():
                    self.ev = ev
                    pt = self.imageview.getImageItem().mapFromScene(ev.buttonDownScenePos())
                    self.x = pt.x()  # This sets x and y to the button down position, not the current position.
                    self.y = pt.y()
                    self.creatingROI = True
                    self.currentROI = ROI_Drawing(self, self.x, self.y, mm)
                if ev.isFinish():
                    if self.creatingROI:   
                        if ev._buttons | QtCore.Qt.RightButton != ev._buttons:
                            self.currentROI = self.currentROI.drawFinished()
                            self.creatingROI = False
                        else:
                            self.currentROI.cancel()
                            self.creatingROI = False
                else:  # If we are in the middle of the drag between starting and finishing.
                    if self.creatingROI:
                        self.currentROI.extend(self.x, self.y)

    def updateTimeStampLabel(self,frame):
        label = self.timeStampLabel
        if self.framerate == 0:
            label.setHtml("<span style='font-size: 12pt;color:white;background-color:None;'>Frame rate is 0 Hz</span>" )
            return False
        ttime = frame/self.framerate  # Time elapsed since the first frame until the current frame, in seconds.
        if ttime < 1:
            ttime = ttime * 1000
            label.setHtml("<span style='font-size: 12pt;color:white;background-color:None;'>{:.0f} ms</span>".format(ttime))
        elif ttime < 60:
            label.setHtml("<span style='font-size: 12pt;color:white;background-color:None;'>{:.3f} s</span>".format(ttime))
        elif ttime < 3600:
            minutes = int(np.floor(ttime/60))
            seconds = ttime % 60
            label.setHtml("<span style='font-size: 12pt;color:white;background-color:None;'>{}m {:.3f} s</span>".format(minutes,seconds))
        else:
            hours = int(np.floor(ttime/3600))
            mminutes = ttime-hours*3600
            minutes = int(np.floor(mminutes/60))
            seconds = mminutes-minutes*60
            label.setHtml("<span style='font-size: 12pt;color:white;background-color:None;'>{}h {}m {:.3f} s</span>".format(hours,minutes,seconds))
logger.debug("Completed 'reading window.py'")


def get_line(x1, y1, x2, y2):
    """Bresenham's Line Algorithm
    Produces a list of tuples """
    # Setup initial conditions
    dx = x2 - x1
    dy = y2 - y1

    # Determine how steep the line is
    is_steep = abs(dy) > abs(dx)

    # Rotate line
    if is_steep:
        x1, y1 = y1, x1
        x2, y2 = y2, x2

    # Swap start and end points if necessary and store swap state
    swapped = False
    if x1 > x2:
        x1, x2 = x2, x1
        y1, y2 = y2, y1
        swapped = True

    # Recalculate differentials
    dx = x2 - x1
    dy = y2 - y1

    # Calculate error
    error = int(dx / 2.0)
    ystep = 1 if y1 < y2 else -1

    # Iterate over bounding box generating points between start and end
    y = y1
    points = []
    for x in range(x1, x2 + 1):
        coord = [y, x] if is_steep else [x, y]
        points.append(coord)
        error -= abs(dy)
        if error < 0:
            y += ystep
            error += dx

    # Reverse the list if the coordinates were swapped
    if swapped:
        points.reverse()
    return np.array(points)