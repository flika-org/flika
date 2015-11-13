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
from collections import OrderedDict

class ROIRange(pg.LinearRegionItem):
	sigRemoved = Signal(object)
	def __init__(self, bounds = [0, 10]):
		super(ROIRange, self).__init__(bounds)
		self.id = 0
		self.__name__ = "ROI Range %d" % self.id
		self.lines[0].setPos = lambda pos : pg.InfiniteLine.setPos(self.lines[0], int(pos if isinstance(pos, (int, float)) else pos.x()))
		self.lines[1].setPos = lambda pos : pg.InfiniteLine.setPos(self.lines[1], int(pos if isinstance(pos, (int, float)) else pos.x()))
		self.setZValue(20)
		self._make_menu()

	def parentChanged(self):
		if self.parentWidget() != None:
			self.id = 1
			while any([roi.id == self.id for roi in self.getViewBox().items() if isinstance(roi, ROIRange) and roi != self]):
				self.id += 1
			self.__name__ = "ROI Range %d" % self.id
			self.menu.setTitle(self.__name__)
		super(ROIRange, self).parentChanged()

	def _make_menu(self):
		self.menu = QMenu(self.__name__)
		setMenu = self.menu.addMenu("Set Range to...")
		setMenu.addAction(QAction("&Average Value", self.menu, triggered=lambda : self.setTrace(np.average(self.getRegionTrace()[1]))))
		setMenu.addAction(QAction("&Enter Value", self.menu, triggered=lambda : self.setTrace(getFloat(self, "Setting Range Value", "What value would you like to set the region to?"))))
		self.menu.addAction(QAction("&Make Baseline", self.menu, triggered=lambda : self.setTrace(self.getTrace() / np.average(self.getRegionTrace()[1]), portion=False)))
		self.menu.addAction(QAction("&Remove", self.menu, triggered=self.delete))

	def contextMenuEvent(self, ev):
		ev.accept()
		self.menu.popup(ev.screenPos())

	def delete(self):
		self.parentItem().getViewBox().removeItem(self)
		self.sigRemoved.emit(self)

	def getRegionTrace(self):
		t = self.getTrace()
		x1, x2 = self.getRegion()
		x1 = int(x1)
		x1 = max(0, x1)
		x2 = int(x2)
		x2 = min(x2, len(t))
		return (np.arange(x1, x2+1), t[x1:x2 + 1])

	def getTrace(self):
		trace = [line for line in self.parentItem().getViewBox().addedItems if isinstance(line, pg.PlotDataItem)][0]
		return np.copy(trace.getData()[1])

	def setTrace(self, val, portion=True):
		trace = [line for line in self.parentItem().getViewBox().addedItems if isinstance(line, pg.PlotDataItem)][0]
		x1, x2 = self.getRegion()
		if portion:
			t = trace.getData()[1]
			t[x1:x2+1] = val
		else:
			t = val
		trace.setData(y=t)

	def getIntegral(self):
		x1, x2 = self.getRegion()
		y = self.getTrace()[x1:x2+1]
		return np.trapz(y)

def get_polyfit(x, y):
	np.warnings.simplefilter('ignore', np.RankWarning)
	poly=np.poly1d(np.polyfit(x, y, 20))
	ftrace=poly(x)
	return ftrace
def analyze_trace(x, y, ftrace):
	x_peak = np.argmax(y)
	f_peak = np.argmax(ftrace)
	data = OrderedDict([('Baseline', (x[0], y[0], x[0], ftrace[0])), ('Peak', (x_peak + x[0], y[x_peak], f_peak + x[0], ftrace[f_peak])),\
		('Delta Peak', (x_peak, y[x_peak]-y[0], f_peak, ftrace[f_peak] - ftrace[0]))])
	yRiseFall = getRiseFall(x, y)
	ftraceRiseFall = getRiseFall(x, ftrace)
	data.update(OrderedDict([(k, yRiseFall[k] + ftraceRiseFall[k]) for k in yRiseFall.keys()]))
	return data

def getRiseFall(x, y):
	x_peak = np.where(y == max(y))[0][0]
	baseline = (x[0], y[0])
	dPeak = (x_peak, y[x_peak]-y[0])
	data = OrderedDict([('Rise 20%', [-1, -1]),
		('Rise 50%', [-1, -1]), ('Rise 80%', [-1, -1]),
		('Rise 100%', [-1, -1]), ('Fall 80%', [-1, -1]),
		('Fall 50%', [-1, -1]), ('Fall 20%', [-1, -1])])
	try:
		thresh20=dPeak[1]*.2 + baseline[1]
		thresh50=dPeak[1]*.5 + baseline[1]
		thresh80=dPeak[1]*.8 + baseline[1]

		data['Rise 20%'] = [np.argwhere(y>thresh20)[0][0], thresh20]
		data['Rise 50%'] = [np.argwhere(y>thresh50)[0][0], thresh50]
		data['Rise 80%'] = [np.argwhere(y>thresh80)[0][0], thresh80]
		data['Rise 100%'] = [np.argmax(y), max(y)]

		tmp=np.squeeze(np.argwhere(y<thresh80))
		data['Fall 80%'] = [tmp[tmp>data['Rise 100%'][0]][0], thresh80]
		tmp=np.squeeze(np.argwhere(y<thresh50))
		data['Fall 50%'] = [tmp[tmp>data['Fall 80%'][0]][0], thresh50]
		tmp=np.squeeze(np.argwhere(y<thresh20))
		data['Fall 20%'] = [tmp[tmp>data['Fall 50%'][0]][0], thresh20]
	except Exception as e:
		print("Analysis Failed: %s" % e)
	return data

def makePolyPath(x, ftrace, baseline):
	poly_path = QPainterPath(QPointF(x[0], baseline))
	for pt in zip(x, ftrace):
		poly_path.lineTo(pt[0], pt[1])
	poly_path.lineTo(x[-1], baseline)
	poly_path.closeSubpath()
	return poly_path

def replaceRange(im, region, val):
	x1, x2 = region
	x1 = max(0, x1)
	x2 = min(x2, len(im))
	im[x1:x2 + 1] = val
	return im