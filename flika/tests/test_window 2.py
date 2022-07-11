import sys, os
import optparse

from .. import global_vars as g
from ..window import Window
import numpy as np
import time
import pytest
from ..roi import makeROI
import pyqtgraph as pg
from qtpy import QtGui
from qtpy.QtWidgets import qApp
im = np.random.random([120, 90, 90])
	
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

	def test_timeline(self):
		self.win1.imageview.setImage(im[0])
		assert self.win1.imageview.ui.roiPlot.isVisible() == False
		self.win1.imageview.setImage(im)
		assert self.win1.imageview.ui.roiPlot.isVisible() == True

class ROITest():
	TYPE=None
	POINTS=[]
	MASK=[]

	def setup_method(self):
		for i in range(3):
			try:
				self.win1 = Window(self.img)
				break
			except RuntimeError:
				pass
		if not hasattr(self, 'win1'):
			raise Exception("Unable to create Window due to RuntimeError")

		self.changed = False
		self.changeFinished = False
		self.roi = makeROI(self.TYPE, self.POINTS, window=self.win1)
		self.roi.sigRegionChanged.connect(self.preChange)
		self.roi.sigRegionChangeFinished.connect(self.preChangeFinished)
		self.check_placement()

	def preChange(self):
		self.changed = True
	
	def preChangeFinished(self):
		self.changeFinished = True

	def checkChanged(self):
		assert self.changed, "Change signal was not sent"
		self.changed = False
	
	def checkChangeFinished(self):
		assert self.changeFinished, "ChangeFinished signal was not sent"
		self.changeFinished = False
	
	def teardown_method(self, func):
		#if self.roi is not None:
		#	self.roi.delete()
		#assert self.roi not in self.win1.rois, "ROI deleted but still in window.rois"
		for roi in self.win1.rois:
			roi.delete()
		self.win1.close()
		from .conftest import fa
		fa().clear()
		pg.ViewBox.AllViews.clear()
		pg.ViewBox.NamedViews.clear()



	def check_placement(self, mask=None, points=None):
		if mask is None:
			mask = self.MASK
		if points is None:
			points = self.POINTS
		assert np.array_equal(self.roi.getMask(), mask), "Mask differs on creation. %s != %s" % (self.roi.getMask(), self.MASK)
		assert np.array_equal(self.roi.pts, points), "pts differs on creation. %s != %s" % (self.roi.pts, self.POINTS)
		assert np.array_equal(self.roi.getPoints(), points), "getPoints differs on creation. %s != %s" % (self.roi.getPoints(), self.POINTS)

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
		
		w2 = Window(self.img)
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
		self.roi.window.save_rois("test.txt")
		from ..roi import open_rois
		rois = open_rois('test.txt')
		assert len(rois) == 1, "Import ROI failure"
		roi = rois[0]
		os.remove('test.txt')
		self.check_similar(roi)
		roi.delete()
	
	def test_plot(self):
		self.roi.unplot()
		trace = self.roi.plot()
		if trace is None:
			assert self.win1.image.ndim == 4, "Trace failed on non-4D image"
			return
		assert self.roi.traceWindow != None, "ROI plotted, roi traceWindow set"
		assert g.currentTrace == trace, "ROI plotted, but currentTrace is still None"
		ind = trace.get_roi_index(self.roi)
		if trace.rois[ind]['p1trace'].opts['pen'] != None:
			assert trace.rois[ind]['p1trace'].opts['pen'].color().name() == self.roi.pen.color().name(), "Color not changed. %s != %s" % (trace.rois[ind]['p1trace'].opts['pen'].color().name(), self.roi.pen.color().name())
		self.roi.unplot()
		assert self.roi.traceWindow == None, "ROI unplotted, roi traceWindow cleared"
		assert g.currentTrace == None, "ROI unplotted, currentTrace cleared"
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
		if trace is None:
			assert self.win1.image.ndim == 4, "Trace failed on non-4D image"
			return
		assert self.roi.traceWindow != None, "ROI plotted, roi traceWindow set. %s should not be None" % (self.roi.traceWindow)
		assert g.currentTrace == self.roi.traceWindow, "ROI plotted, currentTrace not set. %s != %s" % (g.currentTrace, self.roi.traceWindow) 
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
	
	
	def test_translate_multiple(self):
		translates = [[5, 0], [0, 5], [-5, 0], [0, -5]]
		self.roi.copy()
		w2 = Window(self.img)
		roi2 = w2.paste()
		roi2.colorSelected(QtGui.QColor(0, 255, 130))
		self.roi.plot()
		roi2.plot()
		for i in range(20 * len(translates)):
			tr = translates[i % len(translates)]
			self.roi.translate(*tr)
			self.checkChanged()
			self.checkChangeFinished()
			#time.sleep(.02)
			#qApp.processEvents()

		w2.close()
		self.roi.draw_from_points(self.POINTS)
	
	def test_resize_multiple(self):
		if len(self.roi.getHandles()) == 0:
			return
		translates = [[1, 0], [0, 1], [-1, 0], [0, -1]]
		self.roi.copy()
		w2 = Window(self.img)
		roi2 = w2.paste()
		roi2.colorSelected(QtGui.QColor(0, 255, 130))
		self.roi.plot()
		roi2.plot()

		for h in self.roi.getHandles():
			h._updateView()
			pos = h.viewPos()
			for i in range(4 * len(translates)):
				tr = translates[i % len(translates)]
				self.roi.movePoint(h, [pos.x() + tr[0], pos.y() + tr[1]])
				self.checkChanged()
				self.checkChangeFinished()
				self.check_similar(roi2)
				#time.sleep(.02)
				#qApp.processEvents()

		w2.close()
		self.roi.draw_from_points(self.POINTS)

