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
import global_vars as g
from window import Window
from window3d import Window3D
from PyQt4 import uic

from process.stacks import deinterleave, cropper, zproject, image_calculator, pixel_binning, frame_binning, average_movie, average_trace
from process.math_ import multiply, subtract, power, ratio, absolute_value, subtract_trace
from process.filters import gaussian_blur, butterworth_filter,boxcar_differential_filter, wavelet_filter, difference_filter, fourier_filter, mean_filter
from process.binary import threshold, adaptive_threshold, canny_edge_detector, remove_small_blobs, logically_combine, binary_dilation, binary_erosion
from process.roi import set_value
from analyze.measure import measure
from analyze.puffs.frame_by_frame_origin import frame_by_frame_origin
from analyze.puffs.average_origin import average_origin
from analyze.puffs.threshold_cluster import threshold_cluster
from process.file_ import open_file_gui, save_file_gui, open_file, load_metadata, close, save_file, save_movie, change_internal_data_type_gui, save_points, load_points, save_current_frame, save_roi_traces
from roi import load_roi, makeROI, ROI
from process.overlay import time_stamp,background, scale_bar
from scripts import getScriptList
from trace import TraceFig

from GlobalPolyfit import ROIRange, get_polyfit, analyze_trace, makePolyPath

try:
    os.chdir(os.path.split(os.path.realpath(__file__))[0])
except NameError:
    pass

