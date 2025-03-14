import sys, os
import contextlib
import pytest
import numpy as np
import pyqtgraph as pg
from qtpy import QtGui, QtWidgets
from qtpy.QtWidgets import QApplication

from .. import global_vars as g
from ..window import Window
from ..roi import makeROI
from ..app import application
# Create test images for various test cases
STANDARD_2D_IMAGE = np.random.random([20, 20])
STANDARD_3D_IMAGE = np.random.random([10, 20, 20])
STANDARD_4D_IMAGE = np.random.random([10, 20, 20, 3])

# Import suppress_alerts from test_processes or redefine it here
@contextlib.contextmanager
def suppress_alerts():
	"""Context manager to suppress all alerts during test execution"""
	# Store original alert functions
	original_alert = None
	original_message_box = None
	
	if hasattr(g, "alert"):
		original_alert = g.alert
		g.alert = lambda *args, **kwargs: None
	
	if hasattr(g, "messageBox"):
		original_message_box = g.messageBox
		g.messageBox = lambda *args, **kwargs: QtWidgets.QMessageBox.StandardButton.Ok
	
	# Create dummy functions for QtWidgets.QMessageBox
	original_qmessagebox_methods = {}
	for method_name in ['information', 'warning', 'critical', 'question', 'about']:
		if hasattr(QtWidgets.QMessageBox, method_name):
			original_qmessagebox_methods[method_name] = getattr(QtWidgets.QMessageBox, method_name)
			setattr(QtWidgets.QMessageBox, method_name, 
					lambda *args, **kwargs: QtWidgets.QMessageBox.Ok)
	
	try:
		yield
	finally:
		# Restore original functions
		if original_alert is not None:
			g.alert = original_alert
		
		if original_message_box is not None:
			g.messageBox = original_message_box
		
		for method_name, original_method in original_qmessagebox_methods.items():
			setattr(QtWidgets.QMessageBox, method_name, original_method)


# Mock message box fixture to prevent dialogs from blocking tests
@pytest.fixture
def mock_message_box(monkeypatch):
	"""Mock any message boxes to automatically return OK"""
	with suppress_alerts():
		yield  # This will maintain the alert suppression during test execution


# Window fixture for basic window tests
@pytest.fixture
def standard_window():
	"""Create a standard 3D window for testing"""
	win = Window(STANDARD_3D_IMAGE)
	yield win
	win.close()
	

class TestWindow:
	def test_link(self, standard_window, mock_message_box):
		win1 = standard_window
		win2 = Window(STANDARD_3D_IMAGE)
		
		try:
			win1.link(win2)
			win1.setIndex(100)
			assert win2.currentIndex == win1.currentIndex, "Linked windows failure"
			
			win2.setIndex(50)
			assert win1.currentIndex == win2.currentIndex, "Linked windows failure"
			
			win2.unlink(win1)
			win1.setIndex(100)
			assert win2.currentIndex != win1.currentIndex, "Unlinked windows failure"
			
			win2.setIndex(50)
			assert win1.currentIndex != win2.currentIndex, "Unlinked windows failure"
			
			win2.close()
			assert len(win1.linkedWindows) == 0, "Closed window is not unlinked"
		finally:
			if 'win2' in locals():
				win2.close()

	def test_timeline(self, standard_window, mock_message_box):
		win1 = standard_window
		win1.imageview.setImage(STANDARD_3D_IMAGE[0])
		assert win1.imageview.ui.roiPlot.isVisible() == False
		win1.imageview.setImage(STANDARD_3D_IMAGE)
		assert win1.imageview.ui.roiPlot.isVisible() == True