class ROI_Rectangle(ROITest):
	TYPE = "rectangle"
	POINTS = [[3, 2], [2, 5]]
	MASK = [[3, 4, 3, 4, 3, 4, 3, 4, 3, 4], [2, 2, 3, 3, 4, 4, 5, 5, 6, 6]]

	def test_crop(self):
		w2 = self.roi.crop()
		bound = self.roi.boundingRect()
		mask = self.roi.getMask()
		w, h = np.ptp(mask, 1) + [1, 1]

		assert w == bound.width() and h == bound.height(), "Croppped image different size (%s, %s) != (%s, %s)" % (bound.width(), bound.height(), w, h)
		w2.close()

	def test_resize(self):
		self.roi.scale([1, 1.2])

		self.checkChanged()
		self.checkChangeFinished()
		
		points = [self.POINTS[0], [2, 6]]
		mask = [[3, 4, 3, 4, 3, 4, 3, 4, 3, 4, 3, 4], [2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7]]
		self.check_placement(points=points, mask=mask)

		self.roi.draw_from_points(self.POINTS)

class ROI_Line(ROITest):
	TYPE="line"
	POINTS = [[3, 2], [8, 4]]
	MASK = [[3, 4, 5, 6, 7, 8], [2, 2, 3, 3, 4, 4]]

	def test_kymograph(self):
		self.roi.update_kymograph()
		if self.roi.kymograph is None and self.win1.image.ndim != 3:
			return
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


class ROI_Freehand(ROITest):
	TYPE="freehand"
	POINTS = [3, 2], [5, 6], [2, 4]
	MASK = [[3, 3, 3, 4, 4], [2, 3, 4, 4, 5]]

	def test_translate_multiple(self):
		pass


class ROI_Rect_Line(ROITest):
	TYPE="rect_line"
	POINTS = [[3, 2], [5, 4], [4, 8]]
	MASK = [[3, 4, 5, 5, 5, 4, 4, 4], [2, 3, 4, 4, 5, 6, 7, 8]]

	
	def test_extend(self):
		self.roi.extend(9, 2)

		self.checkChanged()
		self.checkChangeFinished()

		self.roi.removeSegment(len(self.roi.lines)-1)
	
	def test_plot_translate(self):
		pass

	def test_translate(self):
		pass

	def test_translate_multiple(self):
		pass

	def test_kymograph(self):
		self.roi.update_kymograph()
		if self.roi.kymograph is None and self.win1.image.ndim != 3:
			return
		kymo = self.roi.kymograph
		assert kymo.image.shape[1] == self.win1.image.shape[0]
		
		self.roi.setWidth(3)
		assert kymo.image.shape[1] == self.win1.image.shape[0]

		kymo.close()
		self.win1.setAsCurrentWindow()

	def test_copy(self):
		self.roi.copy()
		roi1 = self.win1.paste()
		assert roi1 == None and len(self.win1.rois) == 1, "Copying ROI to same window"
		
		w2 = Window(self.img)
		roi2 = w2.paste()
		assert self.roi in roi2.linkedROIs and roi2 in self.roi.linkedROIs, "Linked ROI on paste"
		self.check_similar(roi2)

		self.roi.lines[0].movePoint(0, [1, 2])

		self.checkChanged()
		self.checkChangeFinished()

		self.check_similar(roi2)

		w2.close()
		self.win1.setAsCurrentWindow()


class Test_Rectangle_2D(ROI_Rectangle):
	img = np.random.random([20, 20])
class Test_Rectangle_3D(ROI_Rectangle):
	img = np.random.random([10, 20, 20])
class Test_Rectangle_4D(ROI_Rectangle):
	img = np.random.random([10, 20, 20, 3])

class Test_Line_2D(ROI_Line):
	img = np.random.random([20, 20])
class Test_Line_3D(ROI_Line):
	img = np.random.random([10, 20, 20])
class Test_Line_4D(ROI_Line):
	img = np.random.random([10, 20, 20, 3])

class Test_Freehand_2D(ROI_Freehand):
	img = np.random.random([20, 20])
class Test_Freehand_3D(ROI_Freehand):
	img = np.random.random([10, 20, 20])
class Test_Freehand_4D(ROI_Freehand):
	img = np.random.random([10, 20, 20, 3])

class Test_Rect_Line_2D(ROI_Rect_Line):
	img = np.random.random([20, 20])
class Test_Rect_Line_3D(ROI_Rect_Line):
	img = np.random.random([10, 20, 20])
class Test_Rect_Line_4D(ROI_Rect_Line):
	img = np.random.random([10, 20, 20, 3])




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
		self.rect.window.save_rois('tempROI.txt')
		t = open('tempROI.txt').read()
		assert t == 'rectangle\n3 2\n4 5\n'
		os.remove('tempROI.txt')
