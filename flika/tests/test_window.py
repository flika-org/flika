import sys, os
import optparse

from flika.app import *
import flika.global_vars as g
from flika.window import Window
import numpy as np
import time
import pytest
from flika.roi import makeROI
import pyqtgraph as pg
from qtpy import QtGui

fa = FlikaApplication()
im = np.random.random([150, 60, 60])

class TestWindow():
	def setup_method(self):
		self.win1 = Window(im)

	def teardown_method(self):
		self.win1.close()

	def test_link(self):
		win2 = Window(im)
		self.win1.link(win2)
		self.win1.setIndex(100)
		assert win2.currentIndex == self.win1.currentIndex, "Linked windows failure"
		win2.setIndex(50)
		assert self.win1.currentIndex == win2.currentIndex, "Linked windows failure"
		win2.unlink(self.win1)
		self.win1.setIndex(100)
		assert win2.currentIndex != self.win1.currentIndex, "Unlinked windows failure"
		win2.setIndex(50)
		assert self.win1.currentIndex != win2.currentIndex, "Unlinked windows failure"
		win2.close()
		assert len(self.win1.linkedWindows) == 0, "Closed window is not unlinked"

class ROITest():
	TYPE=None
	POINTS=[]
	MASK=[]

	def setup_method(self):
		self.win1 = Window(im)
		self.roi = makeROI(self.TYPE, self.POINTS, window=self.win1)
		
	def teardown_method(self):
		self.roi.plot()
		self.roi.delete()
		assert self.roi not in self.win1.rois, "ROI deleted but still in window.rois"
		assert g.currentTrace == None, "Trace closed"
		self.win1.close()
	'''
	def test_copy(self):
		self.roi.copy()
		roi1 = self.win1.paste()
		assert roi1 == None and len(self.win1.rois) == 1, "Copying ROI to same window"
		assert len(self.roi.linkedROIs) == 0, "no link on paste failure"
		
		w2 = Window(im)
		roi2 = w2.paste()
		assert self.roi in roi2.linkedROIs and roi2 in self.roi.linkedROIs, "Linked ROI on paste"
		assert np.array_equal(self.roi.mask, roi2.mask), "Masks do not match"

		self.roi.translate([1, 2])
		assert np.array_equal(roi2.pts, self.roi.pts), "linked rois move together"

		w2.close()
		self.win1.setAsCurrentWindow()

	def test_export_import(self):
		s = str(self.roi)
		self.roi.window.exportROIs("test.txt")
		from flika.roi import load_rois
		rois = load_rois('test.txt')
		assert len(rois) == 1, "Import ROI failure"
		roi = rois[0]
		assert np.array_equal(roi.mask, self.roi.mask), "Imported ROI mask comparison"
		roi.delete()

	def test_mask(self):
		assert np.array_equal(self.roi.mask, self.MASK), "Mask not what expected. %s != %s" % (self.roi.mask, self.MASK)
		assert self.roi in self.win1.rois, "makeROI not in window.rois"
	
	def test_plot(self):
		self.roi.unplot()
		if g.settings['multipleTraceWindows']:
			trace = self.roi.plot()
			assert self.roi.traceWindow != None, "ROI plotted, roi traceWindow set"
			assert g.m.currentTrace == trace, "ROI plotted, but currentTrace is still None"
			ind = trace.get_roi_index(self.roi)
			assert trace.rois[ind]['p1trace'].opts['pen'].color() == self.roi.pen, "Color not changed. %s != %s" % (trace.rois[ind]['p1trace'].opts['pen'], self.roi.pen)
			self.roi.unplot()
			assert self.roi.traceWindow == None, "ROI unplotted, roi traceWindow cleared"
			assert g.m.currentTrace == None, "ROI unplotted, currentTrace cleared"
		g.settings['multipleTraceWindows'] = False
	
	def test_translate(self):
		path = self.roi.pts.copy()
		self.roi.translate([2, 1])
		assert len(self.roi.pts) == len(path), "roi size change on translate"
		assert [i + [2, 1] in path for i in self.roi.pts], "translate applied to mask"
		self.roi.translate([-2, -1])

	'''
	def test_plot_translate(self):
		trace = self.roi.plot()
		assert self.roi.traceWindow != None, "ROI plotted, roi traceWindow set. %s should not be None" % (self.roi.traceWindow)
		assert g.m.currentTrace == self.roi.traceWindow, "ROI plotted, currentTrace not set. %s != %s" % (g.m.currentTrace, self.roi.traceWindow) 
		ind = trace.get_roi_index(self.roi)

		traceItem = trace.rois[ind]['p1trace']
		yData = traceItem.yData.copy()
		self.roi.translate(2, 1, finish=False)
		trace.redrawPartialThread.quit_loop = True#.emit()
		self.roi.finish_translate()
		#g.currentTrace.translate_done(self.roi)
		assert not np.array_equal(yData, traceItem.yData), "Translated ROI yData compare %s" % (yData - traceItem.yData)
		
		self.roi.translate(2, 1, finish=False)
		trace.redrawPartialThread.quit_loop = True#.emit()
		self.roi.finish_translate()
		assert np.array_equal(yData, traceItem.yData), "Translated back ROI yData compare %s" % (yData - traceItem.yData)

		self.roi.unplot()
	
	def test_change_color(self):
		self.roi.unplot()
		color = QtGui.QColor('#ff00ff')
		self.roi.plot()
		self.roi.colorSelected(color)
		assert self.roi.color == color, "Color not changed. %s != %s" % (self.roi.color, color)
		self.roi.unplot()