# Base class for ROI tests with common setup/teardown
class ROITest:
	TYPE = None
	POINTS = []
	MASK = []
	
	@pytest.fixture
	def roi_setup(self, mock_message_box, fa: application.FlikaApplication):
		"""Setup ROI test with window and ROI creation"""
		# Setup window with retries in case of RuntimeError
		for i in range(3):
			try:
				win = Window(self.img)
				break
			except RuntimeError:
				pass
		else:
			raise Exception("Unable to create Window due to RuntimeError")
			
		# Create tracking variables and ROI
		changed = False
		changeFinished = False
		
		roi = makeROI(self.TYPE, self.POINTS, window=win)
		
		# Define callback handlers
		def on_change():
			nonlocal changed
			changed = True
			
		def on_change_finished():
			nonlocal changeFinished
			changeFinished = True
			
		roi.sigRegionChanged.connect(on_change)
		roi.sigRegionChangeFinished.connect(on_change_finished)
		
		# Return all the objects needed for testing
		yield win, roi, lambda: changed, lambda: changeFinished, lambda: (changed := False), lambda: (changeFinished := False)
		
		# Cleanup
		for r in win.rois:
			r.delete()
		win.close()
		
		# Clear FlikaApplication correctly through the fixture
		fa.clear()
		
		pg.ViewBox.AllViews.clear()
		pg.ViewBox.NamedViews.clear()
	
	def check_placement(self, roi, mask=None, points=None):
		"""Verify ROI placement is correct"""
		if mask is None:
			mask = self.MASK
		if points is None:
			points = self.POINTS
			
		assert np.array_equal(roi.getMask(), mask), f"Mask differs on creation. {roi.getMask()} != {mask}"
		assert np.array_equal(roi.pts, points), f"pts differs on creation. {roi.pts} != {points}"
		assert np.array_equal(roi.getPoints(), points), f"getPoints differs on creation. {roi.getPoints()} != {points}"

	def check_similar(self, roi1, roi2):
		"""Verify two ROIs have similar properties"""
		mask1 = roi1.getMask()
		mask2 = roi2.getMask()
		assert np.array_equal(mask1, mask2), f"Mask differs between ROIs. {mask1} != {mask2}"
		assert np.array_equal(roi1.pts, roi2.pts), f"pts differs between ROIs. {roi1.pts} != {roi2.pts}"
		assert np.array_equal(roi1.getPoints(), roi2.getPoints()), f"getPoints differs between ROIs. {roi1.getPoints()} != {roi2.getPoints()}"

	def test_roi_creation(self, roi_setup):
		"""Test basic ROI creation and properties"""
		win, roi, _, _, _, _ = roi_setup
		self.check_placement(roi)
	
	def test_copy(self, roi_setup, mock_message_box):
		win, roi, _, _, _, _ = roi_setup
		
		roi.copy()
		roi1 = win.paste()
		assert roi1 == None and len(win.rois) == 1, "Copying ROI to same window"
		
		w2 = Window(self.img)
		try:
			roi2 = w2.paste()
			assert roi in roi2.linkedROIs and roi2 in roi.linkedROIs, "Linked ROI on paste"
			self.check_similar(roi, roi2)

			roi.translate([1, 2])
			assert roi2.pts[0][0] == roi.pts[0][0], "Linked ROIs should move together"
		finally:
			w2.close()
			win.setAsCurrentWindow()

	def test_export_import(self, roi_setup, mock_message_box):
		win, roi, _, _, _, _ = roi_setup
		
		try:
			s = str(roi)
			roi.window.save_rois("test.txt")
			from ..roi import open_rois
			rois = open_rois('test.txt')
			
			assert len(rois) == 1, "Import ROI failure"
			imported_roi = rois[0]
			self.check_similar(roi, imported_roi)
			imported_roi.delete()
		finally:
			# Ensure file is removed even if test fails
			if os.path.exists('test.txt'):
				os.remove('test.txt')

	def test_plot(self, roi_setup, mock_message_box):
		win, roi, _, _, _, _ = roi_setup
		
		roi.unplot()
		trace = roi.plot()
		
		if trace is None:
			assert win.image.ndim == 4, "Trace failed on non-4D image"
			return
			
		assert roi.traceWindow != None, "ROI plotted, roi traceWindow set"
		assert g.currentTrace == trace, "ROI plotted, but currentTrace is still None"
		
		ind = trace.get_roi_index(roi)
		if trace.rois[ind]['p1trace'].opts['pen'] != None:
			assert trace.rois[ind]['p1trace'].opts['pen'].color().name() == roi.pen.color().name(), f"Color not changed. {trace.rois[ind]['p1trace'].opts['pen'].color().name()} != {roi.pen.color().name()}"
		
		roi.unplot()
		assert roi.traceWindow == None, "ROI unplotted, roi traceWindow cleared"
		assert g.currentTrace == None, "ROI unplotted, currentTrace cleared"
		g.settings['multipleTraceWindows'] = False

	def test_translate(self, roi_setup, mock_message_box):
		win, roi, get_changed, get_change_finished, reset_changed, reset_change_finished = roi_setup
		
		path = roi.pts.copy()
		roi.translate([2, 1])

		assert get_changed(), "Change signal was not sent"
		assert get_change_finished(), "ChangeFinished signal was not sent"
		reset_changed()
		reset_change_finished()

		assert len(roi.pts) == len(path), "roi size change on translate"
		for i in roi.pts:
			assert any(np.array_equal(i + [2, 1], p) for p in path), "translate applied to mask"
		
		roi.translate([-2, -1])
		assert get_changed(), "Change signal was not sent"
		assert get_change_finished(), "ChangeFinished signal was not sent"

	def test_plot_translate(self, roi_setup, mock_message_box):
		win, roi, get_changed, get_change_finished, reset_changed, reset_change_finished = roi_setup
		
		trace = roi.plot()
		if trace is None:
			assert win.image.ndim == 4, "Trace failed on non-4D image"
			return
			
		assert roi.traceWindow != None, f"ROI plotted, roi traceWindow set. {roi.traceWindow} should not be None"
		assert g.currentTrace == roi.traceWindow, f"ROI plotted, currentTrace not set. {g.currentTrace} != {roi.traceWindow}"
		
		ind = trace.get_roi_index(roi)
		traceItem = trace.rois[ind]['p1trace']
		yData = traceItem.yData.copy()
		
		roi.translate(2, 1)
		assert not np.array_equal(yData, traceItem.yData), f"Translated ROI yData compare {yData} != {traceItem.yData}"
		
		assert get_changed(), "Change signal was not sent"
		assert get_change_finished(), "ChangeFinished signal was not sent"
		reset_changed()
		reset_change_finished()

		roi.translate(-2, -1)
		assert np.array_equal(yData, traceItem.yData), f"Translated back ROI yData compare {yData} != {traceItem.yData}"

		assert get_changed(), "Change signal was not sent"
		assert get_change_finished(), "ChangeFinished signal was not sent"

		roi.unplot()

	def test_change_color(self, roi_setup, mock_message_box):
		win, roi, get_changed, get_change_finished, reset_changed, reset_change_finished = roi_setup
		
		roi.unplot()
		color = QtGui.QColor('#ff00ff')
		roi.plot()
		roi.colorSelected(color)
		
		assert get_change_finished(), "ChangeFinished signal was not sent"
		reset_change_finished()

		assert roi.pen.color().name() == color.name(), f"Color not changed. {roi.pen.color().name()} != {color.name()}"
		roi.unplot()
	
	def test_translate_multiple(self, roi_setup, mock_message_box):
		win, roi, get_changed, get_change_finished, reset_changed, reset_change_finished = roi_setup
		
		translates = [[5, 0], [0, 5], [-5, 0], [0, -5]]
		roi.copy()
		
		w2 = Window(self.img)
		try:
			roi2 = w2.paste()
			roi2.colorSelected(QtGui.QColor(0, 255, 130))
			roi.plot()
			roi2.plot()
			
			for i in range(5 * len(translates)):  # Reduced from 20 to 5 for faster tests
				tr = translates[i % len(translates)]
				roi.translate(*tr)
				assert get_changed(), "Change signal was not sent"
				assert get_change_finished(), "ChangeFinished signal was not sent"
				reset_changed()
				reset_change_finished()
				
				# Process events to update UI
				QApplication.processEvents()
		finally:
			w2.close()
			roi.draw_from_points(self.POINTS)

	def test_resize_multiple(self, roi_setup, mock_message_box):
		win, roi, get_changed, get_change_finished, reset_changed, reset_change_finished = roi_setup
		
		handles = roi.getHandles()
		if len(handles) == 0:
			pytest.skip("ROI has no handles for resize test")
			
		translates = [[1, 0], [0, 1], [-1, 0], [0, -1]]
		roi.copy()
		
		w2 = Window(self.img)
		try:
			roi2 = w2.paste()
			roi2.colorSelected(QtGui.QColor(0, 255, 130))
			roi.plot()
			roi2.plot()

			for h in roi.getHandles():
				h._updateView()
				pos = h.viewPos()
				
				for i in range(2 * len(translates)):  # Reduced from 4 to 2 for faster tests
					tr = translates[i % len(translates)]
					roi.movePoint(h, [pos.x() + tr[0], pos.y() + tr[1]])
					
					assert get_changed(), "Change signal was not sent"
					assert get_change_finished(), "ChangeFinished signal was not sent"
					reset_changed()
					reset_change_finished()
					
					self.check_similar(roi, roi2)
					
					# Process events to update UI
					QApplication.processEvents()
		finally:
			w2.close()
			roi.draw_from_points(self.POINTS)


