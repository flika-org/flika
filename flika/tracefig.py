# -*- coding: utf-8 -*-
from .logger import logger
logger.debug("Started 'reading tracefig.py'")
import os
import time
import numpy as np
from qtpy import QtCore, QtGui, QtWidgets
from scipy.fftpack import fft, fftfreq, fftshift
import pyqtgraph as pg
from pyqtgraph.dockarea import *
from . import global_vars as g
from .utils.misc import save_file_gui


pg.setConfigOptions(useWeave=False)


class TraceFig(QtWidgets.QWidget):
    """Pyqtgraph PlotWidget with frame range selector. Display average trace of ROIs and updates in realtime.
    
    Attributes:
        p1 (pg.PlotWidget): top plot widget displaying selected region of traces
        p2 (pg.PlotWidget): bottom plot widget displaying entire traces with region selection
        rois ([dict]): list of roi information dicts for reference

    Signals:
        :indexChanged(int): emits the index of the mouse when the user hovers over the top plotWidget
        :finishedDrawingSignal(): emits when the bottom ROI is finished updating
        :keyPressSignal(QtCore.QEvent): emits when the traceWindow is selected and a key is pressed
        :partialThreadUpdatedSignal(): emits when the top plot widget is updated
    """
    indexChanged=QtCore.Signal(int)
    finishedDrawingSignal=QtCore.Signal()
    keyPressSignal=QtCore.Signal(QtCore.QEvent)
    partialThreadUpdatedSignal = QtCore.Signal()
    name = "Trace Widget"

    def __init__(self):
        super(TraceFig, self).__init__()
        g.traceWindows.append(self)
        self.setCurrentTraceWindow()
        if 'tracefig_settings' in g.settings and 'coords' in g.settings['tracefig_settings']:
            self.setGeometry(QtCore.QRect(*g.settings['tracefig_settings']['coords']))
        else:
            self.setGeometry(QtCore.QRect(355, 30, 1219, 148))
        self.setWindowTitle('flika')
        self.l = QtWidgets.QVBoxLayout()

        self.l.setContentsMargins(0,0,0,0)
        self.setLayout(self.l)
        self.p1=pg.PlotWidget()
        self.p2=pg.PlotWidget()
        self.p1.getPlotItem().axes['left']['item'].setGrid(100) #this makes faint horizontal lines
        self.p2.setMaximumHeight(50)
        self.export_button = QtWidgets.QPushButton("Export")
        self.export_button.setMaximumWidth(100)
        self.export_button.clicked.connect(self.export_gui)
        self.power_spectrum_button = QtWidgets.QPushButton("Power Spectrum")
        self.power_spectrum_button.setMaximumWidth(100)
        self.power_spectrum_button.clicked.connect(self.generate_power_spectrum)
        self.button_layout = QtWidgets.QGridLayout()
        self.l.addWidget(self.p1, 1)
        self.l.addWidget(self.p2, 1)
        self.l.addLayout(self.button_layout)
        self.button_layout.setContentsMargins(0, 0, 0, 0)
        self.button_layout.addWidget(self.export_button, 0, 0)
        self.button_layout.addWidget(self.power_spectrum_button, 0, 1)
        verticalSpacer = QtWidgets.QSpacerItem(10, 10, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.button_layout.addItem(verticalSpacer, 0, 2)
    
        self.region = pg.LinearRegionItem()         # Add the LinearRegionItem to the ViewBox, but tell the ViewBox to exclude this item when doing auto-range calculations.
        self.region.setZValue(10)
        self.p2.plotItem.addItem(self.region, ignoreBounds=True)
        self.p1.setAutoVisible(y=True)
        self.rois=[] # roi in this list is a dict: {roi, p1trace,p2trace, sigproxy}
        self.redrawPartialThread = None
        self.vb = self.p1.plotItem.getViewBox()
        
        self.proxy = pg.SignalProxy(self.p1.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)
        self.p2.plotItem.vb.mouseDragEvent=self.mouseDragEvent2
        
        self.region.sigRegionChanged.connect(self.update)
        self.p1.plotItem.sigRangeChanged.connect(self.updateRegion)
        self.region.setRegion([0, 200])

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.p1.update)
        self.timer.start()

        from .process.measure import measure
        self.measure=measure
        self.p1.scene().sigMouseClicked.connect(self.measure.pointclicked)
        self.p1.scene().sigMouseClicked.connect(self.setCurrentTraceWindow)
        self.resizeEvent = self.onResize
        self.moveEvent = self.onMove
        
        if 'tracefig_settings' not in g.settings:
            g.settings['tracefig_settings']=dict()
            try:
                g.settings['tracefig_settings']['coords']=self.geometry().getRect()
            except Exception as e:
                g.alert(e)
        self.show()
        
    def onResize(self,event):
        g.settings['tracefig_settings']['coords']=self.geometry().getRect()

    def onMove(self,event):
        g.settings['tracefig_settings']['coords']=self.geometry().getRect()
        
    def setCurrentTraceWindow(self):
        if g.currentTrace is not None:
            g.currentTrace.setStyleSheet("border:1px solid rgb(0, 0, 0); ")
        self.setStyleSheet("border:1px solid rgb(0, 255, 0); ")
        g.currentTrace = self

    def mouseDragEvent2(self,ev):
        ev.ignore() # prevent anything from happening

    def mouseDragEvent1(self,ev):
        ev.ignore() # prevent anything from happening

    def keyPressEvent(self,ev):
        self.keyPressSignal.emit(ev)

    def closeEvent(self, event):
        while len(self.rois) > 0:
            self.removeROI(0)
        try:
            self.p1.scene().sigMouseClicked.disconnect(self.measure.pointclicked)
            self.p1.scene().sigMouseClicked.disconnect(self.setCurrentTraceWindow)
        except:
            pass
        if self in g.traceWindows:
            g.traceWindows.remove(self)
        g.currentTrace = None
        event.accept() # let the window close

    def update(self):
        self.region.setZValue(10)
        minX, maxX = self.region.getRegion()
        self.p1.plotItem.setXRange(minX, maxX, padding=0, update=False)    
        self.p1.plotItem.axes['bottom']['item'].setRange(minX,maxX)

    def updateRegion(self,window, viewRange):
        rgn = viewRange[0]
        self.region.setRegion(rgn)

    def getBounds(self):
        bounds=self.region.getRegion()
        bounds=[int(np.floor(bounds[0])),int(np.ceil(bounds[1]))+1]
        return bounds

    def mouseMoved(self,evt):
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        if modifiers == QtCore.Qt.ShiftModifier:
            pass
        else:
            pos = evt[0]  ## using signal proxy turns original arguments into a tuple
            if self.p1.plotItem.sceneBoundingRect().contains(pos):
                mousePoint = self.vb.mapSceneToView(pos)
                index = int(mousePoint.x())
                if index >= 0:
                    #self.label.setText("<span style='font-size: 12pt'>frame={0}</span>".format(index))
                    self.indexChanged.emit(index)
                    g.m.statusBar().showMessage('frame {}    y={}'.format(index,mousePoint.y()))
    
    def get_roi_index(self,roi):
        return [r['roi'] for r in self.rois].index(roi)
        
    def alert(self, msg):
        #print(msg)
        pass

    def translated(self,roi):
        index=self.get_roi_index(roi)
        self.rois[index]['toBeRedrawn']=True
        if self.redrawPartialThread is None or self.redrawPartialThread.isFinished():
            self.alert('Launching redrawPartialThread')
            self.redrawPartialThread = RedrawPartialThread(self)
            self.redrawPartialThread.alert.connect(self.alert)
            self.redrawPartialThread.start()
            self.redrawPartialThread.updated.connect(self.partialThreadUpdatedSignal.emit)
            
    def translateFinished(self, roi):
        roi_index = self.get_roi_index(roi)
        if self.redrawPartialThread is not None and self.redrawPartialThread.isRunning():
            self.redrawPartialThread.quit_loop = True
            #self.redrawPartialThread.finished_sig.emit() #tell the thread to finish
            #loop = QtCore.QEventLoop()
            #self.redrawPartialThread.finished.connect(loop.quit)
            #loop.exec_()# This blocks until the "finished" signal is emitted
        trace=roi.getTrace()
        self.update_trace_full(roi_index, trace)

    def update_trace_full(self, roi_index, trace):
        pen=QtGui.QPen(self.rois[roi_index]['roi'].pen)
        self.rois[roi_index]['p1trace'].setData(trace,pen=pen)
        self.rois[roi_index]['p2trace'].setData(trace,pen=pen)
        self.finishedDrawingSignal.emit()
        
    def addROI(self,roi):
        if self.hasROI(roi):
            return
        trace=roi.getTrace()
        if trace is None:
            raise InvalidTraceException()
        pen=QtGui.QPen(roi.pen)
        pen.setWidth(0)
        if len(trace)==1:
            p1trace=self.p1.plot(trace, pen=None, symbol='o')
            p2trace=self.p2.plot(trace, pen=None, symbol='o')
        else:
            p1trace=self.p1.plot(trace, pen=pen)
            p2trace=self.p2.plot(trace, pen=pen) 
        
        roi.sigRegionChanged.connect(self.translated)
        roi.sigRegionChangeFinished.connect(self.translateFinished)

        if len(self.rois) == 0:
            self.region.setRegion([0, len(trace)-1])
        self.rois.append(dict({'roi':roi,'p1trace':p1trace,'p2trace':p2trace,'toBeRedrawn':False,'toBeRedrawnFull':False}))

    def removeROI(self,roi):
        from .roi import ROI_Base
        if isinstance(roi, ROI_Base):
            index=[r['roi'] for r in self.rois].index(roi) #this is the index of the roi in self.rois
        elif isinstance(roi, int):
            index = roi
        else:
            g.alert("Failed to remove roi {}".format(roi))
            return
        self.p1.removeItem(self.rois[index]['p1trace'])
        self.p2.removeItem(self.rois[index]['p2trace'])
        self.rois[index]['roi'].traceWindow = None
        try:
            self.rois[index]['roi'].resetSignals()
        except:
            pass
        del self.rois[index]
        if len(self.rois)==0:
            self.close()

    def hasROI(self,roi):
        return roi in [r['roi'] for r in self.rois] #return True if roi is plotted

    def export_gui(self):
        filename = g.settings['filename']
        directory = os.path.dirname(filename)
        if filename is not None:
            filename = save_file_gui('Save Traces', directory, '*.txt')
        else:
            filename = save_file_gui('Save Traces', '', '*.txt')
        if filename == '':
            return False
        else:
            self.export(filename)

    def export(self,filename):
        ''' This function saves out all the traces in the tracefig to a file specified by the argument 'filename'.
        The output file is a tab seperated ascii file where each column is a trace.  
        Traces are saved in the order they were added to the plot.
        
        '''
        g.m.statusBar().showMessage('Saving {}'.format(os.path.basename(filename)))
        traces=[]
        for roi in self.rois:
            traces.append(roi['roi'].getTrace())
        traces.insert(0,np.arange(len(traces[0])))
        traces=np.array(traces).T
        np.savetxt(filename,traces,delimiter='\t',fmt='%10f')
        g.m.statusBar().showMessage('Successfully saved {}'.format(os.path.basename(filename)))

    def generate_power_spectrum(self):
        sample_interval = 1
        self.fft_analyzer = FFT_Analyzer(self.rois, sample_interval, self)

