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
from window3d import Window3D

try:
	os.chdir(os.path.split(os.path.realpath(__file__))[0])
except NameError:
	pass

from process.dbscan_ import cluster, save_scatter, save_clusters, export_distances, export_nearest_distances, load_scatter_gui, save_scatter_gui, getSaveFilename

EPSILON = 30
MIN_POINTS = 10
MIN_NEIGHBORS = 1


def initializeMainGui():
	g.init('gui/DBScan.ui')

	g.m.setGeometry(QRect(15, 33, 326, 80))
	
	g.m.actionCluster.triggered.connect(cluster.gui)
	g.m.actionOpen.triggered.connect(load_scatter_gui)
	g.m.actionSave_Scatter.triggered.connect(save_scatter_gui)
	g.m.actionSave_Clusters.triggered.connect(lambda : save_clusters(getSaveFilename('Export Clusters', '*.txt')))
	g.m.openButton.clicked.connect(load_scatter_gui)
	g.m.saveButton.clicked.connect(save_scatter_gui)
	g.m.saveClustersButton.clicked.connect(lambda : save_clusters(getSaveFilename('Export Clusters', '*.txt')))
	g.m.exportAllDistancesButton.clicked.connect(lambda : export_distances(getSaveFilename('Export distances...', '*.txt')))
	g.m.exportNearestButton.clicked.connect(lambda : export_nearest_distances(getSaveFilename('Export nearest distances', '*.txt')))
	g.m.clusterButton.clicked.connect(lambda : cluster(g.m.epsilonSpin.value(), g.m.minPointsSpin.value(), g.m.minNeighborsSpin.value()))
	
	g.m.epsilonSpin.setValue(EPSILON)
	g.m.minPointsSpin.setValue(MIN_POINTS)
	g.m.minNeighborsSpin.setValue(MIN_NEIGHBORS)

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
				load_scatter_gui(filename)  #This fails on windows symbolic links.  http://stackoverflow.com/questions/15258506/os-path-islink-on-windows-with-python
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
	
	
	
	
	
	
	
	
	