class TestROI_Rectangle(ROITest):
	TYPE = "rectangle"
	POINTS = [[3, 2], [4, 3]]
	MASK = [[3, 2], [3, 3], [3, 4],
			[4, 2], [4, 3], [4, 4],
			[5, 2], [5, 3], [5, 4],
			[6, 2], [6, 3], [6, 4]]

	def test_state(self):
		assert np.array_equal(self.roi.state['pos'], np.array(self.POINTS[0])), 'Position set on creation, %s != %s' % (self.roi.state['pos'], self.POINTS[0])

	def test_crop(self):
		w2 = self.roi.crop()
		bound = self.roi.boundingRect()
		assert w2.image.shape[1] == bound.width()+1 and w2.image.shape[2] == bound.height()+1, "Croppped image different size (%s, %s) != (%s, %s)" % (bound.width()+1, bound.height()+1, w2.image.shape[1], w2.image.shape[2])
		w2.close()

class TestROI_Line(ROITest):
	TYPE="line"
	POINTS = [[3, 2], [4, 3]]
	MASK = [[3, 2], [4, 3]]

	def test_state(self):
		assert self.roi.pts[0] == pg.Point(self.POINTS[0]), 'Position set on creation, %s != %s' % (self.roi.pts[0], self.POINTS[0])

	def test_kymograph(self):
		self.roi.update_kymograph()
		kymo = self.roi.kymograph
		assert kymo.image.shape[1] == self.win1.image.shape[0]
		kymo.close()
		self.win1.setAsCurrentWindow()

class TestROI_Freehand(ROITest):
	TYPE="freehand"
	POINTS = [3, 2], [5, 6], [2, 4]
	MASK = [[3, 2], [3, 3], [3, 4], [4, 4], [4, 5]]

	def test_state(self):
		assert self.roi.pts[0] == pg.Point(self.POINTS[0]), 'Position set on creation, %s != %s' % (self.roi.pts[0], self.POINTS[0])


class TestROI_Rect_Line(ROITest):
	TYPE="rect_line"
	POINTS = [[3, 2], [4, 3]]
	MASK = [[3, 1], [4, 2], [4, 3]]

	def test_state(self):
		assert self.roi.pts[0] == pg.Point(self.POINTS[0]), 'Position set on creation, %s != %s' % (self.roi.pts[0], self.POINTS[0]) 

	def test_extend(self):
		self.roi.extend(6, 8)

	def test_plot_translate(self):
		pass

	def test_kymograph(self):
		self.roi.update_kymograph()
		kymo = self.roi.kymograph
		assert kymo.image.shape[1] == self.win1.image.shape[0]
		kymo.close()
		self.win1.setAsCurrentWindow()
'''
class TestTracefig():
	def setup_method(self):
		self.w1 = Window(im)
		self.rect = makeROI('rectangle', [[3, 2], [4, 5]], window=self.w1)
		self.trace = self.rect.plot()

	def teardown_method(self):
		self.w1.close()

	def test_plotting(self):
		self.trace.indexChanged.emit(20)
		assert self.w1.currentIndex == 20, "trace indexChanged"

	def test_export(self):
		self.rect.window.exportROIs('tempROI.txt')
		t = open('tempROI.txt').read()
		assert t == 'rectangle\n3 2\n7 2\n7 7\n3 7\n'
		os.remove('tempROI.txt')
'''

fa.close()