# -*- coding: utf-8 -*-
"""
Trace display module for flika - provides visualization of ROI traces.
"""

import os
import time
from typing import Any, TypedDict

import numpy as np
import pyqtgraph as pg
from pyqtgraph.dockarea import Dock, DockArea
from qtpy import QtCore, QtGui, QtWidgets
from scipy.fftpack import fft, fftfreq

import flika.global_vars as g
from flika.logger import logger
from flika.roi import ROI_Base
from flika.utils.misc import save_file_gui
from flika.utils.pyqtgraph_patch import apply_pyqtgraph_patches, safe_disconnect

# Apply PyQtGraph patches to prevent errors during cleanup
apply_pyqtgraph_patches()


class ROIDict(TypedDict, total=False):
    """TypedDict for ROI information stored in TraceFig"""

    roi: ROI_Base
    p1trace: pg.PlotDataItem
    p2trace: pg.PlotDataItem
    toBeRedrawn: bool
    toBeRedrawnFull: bool
    power_spectrum_x: np.ndarray
    power_spectrum_y: np.ndarray


class TraceFig(QtWidgets.QWidget):
    """Pyqtgraph PlotWidget with frame range selector. Display average trace of ROIs and updates in realtime.

    Attributes:
        p1 (pg.PlotWidget): top plot widget displaying selected region of traces
        p2 (pg.PlotWidget): bottom plot widget displaying entire traces with region selection
        rois ([dict]): list of roi information dicts for reference

    Signals:
        :indexChanged(int): emits the index of the mouse when the user hovers over the top plotWidget
        :finishedDrawingSignal(): emits when the bottom ROI is finished updating
        :keyPressSignal(QtCore.QEvent): emits when the traceWindow is selected and a key is pressed
        :partialThreadUpdatedSignal(): emits when the top plot widget is updated
    """

    indexChanged = QtCore.Signal(int)
    finishedDrawingSignal = QtCore.Signal()
    keyPressSignal = QtCore.Signal(object)  # Using object instead of QEvent
    partialThreadUpdatedSignal = QtCore.Signal()
    name: str = "Trace Widget"

    def __init__(self) -> None:
        super().__init__()
        g.traceWindows.append(self)
        self.setCurrentTraceWindow()
        if (
            "tracefig_settings" in g.settings
            and "coords" in g.settings["tracefig_settings"]
        ):
            self.setGeometry(QtCore.QRect(*g.settings["tracefig_settings"]["coords"]))
        else:
            self.setGeometry(QtCore.QRect(355, 30, 1219, 148))
        self.setWindowTitle("flika")
        self.l = QtWidgets.QVBoxLayout()

        self.l.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.l)
        self.p1 = pg.PlotWidget()
        self.p2 = pg.PlotWidget()
        self.p1.getPlotItem().axes["left"]["item"].setGrid(
            100
        )  # this makes faint horizontal lines
        self.p2.setMaximumHeight(50)
        self.export_button = QtWidgets.QPushButton("Export")
        self.export_button.setMaximumWidth(100)
        self.export_button.clicked.connect(self.export_gui)
        self.power_spectrum_button = QtWidgets.QPushButton("Power Spectrum")
        self.power_spectrum_button.setMaximumWidth(100)
        self.power_spectrum_button.clicked.connect(self.generate_power_spectrum)
        self.button_layout = QtWidgets.QGridLayout()
        self.l.addWidget(self.p1, 1)
        self.l.addWidget(self.p2, 1)
        self.l.addLayout(self.button_layout)
        self.button_layout.setContentsMargins(0, 0, 0, 0)
        self.button_layout.addWidget(self.export_button, 0, 0)
        self.button_layout.addWidget(self.power_spectrum_button, 0, 1)
        # Using constants avoids linter warnings about missing attributes
        expanding = QtWidgets.QSizePolicy.Policy.Expanding
        minimum = QtWidgets.QSizePolicy.Policy.Minimum
        verticalSpacer = QtWidgets.QSpacerItem(10, 10, expanding, minimum)
        self.button_layout.addItem(verticalSpacer, 0, 2)

        # Add the LinearRegionItem to the ViewBox, but tell the ViewBox to exclude this item
        # when doing auto-range calculations.
        self.region = pg.LinearRegionItem()
        self.region.setZValue(10)
        self.p2.plotItem.addItem(self.region, ignoreBounds=True)
        self.p1.setAutoVisible(y=True)
        self.rois: list[
            ROIDict
        ] = []  # roi in this list is a dict: {roi, p1trace, p2trace, sigproxy}
        self.redrawPartialThread: "RedrawPartialThread | None" = None
        self.vb = self.p1.plotItem.getViewBox()

        self.proxy = pg.SignalProxy(
            self.p1.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved
        )
        self.p2.plotItem.vb.mouseDragEvent = self.mouseDragEvent2

        self.region.sigRegionChanged.connect(self.update_region)
        self.p1.plotItem.sigRangeChanged.connect(self.updateRegion)
        self.region.setRegion([0, 200])

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.p1.update)
        self.timer.start()

        from flika.process.measure import measure

        self.measure = measure
        self.p1.scene().sigMouseClicked.connect(self.measure.pointclicked)
        self.p1.scene().sigMouseClicked.connect(self.setCurrentTraceWindow)

        # Override QWidget events with our custom handlers
        self.original_resize_event = self.resizeEvent
        self.original_move_event = self.moveEvent
        self.resizeEvent = self.onResize  # type: ignore
        self.moveEvent = self.onMove  # type: ignore

        if "tracefig_settings" not in g.settings:
            g.settings["tracefig_settings"] = dict()
            try:
                g.settings["tracefig_settings"]["coords"] = self.geometry().getRect()
            except Exception as e:
                if hasattr(g, "alert"):
                    g.alert(e)
        self.show()

    def onResize(self, event: QtGui.QResizeEvent) -> None:
        """Handle resize events"""
        g.settings["tracefig_settings"]["coords"] = self.geometry().getRect()
        # Call the original resize event handler
        super().resizeEvent(event)

    def onMove(self, event: QtGui.QMoveEvent) -> None:
        """Handle move events"""
        g.settings["tracefig_settings"]["coords"] = self.geometry().getRect()
        # Call the original move event handler
        super().moveEvent(event)

    def setCurrentTraceWindow(self, ev: None | Any = None) -> None:
        pg.GraphicsScene.mousePressEvent
        """Set this window as the current trace window

        Args:
            ev: pyqtgraph.GraphicsScene.mouseEvents.MouseClickEvent. For some reason I cannot import this type.
                AttributeError: type object 'GraphicsScene' has no attribute 'MouseClickEvent'.
                pyqtgraph v0.13.7.
        """
        if g.currentTrace is not None:
            g.currentTrace.setStyleSheet("border:1px solid rgb(0, 0, 0); ")
        self.setStyleSheet("border:1px solid rgb(0, 255, 0); ")
        g.currentTrace = self  # type: ignore

    def mouseDragEvent2(self, ev: Any) -> None:
        """Prevent actions on mouse drag in plot2"""
        ev.ignore()  # prevent anything from happening

    def mouseDragEvent1(self, ev: Any) -> None:
        """Prevent actions on mouse drag in plot1"""
        ev.ignore()  # prevent anything from happening

    def keyPressEvent(self, ev: QtGui.QKeyEvent) -> None:
        """Emit signal when key is pressed"""
        self.keyPressSignal.emit(ev)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """Handle cleanup when window is closed"""
        # Import utility for safe disconnection

        # Clean up signals
        if hasattr(self, "proxy") and self.p1 is not None:
            safe_disconnect(self.p1.scene().sigMouseMoved)
            self.proxy = None

        # Disconnect the region signal and remove it from plot
        if hasattr(self, "region") and self.region is not None:
            safe_disconnect(self.region.sigRegionChanged)
            if self.p2 and self.p2.plotItem:
                try:
                    self.p2.plotItem.removeItem(self.region)
                except Exception as e:
                    logger.error(e)
                    pass

        # Clean up ROIs
        while len(self.rois) > 0:
            self.removeROI(0)

        # Stop timer
        if hasattr(self, "timer") and self.timer is not None:
            self.timer.stop()
            safe_disconnect(self.timer.timeout)

        # Remove from global trackers
        if self in g.traceWindows:
            g.traceWindows.remove(self)
        g.currentTrace = None

        event.accept()

    def update_region(
        self, lri: pg.graphicsItems.LinearRegionItem.LinearRegionItem
    ) -> None:
        """Update the displayed region in the main plot

        Renamed from update() to avoid conflict with QWidget's update method.
        """
        self.region.setZValue(10)
        minX, maxX = self.region.getRegion()
        self.p1.plotItem.setXRange(minX, maxX, padding=0, update=False)
        self.p1.plotItem.axes["bottom"]["item"].setRange(minX, maxX)

    def updateRegion(
        self, window: pg.ViewBox, viewRange: list[list[float | int]]
    ) -> None:
        """Update region selector based on view range changes"""
        rgn = viewRange[0]
        self.region.setRegion(rgn)

    def getBounds(self) -> list[int]:
        """Get the integer bounds of the currently selected region"""
        bounds = self.region.getRegion()
        bounds = [int(np.floor(bounds[0])), int(np.ceil(bounds[1])) + 1]
        return bounds

    def mouseMoved(self, evt: tuple[Any, ...]) -> None:
        """Handle mouse movement over the plot"""
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        shift_modifier = (
            QtCore.Qt.KeyboardModifier.ShiftModifier
        )  # Use enum to avoid linter warning

        if modifiers == shift_modifier:
            pass
        else:
            pos = evt[0]  # using signal proxy turns original arguments into a tuple
            if self.p1.plotItem.sceneBoundingRect().contains(pos):
                mousePoint = self.vb.mapSceneToView(pos)
                index = int(mousePoint.x())
                if index >= 0:
                    # self.label.setText("<span style='font-size: 12pt'>frame={0}</span>".format(index))
                    self.indexChanged.emit(index)
                    if (
                        hasattr(g, "m")
                        and g.m is not None
                        and hasattr(g.m, "statusBar")
                    ):
                        g.m.statusBar().showMessage(
                            f"frame {index}    y={mousePoint.y()}"
                        )

    def get_roi_index(self, roi: ROI_Base) -> int:
        """Get the index of an ROI in the rois list"""
        return [r["roi"] for r in self.rois].index(roi)

    def alert(self, msg: str) -> None:
        """Display an alert message (currently disabled)"""
        # print(msg)
        pass

    def translated(self, roi: ROI_Base) -> None:
        """Handle ROI translation and start redraw thread if needed"""
        index = self.get_roi_index(roi)
        self.rois[index]["toBeRedrawn"] = True
        if self.redrawPartialThread is None or self.redrawPartialThread.isFinished():
            self.alert("Launching redrawPartialThread")
            self.redrawPartialThread = RedrawPartialThread(self)
            self.redrawPartialThread.alert.connect(self.alert)
            self.redrawPartialThread.start()
            self.redrawPartialThread.updated.connect(
                self.partialThreadUpdatedSignal.emit
            )

    def translateFinished(self, roi: ROI_Base) -> None:
        """Handle completion of ROI translation"""
        roi_index = self.get_roi_index(roi)
        if (
            self.redrawPartialThread is not None
            and self.redrawPartialThread.isRunning()
        ):
            self.redrawPartialThread.quit_loop = True
            # self.redrawPartialThread.finished_sig.emit() #tell the thread to finish
            # loop = QtCore.QEventLoop()
            # self.redrawPartialThread.finished.connect(loop.quit)
            # loop.exec_()# This blocks until the "finished" signal is emitted
        trace = roi.getTrace()
        if trace is not None:
            self.update_trace_full(roi_index, trace)

    def update_trace_full(self, roi_index: int, trace: np.ndarray) -> None:
        """Update the complete trace display for an ROI"""
        pen = QtGui.QPen(self.rois[roi_index]["roi"].pen)
        self.rois[roi_index]["p1trace"].setData(trace, pen=pen)
        self.rois[roi_index]["p2trace"].setData(trace, pen=pen)
        self.finishedDrawingSignal.emit()

    def addROI(self, roi: ROI_Base) -> None:
        """Add an ROI to the trace display"""
        if self.hasROI(roi):
            return
        trace = roi.getTrace()
        if trace is None:
            raise InvalidTraceException()
        pen = QtGui.QPen(roi.pen)
        pen.setWidth(0)
        if len(trace) == 1:
            p1trace = self.p1.plot(trace, pen=None, symbol="o")
            p2trace = self.p2.plot(trace, pen=None, symbol="o")
        else:
            p1trace = self.p1.plot(trace, pen=pen)
            p2trace = self.p2.plot(trace, pen=pen)

        # Check if methods exist before connecting signals
        if hasattr(roi, "sigRegionChanged"):
            roi.sigRegionChanged.connect(self.translated)
        if hasattr(roi, "sigRegionChangeFinished"):
            roi.sigRegionChangeFinished.connect(self.translateFinished)

        if len(self.rois) == 0:
            self.region.setRegion([0, len(trace) - 1])

        new_roi: ROIDict = {
            "roi": roi,
            "p1trace": p1trace,
            "p2trace": p2trace,
            "toBeRedrawn": False,
            "toBeRedrawnFull": False,
        }
        self.rois.append(new_roi)

    def removeROI(self, roi: ROI_Base | int) -> None:
        """Remove an ROI from the trace display"""

        if isinstance(roi, ROI_Base):
            # this is the index of the roi in self.rois
            index = [r["roi"] for r in self.rois].index(roi)
        elif isinstance(roi, int):
            index = roi
        else:
            if hasattr(g, "alert"):
                g.alert(f"Failed to remove roi {roi}")
            return

        self.p1.removeItem(self.rois[index]["p1trace"])
        self.p2.removeItem(self.rois[index]["p2trace"])
        self.rois[index]["roi"].traceWindow = None
        try:
            self.rois[index]["roi"].resetSignals()
        except Exception:
            pass
        del self.rois[index]
        if len(self.rois) == 0:
            self.close()

    def hasROI(self, roi: ROI_Base) -> bool:
        """Check if the ROI is already in the trace display"""
        return roi in [r["roi"] for r in self.rois]  # return True if roi is plotted

    def export_gui(self) -> bool:
        """Show GUI for exporting traces"""
        filename = g.settings.get("filename")
        directory = os.path.dirname(filename) if filename is not None else ""
        if filename is not None:
            filename = save_file_gui("Save Traces", directory, "*.txt")
        else:
            filename = save_file_gui("Save Traces", "", "*.txt")
        if filename == "":
            return False
        else:
            self.export(filename)
            return True

    def export(self, filename: str) -> None:
        """Export traces to a file

        This function saves all the traces in the tracefig to a file specified by the argument 'filename'.
        The output file is a tab separated ascii file where each column is a trace.
        Traces are saved in the order they were added to the plot.
        """
        if hasattr(g, "m") and g.m is not None and hasattr(g.m, "statusBar"):
            g.m.statusBar().showMessage(f"Saving {os.path.basename(filename)}")

        traces = []
        for roi in self.rois:
            trace = roi["roi"].getTrace()
            if trace is not None:
                traces.append(trace)

        if not traces:
            return

        traces_array = [np.arange(len(traces[0]))]
        traces_array.extend(traces)
        np_traces = np.array(traces_array).T
        np.savetxt(filename, np_traces, delimiter="\t", fmt="%10f")

        if hasattr(g, "m") and g.m is not None and hasattr(g.m, "statusBar"):
            g.m.statusBar().showMessage(
                f"Successfully saved {os.path.basename(filename)}"
            )

    def generate_power_spectrum(self) -> None:
        """Create and display power spectrum analysis of the traces"""
        sample_interval = 1
        self.fft_analyzer = FFT_Analyzer(self.rois, sample_interval, self)


