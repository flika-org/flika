# -*- coding: utf-8 -*-
"""
Created on Sun Jun 29 13:13:59 2014

@author: Kyle Ellefsen
"""
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import pyqtgraph as pg
pg.setConfigOptions(useWeave=False)
import numpy as np
import global_vars as g
import os
import time

default_trace_color='w' #'k' is black and 'w' is white 

class TraceFig(QWidget):
    indexChanged=Signal(int)
    redrawROIsPartialSlot=Signal()
    finishedDrawingSignal=Signal()
    keyPressSignal=Signal(QEvent)
    name = "Trace Widget"
    def __init__(self):
        super(TraceFig,self).__init__()
        g.m.traceWindows.append(self)
        self.setCurrentTraceWindow()
        #roi.translated.connect(lambda: self.translated(roi))
        #self.setGeometry(QRect(8,150,1901,296))
        self.label = pg.LabelItem(justify='right')
        self.l = QVBoxLayout()
        self.setLayout(self.l)
        self.p1=pg.PlotWidget()
        self.p2=pg.PlotWidget()
        self.p1.getPlotItem().axes['left']['item'].setGrid(100) #this makes faint horizontal lines
        self.p2.setMaximumHeight(50)
        self.export_button = QPushButton("Export")
        self.export_button.setMaximumWidth(100)
        self.export_button.clicked.connect(self.export_gui)
        #self.l.addItem(self.label)
        self.l.addWidget(self.p1, 1)
        self.l.addWidget(self.p2, 1)
        self.l.addWidget(self.export_button, 0)
    
        self.region = pg.LinearRegionItem()         # Add the LinearRegionItem to the ViewBox, but tell the ViewBox to exclude this item when doing auto-range calculations.
        self.region.setZValue(10)
        self.p2.plotItem.addItem(self.region, ignoreBounds=True)
        self.p1.setAutoVisible(y=True)
        #self.traces=[]
        self.rois=[] # roi in this list is a dict: {roi, p1trace,p2trace, sigproxy}
        #self.sigproxies=[]
        self.vb = self.p1.plotItem.getViewBox()
        
        self.proxy = pg.SignalProxy(self.p1.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)
        self.p2.plotItem.vb.mouseDragEvent=self.mouseDragEvent2
        
        self.region.sigRegionChanged.connect(self.update)
        self.p1.plotItem.sigRangeChanged.connect(self.updateRegion)
        self.region.setRegion([0, 200])
        self.redrawROIsPartialSlot.connect(self.redrawROIsPartial)
        #self.proxy2= pg.SignalProxy(self.redrawROIsPartialSlot,rateLimit=60, slot=self.redrawROIsPartial)
        self.redrawPartialThread=None
        self.redrawFullThread=None
        from analyze.measure import measure
        self.measure=measure
        self.p1.scene().sigMouseClicked.connect(self.measure.pointclicked)
        self.p1.scene().sigMouseClicked.connect(self.setCurrentTraceWindow)
        self.show()

    def setCurrentTraceWindow(self):
        if g.m.currentTrace is not None:
            g.m.currentTrace.setStyleSheet("border:1px solid rgb(0, 0, 0); ")
        self.setStyleSheet("border:1px solid rgb(0, 255, 0); ")
        g.m.currentTrace = self

    def mouseDragEvent2(self,ev):
        ev.ignore() # prevent anything from happening
    def mouseDragEvent1(self,ev):
        ev.ignore() # prevent anything from happening
    def keyPressEvent(self,ev):
        self.keyPressSignal.emit(ev)
    def closeEvent(self, event):
        for roi in self.rois:
            self.removeROI(roi['roi'])
        self.p1.scene().sigMouseClicked.disconnect(self.measure.pointclicked)
        self.p1.scene().sigMouseClicked.disconnect(self.setCurrentTraceWindow)

        g.m.currentTrace = None
        event.accept() # let the window close
    def update(self):
        self.region.setZValue(10)
        minX, maxX = self.region.getRegion()
        self.p1.plotItem.setXRange(minX, maxX, padding=0, update=False)    
        self.p1.plotItem.axes['bottom']['item'].setRange(minX,maxX)
        #self.p1.plotItem.update()
    def updateRegion(self,window, viewRange):
        rgn = viewRange[0]
        self.region.setRegion(rgn)
    def getBounds(self):
        bounds=self.region.getRegion()
        bounds=[int(np.floor(bounds[0])),int(np.ceil(bounds[1]))]
        return bounds

    def mouseMoved(self,evt):
        modifiers = QApplication.keyboardModifiers()
        if modifiers == Qt.ShiftModifier:
            pass
        else:
            pos = evt[0]  ## using signal proxy turns original arguments into a tuple
            if self.p1.plotItem.sceneBoundingRect().contains(pos):
                mousePoint = self.vb.mapSceneToView(pos)
                index = int(mousePoint.x())
                if index >= 0:
                    self.label.setText("<span style='font-size: 12pt'>frame={0}</span>".format(index))
                    self.indexChanged.emit(index)
                    g.m.statusBar().showMessage('frame {}    y={}'.format(index,mousePoint.y()))

    
    def get_roi_index(self,roi):
        return [r['roi'] for r in self.rois].index(roi)
    def translated(self,roi):
        index=self.get_roi_index(roi)
        self.rois[index]['toBeRedrawn']=True
        self.redrawROIsPartialSlot.emit()
    def translate_done(self,roi):
        index=self.get_roi_index(roi)
        self.rois[index]['toBeRedrawnFull']=True
        if self.redrawFullThread is None or self.redrawFullThread.isFinished():
            self.redrawFullThread=RedrawFullThread(self,roi)
            if self.redrawPartialThread is not None and self.redrawPartialThread.isRunning():
                self.redrawPartialThread.finished.connect(self.redrawFullThread.start)
            else:
                self.redrawFullThread.start()
                
    def redrawROIsPartial(self):
        if self.redrawPartialThread is None or self.redrawPartialThread.isFinished():
            self.redrawPartialThread=RedrawPartialThread(self)
            #self.redrawPartialThread.finished.connect(self.printtoc)
            self.redrawPartialThread.start()
            
    def printtoc(self,toc):
        print(toc)
        
    def update_trace_full(self,roi_index,trace):
        pen=QPen(self.rois[roi_index]['roi'].color)
        self.rois[roi_index]['p1trace'].setData(trace,pen=pen)
        self.rois[roi_index]['p2trace'].setData(trace,pen=pen)
        self.finishedDrawingSignal.emit()
    def update_trace_partial(self,roi_index,trace):
        pen=QPen(self.rois[roi_index]['roi'].color)
        bounds=self.getBounds()
        newtrace=self.rois[roi_index]['p1trace'].getData()[1]
        if bounds[0]<0: bounds[0]=0
        if bounds[1]>len(newtrace): bounds[1]=len(newtrace)
        if bounds[1]<0 or bounds[0]>len(newtrace):
            return
        newtrace[bounds[0]:bounds[1]]=trace
        self.rois[roi_index]['p1trace'].setData(newtrace,pen=pen)
        self.finishedDrawingSignal.emit()
        
        
    def addROI(self,roi):
        if self.hasROI(roi):
            return
        trace=roi.getTrace()
        pen=QPen(roi.color)
        p1trace=self.p1.plot(trace, pen=pen)
        p2trace=self.p2.plot(trace, pen=pen) 
        roi.translated.connect(lambda: self.translated(roi))
        roi.translate_done.connect(lambda: self.translate_done(roi))
        #proxy= pg.SignalProxy(roi.translated,rateLimit=60, slot=self.redrawROIs)
        if len(self.rois)==0:
            self.region.setRegion([0, len(trace)-1])
        self.rois.append(dict({'roi':roi,'p1trace':p1trace,'p2trace':p2trace,'toBeRedrawn':False,'toBeRedrawnFull':False}))
        #self.rois.append([roi,p1data,p2data,proxy])

    def addTrace(self, trace):
        p1trace=self.p1.plot(trace)
        p2trace=self.p2.plot(trace) 
        #proxy= pg.SignalProxy(roi.translated,rateLimit=60, slot=self.redrawROIs)
        if len(self.rois)==0:
            self.region.setRegion([0, len(trace)-1])
        #self.rois.append([roi,p1data,p2data,proxy])

    def removeROI(self,roi):
        index=[r['roi'] for r in self.rois].index(roi) #this is the index of the roi in self.rois
        self.p1.removeItem(self.rois[index]['p1trace'])
        self.p2.removeItem(self.rois[index]['p2trace'])
        self.rois[index]['roi'].translated.disconnect()
        self.rois[index]['roi'].translate_done.disconnect()
        del self.rois[index]
        if len(self.rois)==0:
            self.close()
            
    def hasROI(self,roi):
        return roi in [r['roi'] for r in self.rois] #return True if roi is plotted
    def export_gui(self):
        filename=g.m.settings['filename']
        directory=os.path.dirname(filename)
        if filename is not None:
            filename= QFileDialog.getSaveFileName(g.m, 'Save Traces', directory, '*.txt')
        else:
            filename= QFileDialog.getSaveFileName(g.m, 'Save Traces', '*.txt')
        filename=str(filename)
        if filename=='':
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
        