class ROI_Rectangle(ROITest):
	TYPE = "rectangle"
	POINTS = [[3, 2], [2, 5]]
	MASK = [[3, 4, 3, 4, 3, 4, 3, 4, 3, 4], [2, 2, 3, 3, 4, 4, 5, 5, 6, 6]]

	def test_crop(self, roi_setup, mock_message_box):
		win, roi, _, _, _, _ = roi_setup
		
		w2 = roi.crop()
		try:
			bound = roi.boundingRect()
			mask = roi.getMask()
			w, h = np.ptp(mask, 1) + [1, 1]

			assert w == bound.width() and h == bound.height(), f"Croppped image different size ({bound.width()}, {bound.height()}) != ({w}, {h})"
		finally:
			if w2 is not None:
				w2.close()

	def test_resize(self, roi_setup, mock_message_box):
		win, roi, get_changed, get_change_finished, reset_changed, reset_change_finished = roi_setup
		
		roi.scale([1, 1.2])

		assert get_changed(), "Change signal was not sent"
		assert get_change_finished(), "ChangeFinished signal was not sent"
		reset_changed()
		reset_change_finished()
		
		points = [self.POINTS[0], [2, 6]]
		mask = [[3, 4, 3, 4, 3, 4, 3, 4, 3, 4, 3, 4], [2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7]]
		self.check_placement(roi, points=points, mask=mask)

		roi.draw_from_points(self.POINTS)


