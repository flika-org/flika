# -*- coding: utf-8 -*-
"""
Created on Thu Jun 26 16:10:00 2014

@author: Kyle Ellefsen
"""
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtCore import pyqtSignal as Signal
import pyqtgraph as pg
pg.setConfigOptions(useWeave=False)
import os, time
import numpy as np
from tracefig import TraceFig
import global_vars as g
from roi import *

class Window(QWidget):
    closeSignal=Signal()
    keyPressSignal=Signal(QEvent)
    sigTimeChanged=Signal(int)
    def __init__(self,tif,name='Flika',filename='',commands=[],metadata=dict()):
        QWidget.__init__(self)
        self.commands=commands #commands is a list of the commands used to create this window, starting with loading the file
        self.metadata=metadata
        if 'is_rgb' not in metadata.keys():
            metadata['is_rgb']=False

        if g.m.currentWindow is None:
            width=684
            height=585
            nwindows=len(g.m.windows)
            x=10+10*nwindows
            y=484+10*nwindows
        else:
            oldGeometry=g.m.currentWindow.geometry()
            width=oldGeometry.width()
            height=oldGeometry.height()
            x=oldGeometry.x()+10
            y=oldGeometry.y()+10
        self.name=name
        self.filename=filename
        self.setAsCurrentWindow()
        self.setWindowTitle(name)
        self.setWindowIcon(QIcon('images/favicon.png'))
        self.imageview=pg.ImageView(self)
        self.imageview.setMouseTracking(True)
        self.imageview.installEventFilter(self)
        self.imageview.ui.menuBtn.setParent(None)





        #self.imageview.ui.normBtn.setParent(None) # gets rid of 'norm' button that comes with ImageView
        self.imageview.ui.roiBtn.setParent(None) # gets rid of 'roi' button that comes with ImageView

        self.imageview.ui.normLUTbtn = QPushButton(self.imageview.ui.layoutWidget)
        #sizePolicy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        #sizePolicy.setHorizontalStretch(0)
        #sizePolicy.setVerticalStretch(1)
        #sizePolicy.setHeightForWidth(self.imageview.ui.roiBtn.sizePolicy().hasHeightForWidth())
        #self.imageview.ui.roiBtn.setSizePolicy(sizePolicy)
        #self.imageview.ui.normLUTbtn.setCheckable(True)
        self.imageview.ui.normLUTbtn.setObjectName("LUT norm")
        self.imageview.ui.normLUTbtn.setText("LUT norm")
        self.imageview.ui.gridLayout.addWidget(self.imageview.ui.normLUTbtn, 1, 1, 1, 1)
        self.imageview.ui.normLUTbtn.pressed.connect(self.normLUT)



        rp = self.imageview.ui.roiPlot.getPlotItem()
        self.linkMenu = QMenu("Link frame")
        rp.ctrlMenu = self.linkMenu
        self.linkMenu.aboutToShow.connect(self.make_link_menu)
        self.imageview.setImage(tif)

        self.image=tif
        """ Here we set the initial range of the look up table.  """
        self.nDims = len(np.shape(self.image))
        if self.nDims == 3:
            if metadata['is_rgb']:
                mx,my,mc=tif.shape
                mt=1
                dimensions_txt="{}x{} pixels; {} colors; ".format(mx,my,mc)
            else:
                mt,mx,my=tif.shape
                dimensions_txt="{} frames; {}x{} pixels; ".format(mt,mx,my)
        elif self.nDims == 4:
            mt,mx,my,mc = tif.shape
            dimensions_txt = "{} frames; {}x{} pixels; {} colors; ".format(mt,mx,my,mc)
        elif self.nDims == 2:
            mt=1
            mx,my=tif.shape
            dimensions_txt="{}x{} pixels; ".format(mx,my)
        self.mx = mx; self.my = my; self.mt = mt
        dtype=self.image.dtype

        self.top_left_label = pg.LabelItem(dimensions_txt+'dtype='+str(dtype), justify='right')
        self.imageview.ui.graphicsView.addItem(self.top_left_label)
        
        self.imageview.timeLine.sigPositionChanged.connect(self.updateindex)
        self.currentIndex=self.imageview.currentIndex
        self.normLUT()
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.imageview)
        self.layout.setContentsMargins(0,0,0,0)
        self.setGeometry(QRect(x, y, width, height))
        self.imageview.scene.sigMouseMoved.connect(self.mouseMoved)
        self.imageview.view.mouseDragEvent=self.mouseDragEvent
        self.imageview.view.mouseClickEvent=self.mouseClickEvent
        self.rois=[]
        self.currentROI=None
        self.currentROIs={}
        self.creatingROI=False
        pointSize=g.settings['point_size']
        pointColor = QColor(g.settings['point_color'])
        self.scatterPlot=pg.ScatterPlotItem(size=pointSize, pen=pg.mkPen([0,0,0,255]), brush=pg.mkBrush(*pointColor.getRgb()))  #this is the plot that all the red points will be drawn on
        self.scatterPoints=[[] for _ in np.arange(mt)]
        self.scatterPlot.sigClicked.connect(self.clickedScatter)
        self.imageview.addItem(self.scatterPlot)
        self.pasteAct = QAction("&Paste", self, triggered=self.paste)
        if g.settings['show_windows']:
            self.show()
            qApp.processEvents()
        self.sigTimeChanged.connect(self.showFrame)
        if self not in g.m.windows:
            g.m.windows.append(self)
        self.closed=False

        self.linkedWindows = []

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
            self.linkedWindows.append(win)
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
        for win in g.m.windows:
            if win == self or not win.isVisible():
                continue
            win_action = QAction("%s" % win.name, self.linkMenu, checkable=True)
            win_action.setChecked(win in self.linkedWindows)
            win_action.toggled.connect(self.link_toggled(win))
            self.linkMenu.addAction(win_action)
        
    def updateindex(self):
        (idx, t) = self.imageview.timeIndex(self.imageview.timeLine)
        t = int(np.floor(t))
        if 0 <= t < self.mt:
            self.currentIndex = t
            if not g.m.settings['show_all_points']:
                pointSizes = [pt[3] for pt in self.scatterPoints[t]]
                brushes = [pg.mkBrush(*pt[2].getRgb()) for pt in self.scatterPoints[t]]
                self.scatterPlot.setPoints(pos=self.scatterPoints[t], size=pointSizes, brush=brushes)
            self.sigTimeChanged.emit(t)

    def setIndex(self,index):
        if index>=0 and index<len(self.image):
            self.imageview.setCurrentIndex(index)

    def showFrame(self,index):
        if index>=0 and index<self.mt:
            g.m.statusBar().showMessage('frame {}'.format(index))

    def setName(self,name):
        name=str(name)
        self.name=name
        self.setWindowTitle(name)
        
    def reset(self):
        currentIndex=self.currentIndex
        self.imageview.setImage(self.image,autoLevels=True) #I had autoLevels=False before.  I changed it to adjust after boolean previews.
        self.imageview.setCurrentIndex(currentIndex)
        g.m.statusBar().showMessage('')

    def closeEvent(self, event):
        if self.closed:
            print('This window was already closed')
            event.accept()
        else:
            self.closeSignal.emit()
            for win in self.linkedWindows:
                self.unlink(win)
            if hasattr(self,'image'):
                del self.image
            self.imageview.setImage(np.zeros((2,2))) #clear the memory
            #self.imageview.close()
            del self.imageview
            if g.m.currentWindow==self:
                g.m.currentWindow=None
            if self in g.m.windows:
                g.m.windows.remove(self)
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
        if g.m.clipboard in self.rois:
            return False
        self.currentROI=makeROI(g.m.clipboard.kind,g.m.clipboard.pts,self)
        self.currentROI.link(g.m.clipboard)
        
    def mousePressEvent(self,ev):
        ev.accept()
        self.setAsCurrentWindow()

    def setAsCurrentWindow(self):
        if g.m.currentWindow is not None:
            g.m.currentWindow.setStyleSheet("border:1px solid rgb(0, 0, 0); ")
        g.m.currentWindow=self
        g.m.setWindowTitle("Flika - {}".format(os.path.basename(self.name)))
        self.setStyleSheet("border:1px solid rgb(0, 255, 0); ")
        g.m.setCurrentWindowSignal.sig.emit()
    
    def clickedScatter(self, plot, points):
        p = points[0]
        x, y = p.pos()

        if g.m.settings['show_all_points']:
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
        
        
    def mouseClickEvent(self,ev):
        self.EEEE=ev
        if self.x is not None and self.y is not None and ev.button()==2:
            if self.creatingROI is False:
                mm=g.m.settings['mousemode']
                if mm=='point':
                    t=self.currentIndex
                    pointSize=g.m.settings['point_size']
                    pointColor = QColor(g.m.settings['point_color'])
                    position=[self.x,self.y, pointColor, pointSize]
                    self.scatterPoints[t].append(position)
                    self.scatterPlot.addPoints(pos=[[self.x,self.y]], size=pointSize, brush=pg.mkBrush(*pointColor.getRgb()))
                    #  self.imageview.view.__class__.mouseClickEvent(self.imageview.view, ev)
                            
                elif g.m.clipboard is not None:
                    self.menu = QMenu(self)
                    self.menu.addAction(self.pasteAct)
                    self.menu.exec_(ev.screenPos().toQPoint())

                        
    
    def keyPressEvent(self,ev):
        if ev.key() == Qt.Key_Delete:
            if self.currentROI is not None:
                self.currentROI.delete()
        self.keyPressSignal.emit(ev)
        
    def mouseMoved(self,point):
        point=self.imageview.getImageItem().mapFromScene(point)
        self.point=point
        self.x=point.x()
        self.y=point.y()
        image=self.imageview.getImageItem().image
        if self.x<0 or self.y<0 or self.x>=image.shape[0] or self.y>=image.shape[1]:
            pass# if we are outside the image
        else:
            z=self.imageview.currentIndex
            value=image[int(self.x),int(self.y)]
            g.m.statusBar().showMessage('x={}, y={}, z={}, value={}'.format(int(self.x),int(self.y),z,value))
        

    def mouseDragEvent(self, ev):
        modifiers = QApplication.keyboardModifiers()
        if modifiers == Qt.ShiftModifier:
            pass #This is how I detect that the shift key is held down.
        if ev.button() == Qt.LeftButton:
            ev.accept()
            difference=self.imageview.getImageItem().mapFromScene(ev.lastScenePos())-self.imageview.getImageItem().mapFromScene(ev.scenePos())
            self.imageview.view.translateBy(difference)
        if ev.button() == Qt.RightButton:
            ev.accept()
            mm=g.m.settings['mousemode']
            if mm in ('freehand', 'line', 'rectangle', 'rect_line'):
                if ev.isStart():
                    self.ev=ev
                    pt=self.imageview.getImageItem().mapFromScene(ev.buttonDownScenePos())
                    self.x=pt.x() # this sets x and y to the button down position, not the current position
                    self.y=pt.y()
                    self.creatingROI=True
                    self.currentROI=ROI_Drawing(self,self.x,self.y, mm)
                if ev.isFinish():
                    if self.creatingROI:
                        self.currentROI = self.currentROI.drawFinished()
                        self.creatingROI=False
                    else: 
                        for r in self.currentROIs:
                            r.finish_translate()
                else: # if we are in the middle of the drag between starting and finishing
                    #if inImage:
                    if self.creatingROI:
                        self.currentROI.extend(self.x,self.y)
                    else:
                        difference=self.imageview.getImageItem().mapFromScene(ev.scenePos())-self.imageview.getImageItem().mapFromScene(ev.lastScenePos())
                        if difference.isNull():
                            return
                        for r in self.currentROIs:
                            r.translate(difference,self.imageview.getImageItem().mapFromScene(ev.lastScenePos()))
    def updateTimeStampLabel(self,frame):
        label=self.timeStampLabel
        if self.framerate==0:
            label.setHtml("<span style='font-size: 12pt;color:white;background-color:None;'>Frame rate is 0 Hz</span>" )
            return False
        ttime=frame/self.framerate
        
        if ttime<1:
            ttime=ttime*1000
            label.setHtml("<span style='font-size: 12pt;color:white;background-color:None;'>{:.0f} ms</span>".format(ttime))
        elif ttime<60:
            label.setHtml("<span style='font-size: 12pt;color:white;background-color:None;'>{:.3f} s</span>".format(ttime))
        elif ttime<3600:
            minutes=int(np.floor(ttime/60))
            seconds=ttime % 60
            label.setHtml("<span style='font-size: 12pt;color:white;background-color:None;'>{}m {:.3f} s</span>".format(minutes,seconds))
        else:
            hours=int(np.floor(ttime/3600))
            mminutes=ttime-hours*3600
            minutes=int(np.floor(mminutes/60))
            seconds=mminutes-minutes*60
            label.setHtml("<span style='font-size: 12pt;color:white;background-color:None;'>{}h {}m {:.3f} s</span>".format(hours,minutes,seconds))
