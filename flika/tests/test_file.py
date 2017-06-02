import sys, os
import optparse

from ..process.file_ import *
from .. import global_vars as g
from ..window import Window
import numpy as np
import time
import pytest
from ..roi import makeROI, open_rois
import pyqtgraph as pg
from qtpy import QtGui
im = np.random.random([150, 60, 60])



class Test_File():
	def test_open(self):
		if len(g.settings['recent_files']) == 0:
			g.settings['recent_files'].append('tests')
		w = open_file()
		w.close()

	def test_open_recent(self):
		g.m._make_recents()
		if len(g.m.recentFileMenu.actions()) > 0:
			g.m.recentFileMenu.actions()[0].trigger()
			g.win.close()

	def test_save_as(self):
		w = Window(im)
		a = save_file('movie')
		os.remove(a)
		w.close()

	def test_points_io(self):
		w = Window(im)
		w.addPoint([1, 2, 3])
		w.addPoint([3, 1, 2])
		ps = save_points('test.pos')
		open_points('test.pos')
		os.remove('test.pos')

		w.close()

	def test_rois_io(self):
		w = Window(im)
		a = makeROI('rectangle', [[3, 7], [6, 5]])
		w.save_rois('test.roi')
		a.delete()
		b = open_rois('test.roi')[0]
		os.remove('test.roi')
		assert np.array_equal(b.pts, [[3, 7], [6, 5]])
		w.close()
	