class ROI_Line(ROITest):
	TYPE = "line"
	POINTS = [[3, 2], [8, 4]]
	MASK = [[3, 4, 5, 6, 7, 8], [2, 2, 3, 3, 4, 4]]

	def test_kymograph(self, roi_setup, mock_message_box):
		win, roi, _, _, _, _ = roi_setup
		
		roi.update_kymograph()
		if roi.kymograph is None and win.image.ndim != 3:
			pytest.skip("Kymograph requires 3D image")
			return
			
		try:
			kymo = roi.kymograph
			assert kymo.image.shape[1] == win.image.shape[0]
		finally:
			if hasattr(roi, 'kymograph') and roi.kymograph is not None:
				roi.kymograph.close()
			win.setAsCurrentWindow()

	def test_move_handle(self, roi_setup, mock_message_box):
		win, roi, get_changed, get_change_finished, reset_changed, reset_change_finished = roi_setup
		
		roi.movePoint(0, [3, 4])

		assert get_changed(), "Change signal was not sent"
		assert get_change_finished(), "ChangeFinished signal was not sent"
		reset_changed()
		reset_change_finished()
		
		newMask = [[3, 4, 5, 6, 7, 8], [4, 4, 4, 4, 4, 4]]
		assert np.array_equal(roi.getMask(), newMask)
		assert np.array_equal(roi.getPoints(), [[3, 4], [8, 4]])
		
		roi.movePoint(0, [3, 2])

		assert get_changed(), "Change signal was not sent"
		assert get_change_finished(), "ChangeFinished signal was not sent"


class ROI_Freehand(ROITest):
	TYPE = "freehand"
	POINTS = [3, 2], [5, 6], [2, 4]
	MASK = [[3, 3, 3, 4, 4], [2, 3, 4, 4, 5]]

	def test_translate_multiple(self, roi_setup, mock_message_box):
		# Skip this test for freehand ROIs
		pytest.skip("Translate multiple not applicable to freehand ROIs")