class FFT_Analyzer(QtWidgets.QWidget):
    """Widget for analyzing and displaying FFT power spectrum of traces"""

    def __init__(
        self,
        rois: list[ROIDict],
        sample_interval: float | int,
        tracefig: TraceFig,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        """
        Initialize FFT analyzer

        Args:
            rois: List of ROI dictionaries to analyze
            sample_interval: Sample duration in seconds. If sample is 1000 Hz, sample_interval = .001 (1 ms)
            tracefig: Parent TraceFig widget
            parent: Parent widget
        """
        super().__init__(parent)
        self.tracefig = tracefig
        self.rois = rois
        geo = self.tracefig.geometry()
        geo.adjust(0, geo.height(), 0, geo.height())
        self.setGeometry(geo)
        self.setWindowTitle("Power Spectrum")
        self.l = QtWidgets.QVBoxLayout()
        self.setLayout(self.l)
        self.area = DockArea()
        self.l.addWidget(self.area)

        self.d3 = Dock("FFT")
        self.area.addDock(self.d3, size=(382, 216))
        self.fftplt = pg.PlotWidget()
        self.d3.addWidget(self.fftplt)
        self.fftplt.showGrid(x=True, y=True)
        self.fftplt.setLogMode(x=True, y=True)
        self.fftplt.setLabel("bottom", "Frequency")
        self.fftplt.setLabel("left", "Power")
        self.sample_interval = sample_interval
        self.set_data(rois, self.sample_interval)

        self.export_button = QtWidgets.QPushButton("Export")
        self.export_button.setMaximumWidth(100)
        self.export_button.clicked.connect(self.export_gui)
        self.d3.addWidget(self.export_button)
        self.show()

    def set_data(self, rois: list[ROIDict], sample_interval: float | int) -> None:
        """Calculate and display power spectrum for each ROI trace"""
        traces = []
        pens = []
        for roi in rois:
            trace = roi["roi"].getTrace()
            if trace is not None:
                traces.append(trace)
                pen = QtGui.QPen(roi["roi"].pen)
                pen.setWidth(0)
                pens.append(pen)

        if not traces:
            return

        longest_trace_len = max(len(trace) for trace in traces)
        N = int(2 ** np.floor(np.log2(longest_trace_len)))
        # x = np.linspace(0.0, N * sample_interval, N)
        for i in range(len(traces)):
            if i >= len(rois):
                break

            trace = traces[i]
            yf = fft(trace[-N:])
            xf = fftfreq(N, sample_interval)
            xf = xf[1 : int(N / 2)]
            yf = np.abs(yf[1 : int(N / 2)]) ** 2
            rois[i]["power_spectrum_x"] = xf
            rois[i]["power_spectrum_y"] = yf
            self.fftplt.plot(xf, yf, pen=pens[i])

    def export_gui(self) -> bool:
        """Show GUI for exporting power spectrum data"""
        filename = g.settings.get("filename")
        directory = os.path.dirname(filename) if filename is not None else ""
        if filename is not None:
            filename = save_file_gui("Save Power Spectrum", directory, "*.csv")
        else:
            filename = save_file_gui("Save Power Spectrum", "", "*.csv")
        if filename == "":
            return False
        else:
            self.export(filename)
            return True

    def export(self, filename: str) -> None:
        """Export power spectrum data to a CSV file

        This function saves all the traces in the 'Power Spectrum" to a file specified by the argument 'filename'.
        The output file is a CSV.
        Traces are saved in the order they were added to the tracefig window.
        """
        if hasattr(g, "m") and g.m is not None and hasattr(g.m, "statusBar"):
            g.m.statusBar().showMessage(f"Saving {os.path.basename(filename)}")

        headers = []
        cols = []
        for i, roi in enumerate(self.rois):
            if "power_spectrum_x" in roi and "power_spectrum_y" in roi:
                cols.append(roi["power_spectrum_x"])
                cols.append(roi["power_spectrum_y"])
                headers.append(f"X roi{i}")
                headers.append(f"Y roi{i}")

        if not cols:
            return

        header = ",".join(headers)
        cols_array = np.array(
            cols
        ).T  # Create explicitly named variable for type clarity
        np.savetxt(
            filename, cols_array, header=header, delimiter=",", comments="", fmt="%10f"
        )
        if hasattr(g, "m") and g.m is not None and hasattr(g.m, "statusBar"):
            g.m.statusBar().showMessage(
                f"Successfully saved {os.path.basename(filename)}"
            )


def roiPlot(roi: ROI_Base) -> TraceFig | None:
    """Plot an ROI in a trace window

    Args:
        roi: The ROI to plot

    Returns:
        The trace window used for plotting, or None if plotting failed
    """
    if g.settings.get("multipleTraceWindows", False) or g.currentTrace is None:
        win = TraceFig()
    else:
        win = g.currentTrace
    try:
        win.addROI(roi)
    except InvalidTraceException:
        if len(win.rois) == 0:
            win.close()
            return None
    return win


class RedrawPartialThread(QtCore.QThread):
    """Thread for redrawing traces in the background"""

    finished = QtCore.Signal()  # this announces that the thread has finished
    finished_sig = QtCore.Signal()  # This tells the thread to finish
    alert = QtCore.Signal(str)
    updated = QtCore.Signal()  # This signal is emitted after each redraw

    def __init__(self, tracefig: TraceFig) -> None:
        """Initialize redraw thread for a trace window"""
        super().__init__()
        self.tracefig = tracefig
        self.redrawCompleted = True
        self.quit_loop = False

    def run(self) -> None:
        """Main thread execution loop"""
        self.finished_sig.connect(self.request_quit_loop)
        while not self.quit_loop:
            time.sleep(0.05)
            self.redraw()
            self.updated.emit()
        self.alert.emit("Finished Redraw")
        self.finished.emit()

    def request_quit_loop(self) -> None:
        """Signal thread to exit"""
        self.quit_loop = True

    def redraw(self) -> None:
        """Redraw ROI traces that need updating"""
        if not self.redrawCompleted:
            self.alert.emit("Redraw hasn't finished")
            return

        self.alert.emit("Redrawing")
        self.redrawCompleted = False
        idxs = []
        for i in range(len(self.tracefig.rois)):
            if self.tracefig.rois[i]["toBeRedrawn"]:
                self.tracefig.rois[i]["toBeRedrawn"] = False
                idxs.append(i)

        traces = []
        bounds = self.tracefig.getBounds()
        bounds = [max(0, bounds[0]), bounds[1]]

        for i in idxs:
            roi = self.tracefig.rois[i]["roi"]
            trace = roi.getTrace(bounds)
            if trace is not None:
                traces.append(trace)
            else:
                # If trace is None, append an empty array as a placeholder
                traces.append(np.array([]))

        for i, roi_index in enumerate(idxs):
            if len(traces[i]) == 0:
                continue  # Skip empty traces

            trace = traces[i]  # This function can sometimes take a long time.
            pen = QtGui.QPen(self.tracefig.rois[roi_index]["roi"].pen)
            bb = self.tracefig.getBounds()
            curve = self.tracefig.rois[roi_index]["p1trace"]
            newtrace = curve.getData()[1]

            if bb[0] < 0:
                bb[0] = 0
            if bb[1] > len(newtrace):
                bb[1] = len(newtrace)
            if bb[1] < 0 or bb[0] > len(newtrace):
                return

            newtrace[bb[0] : bb[1]] = trace
            curve.setData(newtrace, pen=pen)
            self.alert.emit(f"CURVE {roi_index} redrawn")
            QtWidgets.QApplication.processEvents()

        self.redrawCompleted = True


class InvalidTraceException(Exception):
    """Exception raised when an ROI has no valid trace data"""

    pass
