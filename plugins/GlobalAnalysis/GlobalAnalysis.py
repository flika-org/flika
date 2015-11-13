from PyQt4 import uic
import global_vars as g
import pyqtgraph as pg
from .GlobalPolyfit import *
from window import Window
from roi import ROI
from analyze.measure import measure
print("GlobalAnalysis imported")

def gui():
	ui = uic.loadUi(os.path.join(os.getcwd(), 'plugins\\GlobalAnalysis\\main.ui'))
	ui.addPolyButton.clicked.connect(add_polyfit_item)
	ui.autoROIButton.clicked.connect(makeROIs)
	ui.measureButton.clicked.connect(measure.gui)
	ui.sliderCheck.toggled.connect(setIsoVisible)
	ui.show()
	g.m.dialogs.append(ui)

def add_polyfit_item():
	rangeItem = ROIRange()
	g.m.currentTrace.p1.addItem(rangeItem)
	rangeItem.__name__ = "%s Range %d" % (g.m.currentTrace.name, rangeItem.id)

	rangeItem.poly_pen = QPen(QColor(255, 0, 0))
	rangeItem.poly_pen.setStyle(Qt.DashLine)
	rangeItem.poly_pen.setDashOffset(5)
	#g.m.currentTrace.p1.menu.addMenu(rangeItem.menu)
	#rangeItem.sigRemoved.connect(lambda : g.m.currentTrace.rangeMenu.removeAction(rangeItem.menu.menuAction()))

	rangeItem.poly_fill = QGraphicsPathItem()
	rangeItem.poly_fill.setBrush(QColor(0, 100, 155, 100))
	rangeItem.polyfit_item = pg.PlotDataItem(pen=rangeItem.poly_pen)
	rangeItem.fall_rise_points = pg.ScatterPlotItem()

	rangeItem.poly_fill.setParentItem(rangeItem)
	rangeItem.polyfit_item.setParentItem(rangeItem)
	rangeItem.fall_rise_points.setParentItem(rangeItem)
	rangeItem.sigRegionChangeFinished.connect(lambda : onRegionMove(rangeItem))
	onRegionMove(rangeItem)

def makeROIs():
	if not hasattr(g.m.currentWindow, 'iso'):
		print('Must show the LUT Slider to draw ROIs')
	length = int(g.m.currentWindow.iso.path.length())
	p = g.m.currentWindow.iso.path.pointAtPercent(0)
	p = (p.x(), p.y())
	last_p = p
	cur_roi = ROI(g.m.currentWindow, p[0], p[1])
	for i in range(1, length):
		p = g.m.currentWindow.iso.path.pointAtPercent(i / length)
		p = (p.x(), p.y())
		if np.linalg.norm((last_p[0] - p[0], last_p[1] - p[1])) > 2:
			cur_roi.drawFinished()
			cur_roi = ROI(g.m.currentWindow, p[0], p[1])
		else:
			cur_roi.extend(p[0], p[1])
		last_p = p
	cur_roi.drawFinished()

def onRegionMove(region):
	''' when the region moves, recalculate the polyfit
	data and plot/show it in the table and graph accordingly'''
	x, y = region.getRegionTrace()
	ftrace = get_polyfit(x, y)
	data = analyze_trace(x, y, ftrace)
	region.polyfit_item.setData(x=x, y=ftrace, pen=region.poly_pen)
	integral = region.getIntegral()

	pos = [data[k] for k in data.keys() if k.startswith('Rise, Fall')]
	if len(pos) > 0:
		region.fall_rise_points.setData(pos=pos, pen=region.poly_pen, symbolSize=4)
	else:
		print("Cannot find points")
		region.fall_rise_points.clear()
	region.poly_fill.setPath(makePolyPath(x, ftrace, data['Baseline'][1]))
	if not hasattr(region, 'table_widget'):
		region.table_widget = pg.TableWidget(sortable=False, editable=False)
		region.table_widget.__name__ = '%s Polyfit Table' % region.__name__
		g.m.currentTrace.l.addWidget(region.table_widget)
		region.sigRemoved.connect(region.table_widget.close)
	region.table_widget.setData(data)
	region.table_widget.setHorizontalHeaderLabels(['Frames', 'Y', 'Ftrace Frames', 'Ftrace Y'])

def setIsoVisible(v):
	if not hasattr(g.m.currentWindow, 'iso'):
		if isinstance(g.m.currentWindow, Window):
			addIsoCurve(g.m.currentWindow)
	if g.m.currentWindow != None and hasattr(g.m.currentWindow, 'iso'):
		g.m.currentWindow.iso.setVisible(v)
		g.m.currentWindow.isoLine.setVisible(v)

def addIsoCurve(widg):
	lut = widg.imageview.getHistogramWidget().centralWidget
	widg.iso = pg.IsocurveItem(level=0.8, pen='g')
	widg.iso.setParentItem(widg.imageview.getImageItem())
	widg.iso.setZValue(5)
	widg.isoLine = pg.InfiniteLine(angle=0, movable=True, pen='g')
	lut.vb.addItem(widg.isoLine)
	#lut.vb.setMouseEnabled(y=False) # makes user interaction a little easier
	widg.isoLine.setValue(np.average(lut.getLevels()))
	widg.isoLine.setZValue(1000)
	widg.iso.setData(pg.gaussianFilter(widg.image[widg.currentIndex], (2, 2)))
	def updateIsocurve():
		widg.iso.setLevel(widg.isoLine.value())
	updateIsocurve()
	setIsoVisible(False)

	widg.isoLine.sigDragged.connect(updateIsocurve)
