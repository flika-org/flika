# -*- coding: utf-8 -*-
"""
Created on Thu Jun 26 14:17:38 2014
updated 2015.01.27
@author: Kyle Ellefsen
"""
from __future__ import (absolute_import, division,print_function, unicode_literals)
import dependency_check
from future.builtins import (bytes, dict, int, list, object, range, str, ascii, chr, hex, input, next, oct, open, pow, round, super, filter, map, zip)
import time
tic=time.time()
import os, sys
sys.path.insert(0, "C:/Users/Kyle Ellefsen/Documents/GitHub/pyqtgraph")
sys.path.insert(0, "C:/Users/Medha/Documents/GitHub/pyqtgraph")
import numpy as np
from PyQt4.QtCore import * # Qt is Nokias GUI rendering code written in C++.  PyQt4 is a library in python which binds to Qt
from PyQt4.QtGui import *
from PyQt4.QtCore import pyqtSignal as Signal
from pyqtgraph import plot, show
import pyqtgraph as pg
from scripts import getScriptList
from roi import load_roi_gui, load_roi, makeROI, ROI_rectangle, ROI
import global_vars as g
from window import Window

from process.file_ import open_gui, save_as_gui, open_file, load_metadata, close, save_file, save_movie_gui, save_movie, change_internal_data_type, change_internal_data_type_gui, save_points_gui, load_points_gui
from process.stacks import deinterleave, slicekeeper, zproject, image_calculator, pixel_binning, frame_binning
from process.math_ import multiply, subtract, power, ratio, absolute_value, subtract_trace
from process.filters import gaussian_blur, butterworth_filter,boxcar_differential_filter, wavelet_filter, difference_filter, fourier_filter, mean_filter
from process.binary import threshold, adaptive_threshold, canny_edge_detector, remove_small_blobs, logically_combine, binary_dilation, binary_erosion
from process.roi import set_value
from analyze.measure import measure
from analyze.puffs.frame_by_frame_origin import frame_by_frame_origin
from analyze.puffs.average_origin import average_origin
from analyze.puffs.threshold_cluster import threshold_cluster

from process.overlay import time_stamp,background, scale_bar
from pyqtgraph.dockarea import *
from trace import TraceFig

from GlobalPolyfit import ROIRange, get_polyfit, analyze_trace, makePolyPath

try:
    os.chdir(os.path.split(os.path.realpath(__file__))[0])
except NameError:
    pass
 
def showImageTrace(window):
    if g.m.currentWindow == None:
        return
    tf = TraceFig()
    tf.addTrace(np.average(g.m.currentWindow.image, (2, 1)))
    tf.indexChanged.connect(g.m.currentWindow.imageview.setCurrentIndex)
    return

def export_roi_traces():
    filename=g.m.settings['filename']
    directory=os.path.dirname(filename)
    if filename is not None and directory != '':
        filename= QFileDialog.getSaveFileName(g.m, 'Save ROI Traces', directory, '*.txt')
    else:
        filename= QFileDialog.getSaveFileName(g.m, 'Save ROI Traces', '*.txt')
    filename=str(filename)
    if filename=='':
        return False
    to_save = [roi.getTrace() for roi in g.m.currentWindow.rois]
    np.savetxt(filename, np.transpose(to_save), header='\t'.join(['ROI %d' % i for i in range(len(to_save))]), fmt='%.4f', delimiter='\t', comments='')
    g.m.settings['filename'] = filename


