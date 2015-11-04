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
from PropertiesWidget import ParameterEditor

from histogram import Histogram
from process.motility_ import open_bin_gui, create_main_data_struct, bin2mat
from process.file_ import open_gui, open_file_gui, save_file_gui

try:
	os.chdir(os.path.split(os.path.realpath(__file__))[0])
except NameError:
	pass


def import_coords():
	filename = open_file_gui(prompt='Import coordinates from txt file', filetypes='*.txt')
	headers = open(filename, 'r').readline().split('\t')
	pe = ParameterEditor('Coordinate Columns', [{'name': 'X Column', 'value': headers}, {'name': 'Y Column', 'value': headers}])
	pe.done.connect(lambda d: add_coords(np.loadtxt(filename, columns=[headers.index(d['X Column']), headers.index(d['Y Column'])])))

def add_coords(arr):
	print(arr)

def export_distances():
	filename = save_file_gui(prompt='Export Distances', filetypes='*.txt')
	np.savetxt(filename, TrackPlot.plot_data)

class TrackPlot(pg.PlotDataItem):
	'''
	PlotDataItem representation of a set of tracks, imported from a bin file.
	Filterable by track length, mean lag distance, and neighbor points

	'''
	tracksChanged = Signal()
	def __init__(self, *args, **kargs):
		super(TrackPlot, self).__init__()
		self.all_tracks = []
		self.filtered_tracks = []
		self.waitForUpdate = False

	def setTracks(self, track_list):
		self.all_tracks = track_list
		self.filter()

	def filter(self):
		if self.waitForUpdate:
			return
		self.filtered_tracks = []
		for tr in self.all_tracks:
			if isValidTrack(tr):
				self.filtered_tracks.append(tr)
		self._replot()
		self.tracksChanged.emit()

	def _replot(self):
		tracks_x = []
		tracks_y = []
		connect_list = []
		for tr in self.filtered_tracks:
			tracks_x.extend(tr.x_cor)
			tracks_y.extend(tr.y_cor)
			connect_list.extend([1] * (len(tr.x_cor) - 1) + [0])
		g.m.trackView.imageview.setImage(np.zeros((max(tracks_x), max(tracks_y))))
		self.setData(x=tracks_x, y=tracks_y, connect=np.array(connect_list))

	def export(filename, filtered=False):
		pass

def isValidTrack(track):
	if g.m.MLDMinimumSpin.value() <= track.mean_dis_pixel_lag <= g.m.MLDMaximumSpin.value():
		if all([v <= g.m.neighborDistanceSpin.value() for v in track.dis_pixel_lag]):
			if g.m.minLengthSpin.value() <= track.fr_length <= g.m.maxLengthSpin.value():
				if not g.m.ignoreOutsideCheck.isChecked() or track_in_roi(track):
					return True

def simulate_means():
	pass

def exportMSD():
	pass

def import_mat(mat):
	if len(mat) == 0:
		return
	main, reject, r = create_main_data_struct(mat, g.m.minLengthSpin.value(), g.m.maxLengthSpin.value())
	g.m.trackPlot.waitForUpdate = True
	g.m.minLengthSpin.setValue(0)
	g.m.maxLengthSpin.setValue(max([tr.fr_length for tr in main]))
	g.m.MLDMinimumSpin.setValue(0)
	g.m.MLDMaximumSpin.setValue(max([tr.mean_dis_pixel_lag for tr in main]))
	g.m.neighborDistanceSpin.setValue(max([max(track.dis_pixel_lag) for track in main]))
	g.m.trackPlot.waitForUpdate = False
	g.m.trackPlot.setTracks(main)

def track_in_roi(track):
	for roi in g.m.currentWindow.rois:
		if roi.contains(track):
			return True
	return False

def initializeMainGui():
	g.init('gui/MotilityTracking.ui')
	g.m.settings['mousemode'] = 'freehand'
	g.widgetCreated = lambda : None
	g.m.trackView = Window(np.zeros((3, 3, 3)))
	g.m.histogram = Histogram(title='Mean Single Lag Distance Histogram', labels={'left': 'Count', 'bottom': 'Mean SLD Per Track (Pixels)'})
	g.m.trackPlot = TrackPlot()
	g.m.trackView.imageview.addItem(g.m.trackPlot)

	g.m.actionImportBin.triggered.connect(lambda : import_mat(open_bin_gui()))
	g.m.actionImportBackground.triggered.connect(open_gui)
	g.m.actionImportCoordinates.triggered.connect(import_coords)
	g.m.actionSimulateDistances.triggered.connect(simulate_means)
	g.m.actionExportMSD.triggered.connect(exportMSD)
	g.m.actionExportHistogram.triggered.connect(g.m.histogram.export)
	g.m.actionExportOutlined.triggered.connect(lambda : g.m.trackPlot.export(filtered=True))
	g.m.actionExportDistances.triggered.connect(export_distances)

	g.m.MLDMaximumSpin.valueChanged.connect(g.m.trackPlot.filter)
	g.m.MLDMinimumSpin.valueChanged.connect(g.m.trackPlot.filter)
	g.m.neighborDistanceSpin.valueChanged.connect(g.m.trackPlot.filter)
	g.m.minNeighborsSpin.valueChanged.connect(g.m.trackPlot.filter)
	g.m.minLengthSpin.valueChanged.connect(g.m.trackPlot.filter)
	g.m.maxLengthSpin.valueChanged.connect(g.m.trackPlot.filter)
	g.m.hideBackgroundCheck.toggled.connect(lambda v: g.m.trackView.imageitem.setVisible(v))
	g.m.ignoreOutsideCheck.toggled.connect(g.m.trackPlot.filter)

	g.m.viewTab.layout().insertWidget(0, g.m.trackView)

	g.m.MSDWidget = pg.PlotWidget(title='Mean Squared Displacement Per Lag', labels={'left': 'Mean Squared Disance (p^2)', 'bottom': 'Lag Count'})
	g.m.MSDPlot = pg.PlotDataItem()
	g.m.MSDWidget.addItem(g.m.MSDPlot)
	g.m.analysisTab.layout().addWidget(g.m.MSDWidget)
	
	g.m.analysisTab.layout().addWidget(g.m.histogram)

	g.m.CDFWidget = pg.PlotWidget(title = 'Cumulative Distribution Function', labels={'left': 'Cumulative Probability', 'bottom': 'Single Lag Displacement Squared'})
	g.m.CDFPlot = pg.PlotCurveItem()
	g.m.cdfTab.layout().addWidget(g.m.CDFWidget)

	g.m.installEventFilter(mainWindowEventEater)
	g.m.setWindowTitle('Motility Tracking')
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
				import_mat(bin2mat(filename))  #This fails on windows symbolic links.  http://stackoverflow.com/questions/15258506/os-path-islink-on-windows-with-python
				event.accept()
			else:
				event.ignore()
		return False # lets the event continue to the edit
mainWindowEventEater = MainWindowEventEater()

if __name__ == '__main__':
	app = QApplication(sys.argv)
	initializeMainGui()
	
	insideSpyder='SPYDER_SHELL_ID' in os.environ
	if not insideSpyder: #if we are running outside of Spyder
		sys.exit(app.exec_()) #This is required to run outside of Spyder
	
	
	
	
	
	
	
	
	