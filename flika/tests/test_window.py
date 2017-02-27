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

'''
class TestWindow():
	def setup_method(self, obj):
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
'''

class ROITest():
	TYPE=None
	POINTS=[]
	MASK=[]

	def setup_method(self, obj):
		self.win1 = Window(im)
		self.changed = False
		self.changeFinished = False
		self.roi = makeROI(self.TYPE, self.POINTS, window=self.win1)
		self.roi.sigRegionChanged.connect(self.preChange)
		self.roi.sigRegionChangeFinished.connect(self.preChangeFinished)
		self.check_placement()

	def preChange(self):
		assert not self.changed, "Change signal emitted too early"
		self.changed = True
	
	def preChangeFinished(self):
		assert not self.changeFinished, "ChangeFinished signal emitted too early"
		self.changeFinished = True

	def checkChanged(self):
		assert self.changed, "Change signal was not sent"
		self.changed = False
	
	def checkChangeFinished(self):
		assert self.changeFinished, "ChangeFinished signal was not sent"
		self.changeFinished = False
		
	def teardown_method(self, obj):
		self.roi.plot()
		self.roi.delete()
		assert self.roi not in self.win1.rois, "ROI deleted but still in window.rois"
		assert g.currentTrace == None, "Trace closed"
		self.win1.close()

	def check_placement(self):
		assert np.array_equal(self.roi.getMask(), self.MASK), "Mask differs on creation. %s != %s" % (self.roi.getMask(), self.MASK)
		assert np.array_equal(self.roi.pts, self.POINTS), "pts differs on creation. %s != %s" % (self.roi.pts, self.POINTS)
		assert np.array_equal(self.roi.getPoints(), self.POINTS), "getPoints differs on creation. %s != %s" % (self.roi.getPoints(), self.POINTS)

	def check_similar(self, other):
		mask1 = self.roi.getMask()
		mask2 = other.getMask()
		assert np.array_equal(mask1, mask2), "Mask differs on creation. %s != %s" % (mask1, mask2)
		assert np.array_equal(self.roi.pts, other.pts), "pts differs on creation. %s != %s" % (self.roi.pts, self.POINTS)
		assert np.array_equal(self.roi.getPoints(), other.getPoints()), "getPoints differs on creation. %s != %s" % (self.roi.getPoints(), other.getPoints())

	def test_copy(self):
		self.roi.copy()
		roi1 = self.win1.paste()
		assert roi1 == None and len(self.win1.rois) == 1, "Copying ROI to same window"
		
		w2 = Window(im)
		roi2 = w2.paste()
		assert self.roi in roi2.linkedROIs and roi2 in self.roi.linkedROIs, "Linked ROI on paste"
		self.check_similar(roi2)

		self.roi.translate([1, 2])

		self.checkChanged()
		self.checkChangeFinished()

		self.check_similar(roi2)

		w2.close()
		self.win1.setAsCurrentWindow()

	def test_export_import(self):
		s = str(self.roi)
		self.roi.window.exportROIs("test.txt")
		from flika.roi import load_rois
		rois = load_rois('test.txt')
		assert len(rois) == 1, "Import ROI failure"
		roi = rois[0]
		os.remove('test.txt')
		self.check_similar(roi)
		roi.delete()
	
	def test_plot(self):
		self.roi.unplot()
		trace = self.roi.plot()
		assert self.roi.traceWindow != None, "ROI plotted, roi traceWindow set"
		assert g.m.currentTrace == trace, "ROI plotted, but currentTrace is still None"
		ind = trace.get_roi_index(self.roi)
		assert trace.rois[ind]['p1trace'].opts['pen'].color().name() == self.roi.pen.color().name(), "Color not changed. %s != %s" % (trace.rois[ind]['p1trace'].opts['pen'].color().name(), self.roi.pen.color().name())
		self.roi.unplot()
		assert self.roi.traceWindow == None, "ROI unplotted, roi traceWindow cleared"
		assert g.m.currentTrace == None, "ROI unplotted, currentTrace cleared"
		g.settings['multipleTraceWindows'] = False
	
	def test_translate(self):
		path = self.roi.pts.copy()
		self.roi.translate([2, 1])

		self.checkChanged()
		self.checkChangeFinished()

		assert len(self.roi.pts) == len(path), "roi size change on translate"
		assert [i + [2, 1] in path for i in self.roi.pts], "translate applied to mask"
		self.roi.translate([-2, -1])

		self.checkChanged()
		self.checkChangeFinished()

	def test_plot_translate(self):
		trace = self.roi.plot()
		assert self.roi.traceWindow != None, "ROI plotted, roi traceWindow set. %s should not be None" % (self.roi.traceWindow)
		assert g.m.currentTrace == self.roi.traceWindow, "ROI plotted, currentTrace not set. %s != %s" % (g.m.currentTrace, self.roi.traceWindow) 
		ind = trace.get_roi_index(self.roi)

		traceItem = trace.rois[ind]['p1trace']
		yData = traceItem.yData.copy()
		self.roi.translate(2, 1)
		assert not np.array_equal(yData, traceItem.yData), "Translated ROI yData compare %s != %s" % (yData, traceItem.yData)
		
		self.checkChanged()
		self.checkChangeFinished()

		self.roi.translate(-2, -1)
		assert np.array_equal(yData, traceItem.yData), "Translated back ROI yData compare %s != %s" % (yData, traceItem.yData)

		self.checkChanged()
		self.checkChangeFinished()

		self.roi.unplot()

	def test_change_color(self):
		self.roi.unplot()
		color = QtGui.QColor('#ff00ff')
		self.roi.plot()
		self.roi.colorSelected(color)
		
		self.checkChangeFinished()

		assert self.roi.pen.color().name() == color.name(), "Color not changed. %s != %s" % (self.roi.pen.color().name(), color.name())
		self.roi.unplot()