class FFT_Analyzer(QtWidgets.QWidget):
    def __init__(self, rois, sample_interval, tracefig, parent = None) :
        QtWidgets.QWidget.__init__(self, parent)
        """
        sample_interval is the sample_duration in seconds. If the sample is 1000 Hz, sample_interval = .001 (1 ms)
        """
        self.tracefig = tracefig
        self.rois = rois
        geo = self.tracefig.geometry()
        geo.adjust(0, geo.height(), 0, geo.height())
        self.setGeometry(geo)
        self.setWindowTitle("Power Spectrum")
        self.l = QtWidgets.QVBoxLayout()
        self.setLayout(self.l)
        self.area = DockArea()
        self.l.addWidget(self.area)

        self.d3 = Dock("FFT")
        self.area.addDock(self.d3, size=(382, 216))
        self.fftplt = pg.PlotWidget()
        self.d3.addWidget(self.fftplt)
        self.fftplt.showGrid(x=True, y=True)
        self.fftplt.setLogMode(x=True,y=True)
        self.fftplt.setLabel('bottom', 'Frequency')
        self.fftplt.setLabel('left', 'Power')
        self.sample_interval = sample_interval
        self.set_data(rois, self.sample_interval)

        self.export_button = QtWidgets.QPushButton("Export")
        self.export_button.setMaximumWidth(100)
        self.export_button.clicked.connect(self.export_gui)
        self.d3.addWidget(self.export_button)
        self.show()

    def set_data(self, rois, sample_interval):
        traces = []
        pens = []
        for roi in rois:
            traces.append(roi['roi'].getTrace())
            pen = QtGui.QPen(roi['roi'].pen)
            pen.setWidth(0)
            pens.append(pen)

        longest_trace_len = np.max([len(trace) for trace in traces])
        N = int(2**np.floor(np.log2(longest_trace_len)))
        # x = np.linspace(0.0, N * sample_interval, N)
        for i in np.arange(len(rois)):
            trace = traces[i]
            yf = fft(trace[-N:])
            xf = fftfreq(N, sample_interval)
            xf = xf[1:int(N / 2)]
            yf = np.abs(yf[1:int(N / 2)])**2
            rois[i]['power_spectrum_x'] = xf
            rois[i]['power_spectrum_y'] = yf
            self.fftplt.plot(xf, yf, pen=pens[i])

    def export_gui(self):
        filename = g.settings['filename']
        directory = os.path.dirname(filename)
        if filename is not None:
            filename = save_file_gui('Save Power Spectrum', directory, '*.csv')
        else:
            filename = save_file_gui('Save Power Spectrum', '', '*.csv')
        if filename == '':
            return False
        else:
            self.export(filename)

    def export(self, filename):
        ''' This function saves out all the traces in the 'Power Spectrum" to a file specified by the argument 'filename'.
        The output file is a csv.
        Traces are saved in the order they were added to the tracefig window.

        '''
        g.m.statusBar().showMessage('Saving {}'.format(os.path.basename(filename)))
        traces = []
        headers = []
        cols = []
        for i, roi in enumerate(self.rois):
            cols.append(roi['power_spectrum_x'])
            cols.append(roi['power_spectrum_y'])
            headers.append('X roi{}'.format(i))
            headers.append('Y roi{}'.format(i))
        header = ','.join(headers)
        cols = np.array(cols).T
        np.savetxt(filename, cols, header=header, delimiter=',', comments='', fmt='%10f')
        g.m.statusBar().showMessage('Successfully saved {}'.format(os.path.basename(filename)))