def initializeMainGui():
    g.init('gui/GlobalAnalysis.ui')
    g.m.setWindowTitle('Global Cell Analysis')
    g.m.setGeometry(QRect(15, 33, 100, 140))

    g.m.actionOpen.triggered.connect(open_gui)
    g.m.actionSave_Movie.triggered.connect(save_movie_gui)
    g.m.actionSaveAs.triggered.connect(save_as_gui)
    g.m.actionChange_Internal_Data_type.triggered.connect(change_internal_data_type_gui)

    g.m.actionImport_ROI_File.triggered.connect(load_roi_gui)
    g.m.actionExport_ROIs.triggered.connect(lambda : g.m.currentWindow.rois[0].save_gui() if len(g.m.currentWindow.rois) > 0 else None)
    g.m.actionExport_ROI_Traces.triggered.connect(export_roi_traces)
    g.m.actionSave_Points.triggered.connect(save_points_gui)
    g.m.actionLoad_Points.triggered.connect(load_points_gui)
    g.m.actionSubtract.triggered.connect(subtract.gui)
    g.m.actionRatio.triggered.connect(ratio.gui)
    g.m.actionSubtract_Trace.triggered.connect(subtract_trace.gui)
    g.m.actionAbsolute_Value.triggered.connect(absolute_value.gui)
    g.m.menuScripts.aboutToShow.connect(getScriptList)
    
    g.m.openButton.clicked.connect(open_gui)
    g.m.saveButton.clicked.connect(save_movie_gui)
    g.m.subtractButton.clicked.connect(subtract.gui)
    g.m.ratioButton.clicked.connect(ratio.gui)

    g.m.freehandButton.clicked.connect(lambda: g.m.settings.setmousemode('freehand'))
    g.m.lineButton.clicked.connect(lambda: g.m.settings.setmousemode('line'))
    g.m.rectangleButton.clicked.connect(lambda: g.m.settings.setmousemode('rectangle'))
    g.m.pointButton.clicked.connect(lambda: g.m.settings.setmousemode('point'))
    g.m.importROIButton.clicked.connect(load_roi_gui)
    g.m.exportROIButton.clicked.connect(lambda : g.m.currentWindow.rois[0].save_gui() if len(g.m.currentWindow.rois) > 0 else None)
    g.m.plotAllButton.clicked.connect(lambda : [roi.plot() for roi in g.m.currentWindow.rois[:]])
    g.m.clearButton.clicked.connect(lambda : [roi.delete() for roi in g.m.currentWindow.rois[:]])
    g.m.newWindowCheck.toggled.connect(g.m.settings.setMultipleTraceWindows)

    g.m.lineMeasureButton.clicked.connect(measure.gui)
    g.m.showTraceButton.clicked.connect(showImageTrace)
    g.m.closeButton.clicked.connect(lambda : [w.close() for w in g.m.windows])
    g.m.exitButton.clicked.connect(g.m.close)
    
    g.m.settings.setmousemode('rectangle')
    g.m.menuScripts.aboutToShow.connect(getScriptList)
    #url='file:///'+os.path.join(os.getcwd(),'docs','_build','html','index.html')
    #g.m.actionDocs.triggered.connect(lambda: QDesktopServices.openUrl(QUrl(url)))
    g.m.setAcceptDrops(True)


    g.m.outlineCheck.toggled.connect(setIsoVisible)
    g.m.autoROIButton.clicked.connect(makeROIs)
    g.m.installEventFilter(mainWindowEventEater)
    g.m.show()

class MainWindowEventEater(QObject):
    def __init__(self,parent=None):
        QObject.__init__(self,parent)
    def eventFilter(self,obj,event):
        if (event.type()==QEvent.DragEnter):
            if event.mimeData().hasUrls():
                event.accept()   # must accept the dragEnterEvent or else the dropEvent can't occur !!!
            else:
                event.ignore()
        if (event.type() == QEvent.Drop):
            if event.mimeData().hasUrls():   # if file or link is dropped
                url = event.mimeData().urls()[0]   # get first url
                filename=url.toString()
                filename=filename.split('file:///')[1]
                print('filename={}'.format(filename))
                open_file(filename)  #This fails on windows symbolic links.  http://stackoverflow.com/questions/15258506/os-path-islink-on-windows-with-python
                event.accept()
            else:
                event.ignore()
        return False # lets the event continue to the edit
mainWindowEventEater = MainWindowEventEater()

def makeROIs():
    length = int(g.m.currentWindow.iso.path.length())
    p = g.m.currentWindow.iso.path.pointAtPercent(0)
    p = (p.x(), p.y())
    last_p = p
    cur_roi = ROI(g.m.currentWindow, p[0], p[1])
    for i in range(1, length):
        p = g.m.currentWindow.iso.path.pointAtPercent(i / length)
        p = (p.x(), p.y())
        if np.linalg.norm((last_p[0] - p[0], last_p[1] - p[1])) > 2:
            cur_roi.drawFinished()
            cur_roi = ROI(g.m.currentWindow, p[0], p[1])
        else:
            cur_roi.extend(p[0], p[1])
        last_p = p
    cur_roi.drawFinished()