def roiPlot(roi):
    if g.m.settings['multipleTraceWindows'] or g.m.currentTrace is None:
        TraceFig()
    g.m.currentTrace.addROI(roi)
    
class RedrawPartialThread(QThread):
    finished=Signal(float)
    def __init__(self,tracefig):
        QThread.__init__(self)
        self.tracefig=tracefig
    def run(self):
        tic=time.time()
        pts=[]
        idxs=[]
        for i in np.arange(len(self.tracefig.rois)):
            pts.append(self.tracefig.rois[i]['roi'].getPoints())
        for i in np.arange(len(self.tracefig.rois)):
            if self.tracefig.rois[i]['toBeRedrawn']:
                self.tracefig.rois[i]['toBeRedrawn']=False
                idxs.append(i)
        traces=[]
        for i in idxs:
            trace=self.tracefig.rois[i]['roi'].getTrace(self.tracefig.getBounds(),pts[i])
            traces.append(trace)
        for i, idx in enumerate(idxs):
            self.tracefig.update_trace_partial(idx,traces[i]) #This function can sometimes take a long time.  
        toc=time.time()-tic
        self.finished.emit(toc)
        return

class RedrawFullThread(QThread):
    started=Signal()
    finished=Signal(float)
    def __init__(self,tracefig,roi):
        QThread.__init__(self)
        self.tracefig=tracefig
        self.roi=roi
    def run(self):
        self.started.emit()
        tic=time.time()
        pts=[]
        idxs=[]
        for i in np.arange(len(self.tracefig.rois)):
            pts.append(self.tracefig.rois[i]['roi'].getPoints())
        for i in np.arange(len(self.tracefig.rois)):
            if self.tracefig.rois[i]['toBeRedrawnFull']:
                self.tracefig.rois[i]['toBeRedrawnFull']=False
                idxs.append(i)
        traces=[]
        for i in idxs:
            trace=self.tracefig.rois[i]['roi'].getTrace(pts=pts[i])
            traces.append(trace)
        for i, idx in enumerate(idxs):
            self.tracefig.update_trace_full(idx,traces[i]) #This function can sometimes take a long time.  
        toc=time.time()-tic
        self.finished.emit(toc)
        return
    