def initializeMainGui():
    g.init('gui/main.ui')
    g.m.setGeometry(QRect(15, 33, 326, 80))

    g.m.actionOpen.triggered.connect(lambda : open_file_gui(open_file, prompt='Open File', filetypes='*.tif *.stk *.tiff'))
    g.m.actionExportTif.triggered.connect(lambda : save_file_gui(save_file, prompt='Save File As Tif', filetypes='*.tif'))
    g.m.actionExportMp4.triggered.connect(lambda : save_file_gui(save_movie, prompt='Save File as MP4', filetypes='*.mp4'))
    g.m.actionExportCurrentFrame.triggered.connect(lambda : save_file_gui(save_current_frame, prompt='Save Current Frame', filetypes='*.tif'))
    g.m.actionExport_ROI_Traces.triggered.connect(lambda : save_file_gui(save_roi_traces, prompt='Save ROI Traces to File', filetypes='*.txt'))

    g.m.actionExportPoints.triggered.connect(lambda : save_file_gui(save_points, prompt='Save Points', filetypes='*.txt'))
    g.m.actionImportPoints.triggered.connect(lambda : open_file_gui(load_points, prompt='Load Points', filetypes='*.txt'))
    g.m.actionImportROIs.triggered.connect(lambda : open_file_gui(load_roi, prompt='Load ROIs from file', filetypes='*.txt'))
    g.m.actionChange_Internal_Data_type.triggered.connect(change_internal_data_type_gui)

    g.m.actionClose.triggered.connect(lambda : [w.close() for w in g.m.windows])
    g.m.actionExit.triggered.connect(g.m.close)

    g.m.openButton.clicked.connect(lambda : open_file_gui(open_file, prompt='Open File', filetypes='*.tif *.stk *.tiff'))
    g.m.saveTifButton.clicked.connect(lambda : save_file_gui(save_file, prompt='Save File As Tif', filetypes='*.tif'))
    g.m.saveMp4Button.clicked.connect(lambda : save_file_gui(save_movie, prompt='Save File as MP4', filetypes='*.mp4'))
    g.m.closeButton.clicked.connect(lambda : [w.close() for w in g.m.windows()])
    g.m.exitButton.clicked.connect(g.m.close)
    
    g.m.measureButton.clicked.connect(measure.gui)
    g.m.subtractButton.clicked.connect(subtract.gui)
    g.m.ratioButton.clicked.connect(ratio.gui)
    g.m.cropButton.clicked.connect(cropper.gui)
    g.m.averageButton.clicked.connect(average_movie)
    g.m.actionAverage_Frame.triggered.connect(average_movie)
    g.m.actionAverage_Trace.triggered.connect(average_trace)

    g.m.exportTracesButton.clicked.connect(lambda : save_file_gui(save_roi_traces, prompt='Save ROI Traces to File', filetypes='*.txt'))
    g.m.importROIButton.clicked.connect(lambda : open_file_gui(load_roi, prompt='Load ROIs from file', filetypes='*.txt'))
    g.m.exportROIButton.clicked.connect(lambda : save_file_gui(g.m.currentWindow.rois[0].save, prompt='Save ROIs to File', filetypes='*.txt') if len(g.m.currentWindow.rois) > 0 else None)
    g.m.plotAllButton.clicked.connect(lambda : [roi.plot() for roi in g.m.currentWindow.rois])
    g.m.clearButton.clicked.connect(lambda : [roi.delete() for roi in g.m.currentWindow.rois])
    g.m.actionMultiple_Trace_Windows.toggled.connect(g.m.settings.setMultipleTraceWindows)
    g.m.freehand.clicked.connect(lambda: g.m.settings.setmousemode('freehand'))
    g.m.line.clicked.connect(lambda: g.m.settings.setmousemode('line'))
    g.m.rectangle.clicked.connect(lambda: g.m.settings.setmousemode('rectangle'))
    g.m.point.clicked.connect(lambda: g.m.settings.setmousemode('point'))

    g.m.menuScripts.aboutToShow.connect(getScriptList)

    url='file:///'+os.path.join(os.getcwd(),'docs','_build','html','index.html')
    g.m.actionDocs.triggered.connect(lambda: QDesktopServices.openUrl(QUrl(url)))
    
    g.m.actionDeinterleave.triggered.connect(deinterleave.gui)
    g.m.actionZ_Project.triggered.connect(zproject.gui)
    g.m.actionPixel_Binning.triggered.connect(pixel_binning.gui)
    g.m.actionFrame_Binning.triggered.connect(frame_binning.gui)
    g.m.actionCrop_Frames.triggered.connect(cropper.gui)
    g.m.actionMultiply.triggered.connect(multiply.gui)
    g.m.actionSubtract.triggered.connect(subtract.gui)
    g.m.actionPower.triggered.connect(power.gui)
    g.m.actionGaussian_Blur.triggered.connect(gaussian_blur.gui)
    g.m.actionButterworth_Filter.triggered.connect(butterworth_filter.gui)
    g.m.actionMean_Filter.triggered.connect(mean_filter.gui)
    g.m.actionFourier_Filter.triggered.connect(fourier_filter.gui)
    g.m.actionDifference_Filter.triggered.connect(difference_filter.gui)
    g.m.actionBoxcar_Differential.triggered.connect(boxcar_differential_filter.gui)
    g.m.actionWavelet_Filter.triggered.connect(wavelet_filter.gui)
    g.m.actionRatio_by_Baseline.triggered.connect(ratio.gui)
    g.m.actionSubtract_Trace.triggered.connect(subtract_trace.gui)
    g.m.actionAbsolute_Value.triggered.connect(absolute_value.gui)
    g.m.actionThreshold.triggered.connect(threshold.gui)
    g.m.actionAdaptive_Threshold.triggered.connect(adaptive_threshold.gui)
    g.m.actionCanny_Edge_Detector.triggered.connect(canny_edge_detector.gui)
    g.m.actionLogically_Combine.triggered.connect(logically_combine.gui)
    g.m.actionRemove_Small_Blobs.triggered.connect(remove_small_blobs.gui)
    g.m.actionBinary_Erosion.triggered.connect(binary_erosion.gui)
    g.m.actionBinary_Dilation.triggered.connect(binary_dilation.gui)
    g.m.actionSet_Value.triggered.connect(set_value.gui)
    g.m.actionImage_Calculator.triggered.connect(image_calculator.gui)
    g.m.actionTimestamp.triggered.connect(time_stamp.gui)
    g.m.actionScale_Bar.triggered.connect(scale_bar.gui)
    g.m.actionBackground.triggered.connect(background.gui)
    g.m.actionMeasure.triggered.connect(measure.gui)

    global_toolbox = uic.loadUi('gui/GlobalAnalysis.ui')
    global_toolbox.addPolyButton.clicked.connect(lambda : None)
    global_toolbox.averageTraceButton.clicked.connect(average_trace)
    global_toolbox.autoROIButton.clicked.connect(makeROIs)
    global_toolbox.sliderCheck.toggled.connect(setIsoVisible)
    g.m.centralwidget.layout().insertWidget(3, global_toolbox)
    
    g.m.installEventFilter(mainWindowEventEater)
    g.m.show()

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