def add_polyfit_item(traceWidget):
    rangeItem = ROIRange()
    traceWidget.p1.addItem(rangeItem)
    rangeItem.__name__ = "%s Range %d" % (traceWidget.name, rangeItem.id)

    rangeItem.poly_pen = QPen(QColor(255, 0, 0))
    rangeItem.poly_pen.setStyle(Qt.DashLine)
    rangeItem.poly_pen.setDashOffset(5)
    #traceWidget.p1.menu.addMenu(rangeItem.menu)
    #rangeItem.sigRemoved.connect(lambda : traceWidget.rangeMenu.removeAction(rangeItem.menu.menuAction()))

    rangeItem.poly_fill = QGraphicsPathItem()
    rangeItem.poly_fill.setBrush(QColor(0, 100, 155, 100))
    rangeItem.polyfit_item = pg.PlotDataItem(pen=rangeItem.poly_pen)
    rangeItem.fall_rise_points = pg.ScatterPlotItem()

    rangeItem.poly_fill.setParentItem(rangeItem)
    rangeItem.polyfit_item.setParentItem(rangeItem)
    rangeItem.fall_rise_points.setParentItem(rangeItem)
    rangeItem.sigRegionChangeFinished.connect(lambda : onRegionMove(rangeItem))
    onRegionMove(rangeItem)

def onRegionMove(region):
    ''' when the region moves, recalculate the polyfit
    data and plot/show it in the table and graph accordingly'''
    x, y = region.getRegionTrace()
    ftrace = get_polyfit(x, y)
    data = analyze_trace(x, y, ftrace)
    region.polyfit_item.setData(x=x, y=ftrace, pen=region.poly_pen)
    integral = region.getIntegral()

    pos = [data[k] for k in data.keys() if k.startswith('Rise, Fall')]
    if len(pos) > 0:
        region.fall_rise_points.setData(pos=pos, pen=region.poly_pen, symbolSize=4)
    else:
        print("Cannot find points")
        region.fall_rise_points.clear()
    region.poly_fill.setPath(makePolyPath(x, ftrace, data['Baseline'][1]))
    if not hasattr(region, 'table_widget'):
        region.table_widget = pg.TableWidget()
        region.table_widget.__name__ = '%s Polyfit Table' % region.__name__
        g.m.currentTrace.l.addWidget(region.table_widget)
        region.sigRemoved.connect(region.table_widget.close)
    region.table_widget.setData(data)
    region.table_widget.setHorizontalHeaderLabels(['Frames', 'Y'])

def traceShow(widg):
    addButton = QPushButton('Add Polyfit Region')
    addButton.clicked.connect(lambda : add_polyfit_item(widg))
    widg.l.addWidget(addButton, 1)
    addButton.setMaximumWidth(100)
    QWidget.show(widg)
TraceFig.show = traceShow

def setIsoVisible(v):
    if not hasattr(g.m.currentWindow, 'iso'):
        if isinstance(g.m.currentWindow, Window):
            addIsoCurve(g.m.currentWindow)
    if g.m.currentWindow != None and hasattr(g.m.currentWindow, 'iso'):
        g.m.currentWindow.iso.setVisible(v)
        g.m.currentWindow.isoLine.setVisible(v)

def addIsoCurve(widg):
    lut = widg.imageview.getHistogramWidget().centralWidget
    widg.iso = pg.IsocurveItem(level=0.8, pen='g')
    widg.iso.setParentItem(widg.imageview.getImageItem())
    widg.iso.setZValue(5)
    widg.isoLine = pg.InfiniteLine(angle=0, movable=True, pen='g')
    lut.vb.addItem(widg.isoLine)
    #lut.vb.setMouseEnabled(y=False) # makes user interaction a little easier
    widg.isoLine.setValue(np.average(lut.getLevels()))
    widg.isoLine.setZValue(1000)
    widg.iso.setData(pg.gaussianFilter(widg.image[widg.currentIndex], (2, 2)))
    def updateIsocurve():
        widg.iso.setLevel(widg.isoLine.value())
    updateIsocurve()
    setIsoVisible(False)

    widg.isoLine.sigDragged.connect(updateIsocurve)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    initializeMainGui()
    
    
    insideSpyder='SPYDER_SHELL_ID' in os.environ
    if not insideSpyder: #if we are running outside of Spyder
        sys.exit(app.exec_()) #This is required to run outside of Spyder