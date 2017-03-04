import sys, os
import optparse

from flika.app import *
from flika.process.file_ import *
import flika.global_vars as g
from flika.window import Window
import numpy as np
import time
import pytest
from flika.roi import makeROI, load_rois
import pyqtgraph as pg
from qtpy import QtGui

fa = FlikaApplication()
im = np.random.random([150, 60, 60])

class Test_File():
	def test_open(self):
		if 
		w = open_file()
		w.close()

	def test_open_gui(self):
		w = open_file_from_gui()
		if w:
			w.close()

	def test_open_recent(self):
		g.m._make_recents()
		if len(g.m.recentFileMenu.actions()) > 0:
			g.m.recentFileMenu.actions()[0].trigger()
		g.currentWindow.close()


	def test_save_as(self):
		w = Window(im)
		a = save_window('movie')
		os.remove(a)
		w.close()

	def test_points_io(self):
		w = Window(im)
		w.addPoint([1, 2, 3])
		w.addPoint([3, 1, 2])
		ps = save_points('test.pos')
		load_points('test.pos')
		os.remove('test.pos')

		w.close()

	def test_rois_io(self):
		w = Window(im)
		a = makeROI('rectangle', [[3, 7], [6, 5]])
		w.exportROIs('test.roi')
		a.delete()
		b = load_rois('test.roi')[0]
		os.remove('test.roi')
		assert np.array_equal(b.pts, [[3, 7], [6, 5]])
		w.close()



fa.close()