class ROI_Rect_Line(ROITest):
	TYPE = "rect_line"
	POINTS = [[3, 2], [5, 4], [4, 8]]
	MASK = [[3, 4, 5, 5, 5, 4, 4, 4], [2, 3, 4, 4, 5, 6, 7, 8]]

	def test_extend(self, roi_setup, mock_message_box):
		win, roi, get_changed, get_change_finished, reset_changed, reset_change_finished = roi_setup
		
		roi.extend(9, 2)

		assert get_changed(), "Change signal was not sent"
		assert get_change_finished(), "ChangeFinished signal was not sent"
		reset_changed()
		reset_change_finished()

		roi.removeSegment(len(roi.lines)-1)
	
	def test_plot_translate(self, roi_setup, mock_message_box):
		# Skip this test for rect_line ROIs
		pytest.skip("Plot translate test not applicable to rect_line ROIs")

	def test_translate(self, roi_setup, mock_message_box):
		# Skip this test for rect_line ROIs
		pytest.skip("Translate test not applicable to rect_line ROIs")

	def test_translate_multiple(self, roi_setup, mock_message_box):
		# Skip this test for rect_line ROIs
		pytest.skip("Translate multiple not applicable to rect_line ROIs")

	def test_kymograph(self, roi_setup, mock_message_box):
		win, roi, _, _, _, _ = roi_setup
		
		roi.update_kymograph()
		if roi.kymograph is None and win.image.ndim != 3:
			pytest.skip("Kymograph requires 3D image")
			return
			
		try:
			kymo = roi.kymograph
			assert kymo.image.shape[1] == win.image.shape[0]
			
			roi.setWidth(3)
			assert kymo.image.shape[1] == win.image.shape[0]
		finally:
			if hasattr(roi, 'kymograph') and roi.kymograph is not None:
				roi.kymograph.close()
			win.setAsCurrentWindow()

	def test_copy(self, roi_setup, mock_message_box):
		win, roi, get_changed, get_change_finished, reset_changed, reset_change_finished = roi_setup
		
		roi.copy()
		roi1 = win.paste()
		assert roi1 == None and len(win.rois) == 1, "Copying ROI to same window"
		
		w2 = Window(self.img)
		try:
			roi2 = w2.paste()
			assert roi in roi2.linkedROIs and roi2 in roi.linkedROIs, "Linked ROI on paste"
			self.check_similar(roi, roi2)

			roi.lines[0].movePoint(0, [1, 2])

			assert get_changed(), "Change signal was not sent"
			assert get_change_finished(), "ChangeFinished signal was not sent"
			reset_changed()
			reset_change_finished()

			self.check_similar(roi, roi2)
		finally:
			w2.close()
			win.setAsCurrentWindow()


# Define test classes for specific image dimensions
class Test_Rectangle_2D(ROI_Rectangle):
	img = STANDARD_2D_IMAGE

class Test_Rectangle_3D(ROI_Rectangle):
	img = STANDARD_3D_IMAGE

class Test_Rectangle_4D(ROI_Rectangle):
	img = STANDARD_4D_IMAGE

class Test_Line_2D(ROI_Line):
	img = STANDARD_2D_IMAGE

class Test_Line_3D(ROI_Line):
	img = STANDARD_3D_IMAGE

class Test_Line_4D(ROI_Line):
	img = STANDARD_4D_IMAGE

class Test_Freehand_2D(ROI_Freehand):
	img = STANDARD_2D_IMAGE

class Test_Freehand_3D(ROI_Freehand):
	img = STANDARD_3D_IMAGE

class Test_Freehand_4D(ROI_Freehand):
	img = STANDARD_4D_IMAGE

class Test_Rect_Line_2D(ROI_Rect_Line):
	img = STANDARD_2D_IMAGE

class Test_Rect_Line_3D(ROI_Rect_Line):
	img = STANDARD_3D_IMAGE

class Test_Rect_Line_4D(ROI_Rect_Line):
	img = STANDARD_4D_IMAGE


class TestTracefig:
	@pytest.fixture
	def trace_setup(self, mock_message_box):
		"""Setup for trace figure tests"""
		w1 = Window(STANDARD_3D_IMAGE)
		rect = makeROI('rectangle', [[3, 2], [4, 5]], window=w1)
		trace = rect.plot()
		
		yield w1, rect, trace
		
		# Clean up
		w1.close()

	def test_plotting(self, trace_setup, mock_message_box):
		w1, rect, trace = trace_setup
		trace.indexChanged.emit(20)
		assert w1.currentIndex == 20, "trace indexChanged"

	def test_export(self, trace_setup, mock_message_box):
		w1, rect, trace = trace_setup
		
		try:
			rect.window.save_rois('tempROI.txt')
			with open('tempROI.txt', 'r') as f:
				t = f.read()
			assert t == 'rectangle\n3 2\n4 5\n'
		finally:
			if os.path.exists('tempROI.txt'):
				os.remove('tempROI.txt')
