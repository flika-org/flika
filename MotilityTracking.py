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

from process.stacks import deinterleave, slicekeeper, zproject, image_calculator, pixel_binning, frame_binning
from process.math_ import multiply, subtract, power, ratio, absolute_value, subtract_trace
from process.filters import gaussian_blur, butterworth_filter,boxcar_differential_filter, wavelet_filter, difference_filter, fourier_filter, mean_filter
from process.binary import threshold, adaptive_threshold, canny_edge_detector, remove_small_blobs, logically_combine, binary_dilation, binary_erosion
from process.roi import set_value
from analyze.measure import measure
from analyze.puffs.frame_by_frame_origin import frame_by_frame_origin
from analyze.puffs.average_origin import average_origin
from analyze.puffs.threshold_cluster import threshold_cluster
from process.file_ import open_gui, save_as_gui, open_file, load_metadata, close, save_file, save_movie_gui, save_movie, change_internal_data_type, change_internal_data_type_gui, save_points_gui, load_points_gui
from roi import load_roi_gui, load_roi, makeROI
from process.overlay import time_stamp,background, scale_bar
from scripts import getScriptList

try:
	os.chdir(os.path.split(os.path.realpath(__file__))[0])
except NameError:
	pass


def initializeMainGui():
	g.init('gui/MotilityTracking.ui')

	g.m.setGeometry(QRect(15, 33, 326, 80))

	g.m.actionOpen.triggered.connect(open_gui)    
	g.m.actionSaveAs.triggered.connect(save_as_gui)
	g.m.actionSave_Points.triggered.connect(save_points_gui)
	g.m.actionLoad_Points.triggered.connect(load_points_gui)
	g.m.actionSave_Movie.triggered.connect(save_movie_gui)
	g.m.actionLoad_ROI_File.triggered.connect(load_roi_gui)
	g.m.actionChange_Internal_Data_type.triggered.connect(change_internal_data_type_gui)

	g.m.openButton.clicked.connect(open_gui)
	g.m.saveButton.clicked.connect(save_movie_gui)
	g.m.saveAsButton.clicked.connect(save_as_gui)
	
	g.m.importROIButton.clicked.connect(load_roi_gui)
	g.m.exportROIButton.clicked.connect(lambda : g.m.currentWindow.rois[0].save_gui() if len(g.m.currentWindow.rois) > 0 else None)
	g.m.plotAllButton.clicked.connect(lambda : [roi.plot() for roi in g.m.currentWindow.rois])
	g.m.clearButton.clicked.connect(lambda : [roi.delete() for roi in g.m.currentWindow.rois])
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
	g.m.actionSlice_Keeper.triggered.connect(slicekeeper.gui)
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
	g.m.actionRatio.triggered.connect(ratio.gui)
	g.m.actionSubtract_Trace.triggered.connect(subtract_trace.gui)
	g.m.actionAbsolute_Value.triggered.connect(absolute_value.gui)
	g.m.actionThreshold.triggered.connect(threshold.gui)
	g.m.actionAdaptive_Threshold.triggered.connect(adaptive_threshold.gui)
	g.m.actionCanny_Edge_Detector.triggered.connect(canny_edge_detector.gui)
	g.m.actionLogically_Combine.triggered.connect(logically_combine.gui)
	g.m.actionRemove_Small_Blobs.triggered.connect(remove_small_blobs.gui)
	g.m.actionBinary_Erosion.triggered.connect(binary_erosion.gui)
	g.m.actionBinary_Dilation.triggered.connect(binary_dilation.gui)
	g.m.actionSet_value.triggered.connect(set_value.gui)
	g.m.actionImage_Calculator.triggered.connect(image_calculator.gui)    
	g.m.actionTime_Stamp.triggered.connect(time_stamp.gui)
	g.m.actionScale_Bar.triggered.connect(scale_bar.gui)
	g.m.actionBackground.triggered.connect(background.gui)
	g.m.actionMeasure.triggered.connect(measure.gui)    
	g.m.actionFrame_by_frame_origin.triggered.connect(frame_by_frame_origin.gui)
	g.m.actionAverage_origin.triggered.connect(average_origin.gui)
	g.m.actionThreshold_cluster.triggered.connect(threshold_cluster.gui)
	

	g.m.show()

if __name__ == '__main__':
	app = QApplication(sys.argv)
	initializeMainGui()
	
	insideSpyder='SPYDER_SHELL_ID' in os.environ
	if not insideSpyder: #if we are running outside of Spyder
		sys.exit(app.exec_()) #This is required to run outside of Spyder
	
	
	
	
	
	
	
	
	