def roiPlot(roi):
    '''
    returns tracefig that is used to plot roi
    '''
    if g.settings['multipleTraceWindows'] or g.currentTrace is None:
        win = TraceFig()
    else:
        win = g.currentTrace
    try:
        win.addROI(roi)
    except InvalidTraceException:
        if len(win.rois) == 0:
            win.close()
            return None
    return win


class RedrawPartialThread(QtCore.QThread):
    finished=QtCore.Signal() #this announces that the thread has finished
    finished_sig=QtCore.Signal() #This tells the thread to finish
    alert = QtCore.Signal(str)
    updated = QtCore.Signal() #This signal is emitted after each redraw

    def __init__(self,tracefig):
        QtCore.QThread.__init__(self)
        self.tracefig=tracefig
        self.redrawCompleted=True
        self.quit_loop=False
        
    def run(self):
        self.finished_sig.connect(self.request_quit_loop)
        while self.quit_loop is False:
            time.sleep(.05)
            self.redraw()
            self.updated.emit()
        self.alert.emit("Finished Redraw")
        self.finished.emit()
        
    def request_quit_loop(self):
        self.quit_loop=True
        
    def redraw(self):
        if self.redrawCompleted is False:
            self.alert.emit("Redraw hasn't finished")
            pass
        else:
            self.alert.emit("Redrawing")
            self.redrawCompleted=False
            idxs=[]
            for i in np.arange(len(self.tracefig.rois)):
                if self.tracefig.rois[i]['toBeRedrawn']:
                    self.tracefig.rois[i]['toBeRedrawn']=False
                    idxs.append(i)
            traces=[]
            bounds=self.tracefig.getBounds()
            bounds = [max(0, bounds[0]), bounds[1]]
            for i in idxs:
                roi=self.tracefig.rois[i]['roi']
                trace=roi.getTrace(bounds)
                traces.append(trace)
            for i, roi_index in enumerate(idxs):
                trace=traces[i] #This function can sometimes take a long time.  
                pen=QtGui.QPen(self.tracefig.rois[roi_index]['roi'].pen)
                bb=self.tracefig.getBounds()
                curve=self.tracefig.rois[roi_index]['p1trace']
                newtrace=curve.getData()[1]
                if bb[0]<0: bb[0]=0
                if bb[1]>len(newtrace): bb[1]=len(newtrace)
                if bb[1]<0 or bb[0]>len(newtrace):
                    return
                newtrace[bb[0]:bb[1]]=trace
                curve.setData(newtrace,pen=pen)
                self.alert.emit("CURVE {} redrawn".format(roi_index))
                QtWidgets.qApp.processEvents()
            self.redrawCompleted=True

class InvalidTraceException(Exception):
    pass


logger.debug("Completed 'reading tracefig.py'")
