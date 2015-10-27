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
import numpy as np
from PyQt4.QtCore import * # Qt is Nokias GUI rendering code written in C++.  PyQt4 is a library in python which binds to Qt
from PyQt4.QtGui import *
from PyQt4.QtCore import pyqtSignal as Signal
from pyqtgraph import plot, show
import pyqtgraph as pg
import global_vars as g
from window import Window
from window3d import Window3D
from roi import load_roi_gui, load_roi, makeROI

from histogram import Histogram
from process.motility_ import open_bin_gui
from process.file_ import open_gui

try:
	os.chdir(os.path.split(os.path.realpath(__file__))[0])
except NameError:
	pass


def import_coords():
	pass

def export_distances():
	pass

class TrackPlot(pg.PlotDataItem):
	'''
	PlotDataItem representation of a set of tracks, imported from a bin file.
	Filterable by track length, mean lag distance, and neighbor points

	'''
	def __init__(self, *args, **kargs):
		tracksChanged = Signal()
		super(TrackPlot, self).__init__(*args, **kargs)
		self.all_tracks = []
		self.filtered_tracks = []


	def setTracks(self, track_list):
		self.tracks = track_list


	def filter(**kargs):
		self.filtered_tracks = []
		for tr in self.all_tracks:
			if 'MLD_Minimum' in kargs:
				pass
			if 'MLD_Maximum' in kargs:
				pass
			if 'Neighbor_Distance' in kargs:
				pass
			if 'Minimum_Neighbors' in kargs:
				pass
			if 'Minimum_Track_Length' in kargs:
				pass
			if 'Maximum_Track_Length' in kargs:
				pass
			if 'func' in kargs:
				pass

		self.tracksChanged.emit()

	def export(filtered=False):
		pass

def simulateMeans():
	pass

def exportMSD():
	pass

def track_in_roi(track):
	for roi in g.m.currentWindow.rois:
		if roi.contains(track):
			return True
	return False

def initializeMainGui():
	g.init('gui/MotilityTracking.ui')

	g.m.trackView = Window(np.zeros((3, 3, 3)))
	g.m.histogram = Histogram()
	g.m.trackPlot = TrackPlot()

	g.m.actionImportBin.triggered.connect(open_bin_gui)
	g.m.actionImportBackground.triggered.connect(open_gui)
	g.m.actionImportCoordinates.triggered.connect(import_coords)
	g.m.actionSimulateDistances.triggered.connect(simulateMeans)
	g.m.actionExportMSD.triggered.connect(exportMSD)
	g.m.actionExportHistogram.triggered.connect(g.m.histogram.export)
	g.m.actionExportOutlined.triggered.connect(lambda : g.m.trackPlot.export(filtered=True))
	g.m.actionExportDistances.triggered.connect(export_distances)

	g.m.MLDMaximumSpin.valueChanged.connect(lambda v: g.m.trackPlot.filter(MLD_Minimum=v))
	g.m.MLDMinimumSpin.valueChanged.connect(lambda v: g.m.trackPlot.filter(MLD_Maximum=v))
	g.m.neighborDistanceSpin.valueChanged.connect(lambda v: g.m.trackPlot.filter(Neighbor_Distance=v))
	g.m.minNeighborsSpin.valueChanged.connect(lambda v: g.m.trackPlot.filter(Minimum_Neighbors=v))
	g.m.minLengthSpin.valueChanged.connect(lambda v: g.m.trackPlot.filter(Minimum_Track_Length=v))
	g.m.maxLengthSpin.valueChanged.connect(lambda v: g.m.trackPlot.filter(Maximum_Track_Length=v))
	g.m.hideBackgroundCheck.toggled.connect(lambda v: g.m.trackView.imageitem.setVisible(v))
	g.m.ignoreOutsideCheck.toggled.connect(lambda v: g.m.trackPlot.filter(func=track_in_roi))

	g.m.viewTab.layout().insertWidget(0, g.m.trackView)

	g.m.MSDWidget = pg.PlotWidget()
	g.m.MSDPlot = pg.PlotDataItem()
	g.m.MSDWidget.addItem(g.m.MSDPlot)
	g.m.analysisTab.layout().addWidget(g.m.MSDWidget)

	
	g.m.analysisTab.layout().addWidget(g.m.histogram)

	g.m.CDFWidget = pg.PlotWidget()
	g.m.CDFPlot = pg.PlotCurveItem()
	g.m.cdfTab.layout().addWidget(g.m.CDFWidget)

	g.m.show()

if __name__ == '__main__':
	app = QApplication(sys.argv)
	initializeMainGui()
	
	insideSpyder='SPYDER_SHELL_ID' in os.environ
	if not insideSpyder: #if we are running outside of Spyder
		sys.exit(app.exec_()) #This is required to run outside of Spyder
	
	
	
	
	
	
	
	
	