class TestROI_Rectangle(ROITest):
	TYPE = "rectangle"
	POINTS = [[3, 2], [5, 2]]
	MASK = [[3, 4, 5, 6, 7, 3, 4, 5, 6, 7], [2, 2, 2, 2, 2, 3, 3, 3, 3, 3]]

	def test_crop(self):
		w2 = self.roi.crop()
		bound = self.roi.boundingRect()
		assert w2.image.shape[1] == bound.width() and w2.image.shape[2] == bound.height(), "Croppped image different size (%s, %s) != (%s, %s)" % (bound.width(), bound.height(), w2.image.shape[1], w2.image.shape[2])
		w2.close()

	def test_resize(self):
		self.roi.scale([1.2, 1])

		self.checkChanged()
		self.checkChangeFinished()
		
		self.POINTS[1] = [6, 2]
		self.MASK = [[3, 4, 5, 6, 7, 8, 3, 4, 5, 6, 7, 8], [2, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3]]
		self.check_placement()

class TestROI_Line(ROITest):
	TYPE="line"
	POINTS = [[3, 2], [8, 4]]
	MASK = [[3, 4, 5, 6, 7, 8], [2, 2, 3, 3, 4, 4]]

	def test_kymograph(self):
		self.roi.update_kymograph()
		kymo = self.roi.kymograph
		assert kymo.image.shape[1] == self.win1.image.shape[0]
		kymo.close()
		self.win1.setAsCurrentWindow()

	def test_move_handle(self):
		self.roi.movePoint(0, [3, 4])

		self.checkChanged()
		self.checkChangeFinished()
		
		newMask = [[3, 4, 5, 6, 7, 8], [4, 4, 4, 4, 4, 4]]
		assert np.array_equal(self.roi.getMask(), newMask)
		assert np.array_equal(self.roi.getPoints(), [[3, 4], [8, 4]])
		self.roi.movePoint(0, [3, 2])

		self.checkChanged()
		self.checkChangeFinished()


class TestROI_Freehand(ROITest):
	TYPE="freehand"
	POINTS = [3, 2], [5, 6], [2, 4]
	MASK = [[3, 3, 3, 4, 4], [2, 3, 4, 4, 5]]


class TestROI_Rect_Line(ROITest):
	TYPE="rect_line"
	POINTS = [[3, 2], [5, 4], [4, 8]]
	MASK = [[3, 4, 5, 5, 5, 4, 4, 4], [2, 3, 4, 4, 5, 6, 7, 8]]

	def test_extend(self):
		self.roi.extend(6, 8)

		self.checkChanged()
		self.checkChangeFinished()

	def test_plot_translate(self):
		pass

	def test_translate(self):
		pass

	def test_kymograph(self):
		self.roi.update_kymograph()
		kymo = self.roi.kymograph
		assert kymo.image.shape[1] == self.win1.image.shape[0]
		kymo.close()
		self.win1.setAsCurrentWindow()

	def test_copy(self):
		self.roi.copy()
		roi1 = self.win1.paste()
		assert roi1 == None and len(self.win1.rois) == 1, "Copying ROI to same window"
		
		w2 = Window(im)
		roi2 = w2.paste()
		assert self.roi in roi2.linkedROIs and roi2 in self.roi.linkedROIs, "Linked ROI on paste"
		self.check_similar(roi2)

		self.roi.lines[0].movePoint(0, [1, 2])

		self.checkChanged()
		self.checkChangeFinished()

		self.check_similar(roi2)

		w2.close()
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