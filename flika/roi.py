# -*- coding: utf-8 -*-
"""This module declares Region Of Interest (ROI) types as extensions of pyqtgraph.ROI objects.

Current ROI types are:
    * line
    * rectangle
    * freehand
    * rect_line

Example:
    >>> roi = makeROI('line', [[10, 10], [20, 15]])
    >>> roi.plot()
    >>> roi.copy()
    >>> win2 = open_file()
    >>> roi2 = win2.paste()

Todo:
    * Correct ROI line handles to be at center of pixel
"""

# Standard library imports
import os

import beartype
import jaxtyping
import numpy as np
import pyqtgraph as pg
import skimage.draw
from pyqtgraph.graphicsItems.ROI import Handle
from qtpy import QtCore, QtGui, QtWidgets

import flika.global_vars as g
from flika.utils.misc import nonpartial, open_file_gui, random_color


@beartype.beartype
class ROI_Drawing(pg.GraphicsObject):
    """Graphics Object for ROIs while initially being drawn. Extends pyqtrgaph.GraphicsObject

    Only used on initial mouse drag, the drawFinished method returns the
    resulting ROI object which can then be modified

    Attributes:
        window (window.Window): Window object to draw the ROI in
        x (int): x coordinate of mouse press
        y (int): y coordinate of mouse press
        kind (str): one of ['rectangle', 'line', 'freehand', 'rect_line']
        color (QtGui.QColor): pen color to draw ROI with
    """

    def __init__(self, window, x: int | float, y: int | float, kind: str):
        pg.GraphicsObject.__init__(self)
        window.imageview.addItem(self)
        self.window = window
        self.pts: list[pg.Point.Points] = [pg.Point(round(x), round(y))]
        self.kind: str = kind
        self.state: dict[str, pg.Point.Points] = {
            "pos": pg.Point(x, y),
            "size": pg.Point(0, 0),
        }
        self.color: QtGui.QColor = (
            QtGui.QColor(g.settings["roi_color"])
            if g.settings["roi_color"] != "random"
            else random_color()
        )
        self.mouseHovering: bool = False

    def cancel(self):
        g.win.imageview.removeItem(self)
        g.win.currentROI = None
        self.deleteLater()

    def extend(self, x: int | float, y: int | float):
        new_pt = pg.Point(round(x), round(y))
        if self.kind == "freehand":
            if self.pts[-1] != new_pt:
                self.pts.append(new_pt)
        elif self.kind in ("line", "rectangle", "rect_line"):
            if len(self.pts) == 1:
                self.pts.append(new_pt)
            else:
                self.pts[1] = new_pt

            # self.pts = sorted(self.pts, key=lambda a: a.x()/a.y())

        self.state["pos"] = pg.Point(*np.min(self.pts, 0))
        self.state["size"] = pg.Point(*np.ptp(self.pts, 0))

        self.prepareGeometryChange()
        self.update()

    def paint(self, p: QtGui.QPainter, *args):
        pen = QtGui.QPen(self.color)
        pen.setWidth(0)
        p.setPen(pen)
        if self.kind == "freehand":
            p.drawPolyline(self.pts)
        elif self.kind == "rectangle":
            p.drawRect(self.boundingRect())
        elif self.kind in ("rect_line", "line"):
            p.drawLine(*self.pts)

    def drawFinished(self):
        self.window.imageview.removeItem(self)
        if self.kind == "rectangle":
            pts = [self.state["pos"], self.state["size"]]
        else:
            pts = self.pts
        return makeROI(self.kind, pts, self.window, color=self.color)

    def contains(self, *args):
        if len(args) == 2:
            args = [pg.Point(*args)]
        return pg.GraphicsObject.contains(self, *args)

    def boundingRect(self):
        pos_x: int | float = self.state["pos"].x()
        pos_y: int | float = self.state["pos"].y()
        size_x: int | float = self.state["size"].x()
        size_y: int | float = self.state["size"].y()
        return QtCore.QRectF(pos_x, pos_y, size_x, size_y)


@beartype.beartype
class ROI_Base:
    """ROI_Base interface for all ROI types

    Template class for common and abstract functions, connects window.closeEvent to pyqtgraph.ROI.delete, set the window.currentROI to self

    Attributes:
        colorDialog: dialog for selecting the color of the ROI and its trace
        traceWindow: the :class:`TraceFig <flika.tracefig.TraceFig>` that this ROI is plotted to, or None
        pts: array of XY values used to copy the ROI
        linkedROIs: set of rois that act as one ROI

    Note:
        All ROI objects implement the following methods:
            getMask():
                returns the [2, N] array of mask coordinates
            getPoints():
                returns the [N, 2] points that make up the ROI
            draw_from_points(pts, finish=True):
                updates the point locations that make the ROI, used in linked ROIs

    """

    INITIAL_ARGS = {
        "translateSnap": True,
        "removable": True,
        "snapSize": 1,
        "scaleSnap": True,
    }
    # plotSignal = QtCore.Signal()

    def __init__(self, window, pts):
        self.window = window  #: window.Window: Parent window that this ROI belongs to
        self.colorDialog = QtWidgets.QColorDialog()
        self.colorDialog.colorSelected.connect(self.colorSelected)
        self.window.closeSignal.connect(self.delete)
        self.window.currentROI = self
        self.traceWindow = None  #: tracefig.TraceFig: the Trace window that this ROI is plotted in. To test if roi is plotted, check 'roi.traceWindow is None'
        self._trace_signal_connected = False  # Initialize tracking variable
        self.pts = np.array(
            pts
        )  #: list: Array of points that make up the boundary of the ROI
        self.linkedROIs = set()
        self.resetSignals()
        self.makeMenu()
        self.pen = pg.mkPen(QtGui.QColor(255, 255, 255))
        self.currentPen = self.pen
        self.mouseHovering = False

    def trigger_plot_signal(self):
        pass
        # self.plotSignal.emit()

    def mouseClickEvent(self, ev):
        self.window.currentROI = self
        super().mouseClickEvent(ev)

    def resetSignals(self):
        """
        Safely disconnect and reconnect signals, or just connect them if they weren't connected before.
        This function is designed to be idempotent - it can be called multiple times safely.
        """
        # Define markers to track if signals were connected
        if not hasattr(self, "_signals_connected"):
            self._signals_connected = False

        # Create safer signal disconnection helper
        def safe_disconnect(signal, slot):
            try:
                # Use QtCore.SignalInstance.disconnect syntax which is safer
                if isinstance(signal, QtCore.SignalInstance):
                    signal.disconnect(slot)
                else:
                    signal.disconnect()
            except (TypeError, RuntimeError, AttributeError):
                # Silently ignore all exceptions
                pass

        # Only try disconnecting if we previously connected signals
        if self._signals_connected:
            # Handle sigRegionChanged signal
            if hasattr(self, "sigRegionChanged"):
                safe_disconnect(self.sigRegionChanged, self.onRegionChange)

            # Handle sigRegionChangeFinished signal
            if hasattr(self, "sigRegionChangeFinished"):
                safe_disconnect(
                    self.sigRegionChangeFinished, self.onRegionChangeFinished
                )

            # Reset connection tracking
            self._signals_connected = False

        # Now connect signals to their slots
        if hasattr(self, "sigRegionChanged"):
            try:
                self.sigRegionChanged.connect(self.onRegionChange)
                self._signals_connected = True
            except Exception:
                pass

        if hasattr(self, "sigRegionChangeFinished"):
            try:
                self.sigRegionChangeFinished.connect(self.onRegionChangeFinished)
                self._signals_connected = True
            except Exception:
                pass

    def updateLinkedROIs(self, finish=False):
        for roi in self.linkedROIs:
            roi.blockSignals(True)
            roi.draw_from_points(self.pts, finish=False)
            if roi.traceWindow is not None:
                if not finish:
                    roi.traceWindow.translated(roi)
                else:
                    roi.traceWindow.translateFinished(roi)
            roi.blockSignals(False)

    def redraw_trace(self):
        """Emit the translateFinished signal which redraws the ROI trace"""
        if self.traceWindow is not None:
            self.traceWindow.translateFinished(self)

    def onRegionChange(self):
        self.pts = self.getPoints()
        self.updateLinkedROIs(finish=False)

    def onRegionChangeFinished(self):
        self.pts = self.getPoints()
        self.updateLinkedROIs(finish=True)

    def link(self, roi: "ROI_Base"):
        """Link this roi to another, so a translation of one will cause a translation of the other"""
        if not isinstance(roi, type(self)):
            return
        join = self.linkedROIs | roi.linkedROIs | {self, roi}
        self.linkedROIs = join - {self}
        roi.linkedROIs = join - {roi}

    def getMask(self):
        """Returns the list of integer points contained within the ROI, differs by ROI type"""
        raise NotImplementedError()

    def getTrace(
        self, bounds: list[int] | None = None
    ) -> jaxtyping.Float[np.ndarray, "t"] | None:
        """Compute the average of the pixels within this ROI in its window

        Returns:
            Average value within ROI mask, as an array. Cropped to bounds if specified
        """
        trace: jaxtyping.Float[np.ndarray, "t"] | None
        if self.window.image.ndim == 4 or self.window.metadata["is_rgb"]:
            g.alert(
                "Plotting trace of RGB movies is not supported. Try splitting the channels."
            )
            return None
        s1, s2 = self.getMask()
        if np.size(s1) == 0 or np.size(s2) == 0:
            trace = np.zeros(self.window.mt, dtype=float)

        elif self.window.image.ndim == 3:
            trace = self.window.image[:, s1, s2]
            if trace is not None:
                while trace.ndim > 1:
                    trace = np.average(trace, 1)
        elif self.window.image.ndim == 2:
            trace = self.window.image[s1, s2]
            if trace is not None:
                trace = np.array([np.average(trace)])
        if bounds and trace is not None:
            trace = trace[bounds[0] : bounds[1]]
        return trace

    def getPoints(self) -> jaxtyping.Float[np.ndarray, "n 2"]:
        """Get points that represent this ROI, used for exporting

        Returns:
            np.ndarray: An Nx2 array of points where each row is [x, y]
        """
        raise NotImplementedError()

    def draw_from_points(
        self, pts: jaxtyping.Float[np.ndarray, "n 2"], finish: bool = True
    ) -> None:
        """Redraw the ROI from the given points, used on linked ROIs

        Args:
            pts: points used to represent ROI, often handle positions. Shape is Nx2 array
            finish: whether or not to emit the onRegionChangeFinished signal
        """
        raise NotImplementedError()

    def setMouseHover(self, hover: bool):
        """
        Inform the ROI that the mouse is or is not hovering over it.

        Args:
            hover (bool)

        """
        if self.mouseHovering is hover:
            return
        self.mouseHovering = hover
        if hover:
            self.currentPen = pg.mkPen(QtGui.QColor(255, 0, 0))
        else:
            self.currentPen = self.pen

        self.update()

    def plot(self):
        """Plot the ROI trace in a :class:`TraceFig <flika.tracefig.TraceFig>`"""
        from .tracefig import roiPlot

        self.traceWindow = roiPlot(self)
        if self.traceWindow is None:
            return
        self.traceWindow.indexChanged.connect(self.window.setIndex)
        self._trace_signal_connected = True  # Track that we connected this signal
        self.plotSignal.emit()
        return self.traceWindow

    def changeColor(self) -> None:
        self.colorDialog.open()

    def colorSelected(self, color: QtGui.QColor) -> None:
        """Set the pen color of the ROI

        Args:
            color (QtGui.QColor): new color for the ROI
        """
        if color.isValid():
            self.setPen(QtGui.QColor(color.name()))
            self.sigRegionChangeFinished.emit(self)

    def unplot(self) -> None:
        """Remove the ROI from its :class:`TraceFig <flika.tracefig.TraceFig>`"""
        if self.traceWindow is not None:
            # Suppress any QT warnings from disconnection by using blockSignals
            old_state = None
            if hasattr(self.traceWindow, "blockSignals"):
                old_state = self.traceWindow.blockSignals(True)

            try:
                self.traceWindow.indexChanged.disconnect(self.window.setIndex)
                self._trace_signal_connected = False
            except Exception:
                # Explicitly ignore all errors in signal disconnection
                pass

            # Restore signal blocking state
            if hasattr(self.traceWindow, "blockSignals") and old_state is not None:
                self.traceWindow.blockSignals(old_state)

            self.traceWindow.removeROI(self)
            self.traceWindow = None

    def copy(self) -> None:
        """Store this ROI in the clipboard"""
        g.clipboard = self

    def raiseContextMenu(self, ev) -> None:
        pos: QtCore.QPoint = ev.screenPos()
        x: int = int(pos.x())
        y: int = int(pos.y())
        self.menu.addSeparator()
        self.menu.addActions(self.window.menu.actions())
        self.menu.popup(QtCore.QPoint(x, y))

    def makeMenu(self) -> None:
        def plotPressed():
            if plotAct.text() == "&Plot":
                self.plot()
            else:
                self.unplot()

        plotAct = QtWidgets.QAction("&Plot", self, triggered=plotPressed)
        colorAct = QtWidgets.QAction("&Change Color", self, triggered=self.changeColor)
        copyAct = QtWidgets.QAction("&Copy", self, triggered=self.copy)
        remAct = QtWidgets.QAction("&Delete", self, triggered=self.delete)
        self.menu = QtWidgets.QMenu("ROI Menu")

        def updateMenu() -> None:
            # plotAct.setEnabled(self.window.image.ndim > 2)
            plotAct.setText("&Plot" if self.traceWindow is None else "&Unplot")
            self.window.menu.aboutToShow.emit()

        self.menu.addAction(plotAct)
        self.menu.addAction(colorAct)
        self.menu.addAction(copyAct)
        self.menu.addAction(remAct)
        self.menu.aboutToShow.connect(updateMenu)

    def delete(self, optional_bool: bool | None = False) -> None:
        """Remove the ROI from its window, unlink all ROIs and delete the object

        As of 2025-03-15, I don't know where this optional bool comes from or
        what it's for, but I can see from beartype that it's coming in.
        """
        self.unplot()
        for roi in self.linkedROIs:
            if self in roi.linkedROIs:
                roi.linkedROIs.remove(self)
        if self in self.window.rois:
            self.window.rois.remove(self)
        self.window.currentROI = None
        self.window.imageview.removeItem(self)
        self.window.closeSignal.disconnect(self.delete)
        if g.clipboard == self:
            g.clipboard = None

    def drawFinished(self) -> None:
        self.window.imageview.addItem(self)
        self.window.rois.append(self)
        self.window.currentROI = self

    def _str(self) -> str:
        """Return ROI kind and points for easy export and import

        Returns:
            str: ROI string representation
        """
        s = self.kind + "\n"
        for x, y in self.pts:
            s += "{} {}\n".format(x, y)
        return s

    def showMask(self) -> "Window":
        """Create a new binary window that visualizes the ROI mask

        Returns:
            window.Window: created mask window
        """
        from .window import Window

        self.copy()
        im = np.zeros_like(self.window.imageview.getImageItem().image)
        s1, s2 = self.getMask()
        im[s1, s2] = 1
        w = Window(im)
        w.paste()
        return w


@beartype.beartype
class ROI_line(ROI_Base, pg.LineSegmentROI):
    """ROI Line class for selecting a straight line of pixels between two points.

    Extends from :class:`ROI_Base <flika.roi.ROI_Base>` and pyqtgraph pyqtgraph.LineSegmentROI

    Attributes:
        kymograph (Window): :class:`Window <flika.window.Window>` showing 2d kymograph.
    """

    kind = "line"
    plotSignal = QtCore.Signal()

    def __init__(self, window, positions, **kargs):
        roiArgs = self.INITIAL_ARGS.copy()
        roiArgs.update(kargs)
        pg.LineSegmentROI.__init__(self, positions=positions, **roiArgs)
        self.kymograph = None
        self.kymographAct = QtWidgets.QAction(
            "&Kymograph", self, triggered=self.update_kymograph
        )
        ROI_Base.__init__(self, window, positions)
        # self.snapPoints()

    def paint(self, p, *args):
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setPen(self.currentPen)
        h1 = self.handles[0]["item"].pos()
        h2 = self.handles[1]["item"].pos()
        p.drawLine(h1, h2)

    def resetSignals(self):
        ROI_Base.resetSignals(self)
        self.sigRegionChanged.connect(self.snapPoints)

    def snapPoints(self):
        """Correct ROI points to be at the center of pixels, for clarity"""
        fix = False
        self.blockSignals(True)
        for handle in self.handles:
            pos = handle["pos"]
            pos_snap = self.getSnapPosition(pg.Point(pos))  # + pg.Point(.5, .5)
            if not (pos == pos_snap):
                handle["item"].setPos(pos_snap)
                handle["pos"] = pos_snap
                fix = True

        self.blockSignals(False)
        # if fix:
        #    self.sigRegionChanged.emit(self)

    def draw_from_points(self, pts, finish=True):
        self.blockSignals(True)
        self.movePoint(self.handles[0]["item"], pts[0], finish=False)
        self.movePoint(self.handles[1]["item"], pts[1], finish=False)
        self.pts = pts
        self.blockSignals(False)
        if finish:
            self.sigRegionChangeFinished.emit(self)

    def delete(self):
        ROI_Base.delete(self)
        if self.kymograph:
            self.deleteKymograph()

    def getMask(self):
        x = np.array([p[0] for p in self.pts], dtype=int)
        y = np.array([p[1] for p in self.pts], dtype=int)
        xx, yy = skimage.draw.line(x[0], y[0], x[1], y[1])
        idx_to_keep = np.logical_not(
            (xx >= self.window.mx) | (xx < 0) | (yy >= self.window.my) | (yy < 0)
        )
        xx = xx[idx_to_keep]
        yy = yy[idx_to_keep]
        return xx, yy

    def getPoints(self) -> jaxtyping.Float[np.ndarray, "2 2"]:
        return np.array([handle["pos"] + self.state["pos"] for handle in self.handles])

    def makeMenu(self):
        ROI_Base.makeMenu(self)
        self.menu.addAction(self.kymographAct)
        self.kymographAct.setEnabled(
            self.window.image.ndim == 3 and not self.window.metadata["is_rgb"]
        )

    def update_kymograph(self):
        tif = self.window.image
        if tif.ndim != 3:
            g.alert("Can only kymograph a 3d movie")
            return

        xx, yy = self.getMask()
        mt = len(tif)
        if len(xx) == 0:
            return
        xx = np.array(xx)
        yy = np.array(yy)

        if len(xx) == 0:
            return
        mn = np.zeros((mt, len(xx)))
        for t in np.arange(mt):
            mn[t] = tif[t, xx, yy]
        mn = mn.T
        if self.kymograph is None:
            self.createKymograph(mn)
        else:
            self.kymograph.imageview.setImage(mn, autoLevels=False, autoRange=False)
            # self.kymograph.imageview.view.setAspectLocked(lock=True,ratio=mn.shape[1]/mn.shape[0])

    def createKymograph(self, mn):
        from .window import Window

        oldwindow = g.win
        name = oldwindow.name + " - Kymograph"
        self.kymograph = Window(mn, name, metadata=self.window.metadata)
        self.sigRegionChanged.connect(self.update_kymograph)
        self.kymograph.closeSignal.connect(self.deleteKymograph)
        self.sigRemoveRequested.connect(self.deleteKymograph)

    def deleteKymograph(self):
        self.kymograph.closeSignal.disconnect(self.deleteKymograph)
        self.sigRegionChanged.disconnect(self.update_kymograph)
        self.kymograph = None


@beartype.beartype
class ROI_rectangle(ROI_Base, pg.ROI):
    """ROI rectangle class for selecting a set width and height group of pixels on an image.

    Extends from :class:`ROI_Base <flika.roi.ROI_Base>` and pyqtgraph.ROI
    """

    kind = "rectangle"
    plotSignal = QtCore.Signal()

    def __init__(
        self,
        window,
        pos: jaxtyping.Num[np.ndarray, "2"] | tuple[int, int] | list[int] | pg.Point,
        size: jaxtyping.Num[np.ndarray, "2"] | tuple[int, int] | list[int] | pg.Point,
        resizable: bool = True,
        **kargs,
    ):
        """__init__ of ROI_rectangle class

        Args:
            pos: position of top left corner
            size: width and height of the rectangle
            resizable: add resize handles to ROI, this cannot be changed after creation
        """
        roiArgs = self.INITIAL_ARGS.copy()
        roiArgs.update(kargs)
        pos = np.array(pos, dtype=int)
        size = np.array(size, dtype=int)

        pg.ROI.__init__(self, pos, size, **roiArgs)
        if resizable:
            self.addScaleHandle([0, 1], [1, 0])
            self.addScaleHandle([1, 0], [0, 1])
            self.addScaleHandle([0, 0], [1, 1])
            self.addScaleHandle([1, 1], [0, 0])
        self.cropAction = QtWidgets.QAction("&Crop", self, triggered=self.crop)
        ROI_Base.__init__(self, window, [pos, size])

    def center_around(self, x: float | int, y: float | int) -> None:
        """Relocate ROI so center lies at Point (x, y). size is not changed

        Args:
            x (int): new center for rectangle on X axis
            y (int): new center for rectangle on Y axis
        """
        old_pts: jaxtyping.Num[np.ndarray, "2"] = self.getPoints()
        old_center = old_pts[0] + 0.5 * old_pts[1]
        new_center = np.array([x, y])
        diff = new_center - old_center
        new_pts = np.array([old_pts[0] + diff, old_pts[1]])
        self.draw_from_points(new_pts)

    def getPoints(self) -> jaxtyping.Integer[np.ndarray, "2 2"]:
        pos: jaxtyping.Integer[np.ndarray, "2"] = self.state["pos"]
        size: jaxtyping.Integer[np.ndarray, "2"] = self.state["size"]
        return np.array([pos, size], dtype=int)

    def contains_pts(self, x: float | int, y: float | int) -> bool:
        target: jaxtyping.Float[np.ndarray, "2"] = np.array([x, y])

        return bool(np.all(self.pts[0] < target)) and bool(
            np.all(target < self.pts[0] + self.pts[1])
        )

    def getMask(self) -> tuple[np.ndarray, np.ndarray]:
        x, y = self.state["pos"]
        ww, hh = self.state["size"]

        xmin = max(x, 0)
        ymin = max(y, 0)
        xmax = min(x + ww, self.window.mx)
        ymax = min(y + hh, self.window.my)

        xx, yy = np.meshgrid(
            np.arange(xmin, xmax, dtype=int), np.arange(ymin, ymax, dtype=int)
        )

        return xx.flatten(), yy.flatten()

    def draw_from_points(self, pts, finish=True):
        self.setPos(pts[0], finish=False)
        self.setSize(pts[1], finish=False)
        self.pts = np.array(pts)
        self.sigRegionChanged.emit(self)
        if finish:
            self.sigRegionChangeFinished.emit(self)

    def makeMenu(self):
        ROI_Base.makeMenu(self)
        self.menu.addAction(self.cropAction)

    def crop(self):
        """Create a new window of the image cropped to this ROI

        Returns:
            window.Window: cropped image Window
        """
        from .window import Window

        r = self.boundingRect()
        p1 = r.topLeft() + self.state["pos"]
        p2 = r.bottomRight() + self.state["pos"]
        x1, y1 = int(p1.x()), int(p1.y())
        x2, y2 = int(p2.x()), int(p2.y())

        if x1 < 0:
            x1 = 0
        if y1 < 0:
            y1 = 0

        tif = self.window.image
        # if self.window.imageview.hasTimeAxis():
        if self.window.mt > 1:
            mt, mx, my = tif.shape[:3]
            if x2 >= mx:
                x2 = mx - 1
            if y2 >= my:
                y2 = my - 1
            newtif = tif[:, x1:x2, y1:y2]
        else:
            mx, my = tif.shape[:2]
            if x2 >= mx:
                x2 = mx - 1
            if y2 >= my:
                y2 = my - 1
            newtif = tif[x1:x2, y1:y2]

        w = Window(newtif, self.window.name + " Cropped", metadata=self.window.metadata)
        w.imageview.setImage(newtif, axes=self.window.imageview.axes)
        w.image = newtif
        return w


@beartype.beartype
class ROI_freehand(ROI_Base, pg.ROI):
    """ROI freehand class for selecting a polygon from the original image.

    Extends from :class:`ROI_Base <flika.roi.ROI_Base>` and pyqtgraph.ROI.
    """

    kind = "freehand"
    plotSignal = QtCore.Signal()

    def __init__(self, window, pts, **kargs):
        roiArgs = self.INITIAL_ARGS.copy()
        roiArgs.update(kargs)
        roiArgs["closed"] = True
        pg.ROI.__init__(
            self,
            np.min(pts, axis=0),
            np.ptp(a=np.array(pts), axis=0),
            translateSnap=(1, 1),
            **kargs,
        )
        ROI_Base.__init__(self, window, pts)
        self._untranslated_pts: jaxtyping.Float[np.ndarray, "num_pts 2"] = np.subtract(
            self.pts, self.pos()
        )
        self._untranslated_mask = None
        self.getMask()

    def shape(self):
        p = QtGui.QPainterPath()
        p.moveTo(*self._untranslated_pts[0])
        for _, pt in enumerate(self._untranslated_pts):
            p.lineTo(*pt)
        p.lineTo(*self._untranslated_pts[0])
        return p

    def paint(self, painter: QtGui.QPainter, *args) -> None:
        painter.setPen(self.currentPen)
        points: list[pg.Point.Points] = [
            pg.Point(a, b) for a, b in self._untranslated_pts
        ]
        painter.drawPolygon(points)

    def draw_from_points(
        self, pts: jaxtyping.Float[np.ndarray, "n 2"], finish: bool = False
    ) -> None:
        self.blockSignals(True)
        self.setPos(*np.min(pts, 0), False)
        self.setSize(np.ptp(pts, 0), False)
        self._untranslated_pts = np.subtract(pts, self.pos())
        self.pts = pts

        self.sigRegionChanged.emit(self)
        if finish:
            self.sigRegionChangeFinished.emit(self)
        self.blockSignals(False)

    def contextMenuEnabled(self):
        return True

    def getPoints(self) -> jaxtyping.Float[np.ndarray, "n 2"]:
        x, y = self.state["pos"]
        return np.add(self._untranslated_pts, [x, y])

    def contains_pt(self, x, y):
        pt = QtCore.QPointF(x, y) - self.pos()
        qPainterPath = self.shape()
        return qPainterPath.contains(pt)

    def contains_pts(self, x, y):
        """not yet implemented"""
        pass

    def getMask(self):
        if self._untranslated_mask is not None:
            xx = self._untranslated_mask[0] + int(self.state["pos"][0])
            yy = self._untranslated_mask[1] + int(self.state["pos"][1])
        else:
            x, y = np.transpose(self._untranslated_pts)
            mask = np.zeros(self.window.imageDimensions())
            xx, yy = skimage.draw.polygon(x, y, shape=mask.shape)
            self._untranslated_mask = xx, yy

        idx_to_keep = np.logical_not(
            (xx >= self.window.mx) | (xx < 0) | (yy >= self.window.my) | (yy < 0)
        )
        xx = xx[idx_to_keep]
        yy = yy[idx_to_keep]
        return xx, yy


@beartype.beartype
class ROI_rect_line(ROI_Base, QtWidgets.QGraphicsObject):
    """Collection of linked line segments with adjustable width.

    Extends from :class:`ROI_Base <flika.roi.ROI_Base>` and QtWidgets.QGraphicsObject

    Attributes:
        kymograph (Window): :class:`Window <flika.window.Window>` showing 2d kymograph.
    """

    kind = "rect_line"
    plotSignal = QtCore.Signal()
    sigRegionChanged = QtCore.Signal(object)
    sigRegionChangeFinished = QtCore.Signal(object)

    def __init__(self, window, pts, width=1, **kargs):
        self.roiArgs = self.INITIAL_ARGS.copy()
        self.roiArgs.update(kargs)
        self.roiArgs["scaleSnap"] = False
        self.width = width
        self.kymograph = None
        QtWidgets.QGraphicsObject.__init__(self)
        self.kymographAct = QtWidgets.QAction(
            "&Kymograph", self, triggered=self.update_kymograph
        )
        self.removeLinkAction = QtWidgets.QAction(
            "Remove Last Link", self, triggered=nonpartial(self.removeSegment)
        )
        self.setWidthAction = QtWidgets.QAction(
            "Set Width", self, triggered=nonpartial(self.setWidth)
        )
        ROI_Base.__init__(self, window, pts)
        self.getPoints = self.getHandlePositions
        self.pen = QtGui.QPen(QtGui.QColor(255, 255, 0))
        self.pen.setWidth(0)
        self.lines = []
        if len(pts) < 2:
            raise Exception("Must start with at least 2 points")
        self.extendHandle = None

        self.addSegment(pts[1], connectTo=pts[0])
        for p in pts[2:]:
            self.addSegment(p)

    def getHandles(self):
        handles = []
        for line in self.lines:
            handles.append(line.getHandles()[0])
        handles.append(self.lines[-1].getHandles()[1])
        return handles

    def movePoint(self, handle, *args, **kargs):
        if isinstance(handle, int):
            handle = self.getHandles()[handle]
        kargs["finish"] = False
        self.blockSignals(True)
        for line in handle.rois:
            line.movePoint(handle, *args, **kargs)
        self.blockSignals(False)
        self.sigRegionChanged.emit(self)
        self.sigRegionChangeFinished.emit(self)

    def delete(self):
        ROI_Base.delete(self)
        if self.kymograph:
            self.deleteKymograph()

    def draw_from_points(self, pts, finish=False):
        while len(self.lines) > 1:
            self.removeSegment(self.lines[-1])

        self.lines[0].movePoint(0, pts[0])
        self.lines[0].movePoint(1, pts[1])
        for p in pts[2:]:
            self.addSegment(p)

        if finish:
            self.sigRegionChangeFinished.emit(self)
        self.pts = pts

    def getTrace(
        self, bounds: list[int] | None = None
    ) -> jaxtyping.Float[np.ndarray, "t"] | None:
        if self.window.image.ndim > 3 or self.window.metadata["is_rgb"]:
            g.alert(
                "Plotting trace of RGB movies is not supported. Try splitting the channels."
            )
            return None
        trace: jaxtyping.Float[np.ndarray, "t"]
        if self.window.image.ndim == 3:
            region = self.getArrayRegion(
                self.window.imageview.image,
                self.window.imageview.getImageItem(),
                (1, 2),
            )
            while region.ndim > 1:
                trace = np.average(region, 1)
        elif self.window.image.ndim == 2:
            region = self.getArrayRegion(
                self.window.imageview.image,
                self.window.imageview.getImageItem(),
                (0, 1),
            )
            trace = np.array([np.average(region)])
        if bounds:
            trace = trace[bounds[0] : bounds[1]]
        return trace

    def preview(self):
        im = self.getArrayRegion(
            self.window.imageview.getImageItem().image,
            self.window.imageview.getImageItem(),
            (0, 1),
        )
        if not hasattr(self, "prev"):
            from .window import Window

            self.prev = Window(im)
            self.sigRegionChanged.connect(lambda a: self.preview())
        else:
            self.prev.imageview.setImage(im)

    def getHandlePositions(self):
        """Return the positions of all handles in local coordinates."""
        p = self.mapFromScene(self.lines[0].getHandles()[0].scenePos())
        p = self.lines[0].getSnapPosition([p.x(), p.y()])
        pos = [p]
        for line in self.lines:
            p = self.mapFromScene(line.getHandles()[1].scenePos())
            p = line.getSnapPosition([p.x(), p.y()])
            pos.append(p)
        self.pts = pos
        return self.pts

    def getArrayRegion(
        self,
        data: np.ndarray,
        image_item: QtWidgets.QGraphicsItem = None,
        axes: tuple[int, int] = (0, 1),
        **kwds,
    ) -> np.ndarray:
        rgns = []
        for line in self.lines:
            rgn = line.getArrayRegion(data, image_item, axes=axes, **kwds)
            if rgn is None:
                continue
                # return None
            rgns.append(rgn)
            # print line.state['size']

        ## make sure orthogonal axis is the same size
        ## (sometimes fp errors cause differences)
        if image_item.axisOrder == "row-major":
            axes = axes[::-1]
        ms = min([rgn.shape[axes[1]] for rgn in rgns])
        slices = [slice(None)] * rgns[0].ndim
        slices[axes[1]] = slice(0, ms)
        rgns = [rgn[*slices] for rgn in rgns]
        # print [r.shape for r in rgns], axes

        return np.concatenate(rgns, axis=axes[0])

    def addSegment(self, pos=(0, 0), connectTo=None):
        """
        Add a new segment to the ROI connecting from the previous endpoint to *pos*.
        (pos is specified in the parent coordinate system of the MultiRectROI)
        """
        ## by default, connect to the previous endpoint
        if len(self.lines) == 0 or connectTo == self.lines[0].getHandles()[0]:
            ind = 0
        else:
            ind = len(self.lines)

        def dragEvent(handle, ev):
            pos = self.window.imageview.view.mapToView(ev.scenePos())
            if ev.button() == QtCore.Qt.RightButton:
                edgeHandles = self.getHandles()
                edgeHandles = edgeHandles[0], edgeHandles[-1]
                if self.extendHandle is None and handle not in edgeHandles:
                    return

                if len(handle.rois) == 1 and ev.isStart():
                    _, self.extendHandle = self.addSegment(pos, connectTo=handle)
                elif ev.isFinish():
                    self.extendFinished()
                else:
                    self.extend(round(pos.x()), round(pos.y()), finish=False)
            else:
                for roi in handle.rois:
                    roi.movePoint(handle, [round(pos.x()), round(pos.y())])
                return
            Handle.mouseDragEvent(handle, ev)
            ev.accept()

        if connectTo is None:
            connectTo = self.lines[-1].getHandles()[1]

        ## create new ROI
        if len(self.lines) > 0:
            newRoi = pg.ROI(
                (0, 0), [1, self.width], parent=self, pen=self.pen, **self.roiArgs
            )
        else:
            newRoi = pg.ROI((0, 0), [1, self.width], pen=self.pen, **self.roiArgs)
            newRoi.setParentItem(self)

        if len(self.lines) == 0 or ind > 0:  # add handles in order
            ## Add first SR handle
            if isinstance(connectTo, Handle):
                h = newRoi.addScaleRotateHandle([0, 0.5], [1, 0.5], item=connectTo)
                newRoi.movePoint(connectTo, connectTo.scenePos(), coords="scene")
            else:
                h = newRoi.addScaleRotateHandle([0, 0.5], [1, 0.5])
                newRoi.movePoint(h, connectTo, coords="scene")
            h.mouseDragEvent = lambda ev: dragEvent(h, ev)

            ## add second SR handle
            h2 = newRoi.addScaleRotateHandle([1, 0.5], [0, 0.5])
            h2.mouseDragEvent = lambda ev: dragEvent(h2, ev)
            newRoi.movePoint(h2, pos)
        else:
            h2 = newRoi.addScaleRotateHandle([1, 0.5], [0, 0.5])
            h2.mouseDragEvent = lambda ev: dragEvent(h2, ev)
            newRoi.movePoint(h2, pos)

            if isinstance(connectTo, Handle):
                h = newRoi.addScaleRotateHandle([0, 0.5], [1, 0.5], item=connectTo)
                newRoi.movePoint(connectTo, connectTo.scenePos(), coords="scene")
            else:
                h = newRoi.addScaleRotateHandle([0, 0.5], [1, 0.5])
                newRoi.movePoint(h, connectTo, coords="scene")
            h.mouseDragEvent = lambda ev: dragEvent(h, ev)

        self.lines.insert(ind, newRoi)
        self.lines[0]._updateView()

        newRoi.translatable = False
        newRoi.hoverEvent = lambda e: self.hoverEvent(newRoi, e)
        newRoi.raiseContextMenu = self.raiseContextMenu
        # newRoi.sigRegionChangeStarted.connect(self.roiChangeStartedEvent)
        newRoi.sigRegionChanged.connect(lambda a: self.sigRegionChanged.emit(self))
        newRoi.sigRegionChangeFinished.connect(
            lambda a: self.sigRegionChangeFinished.emit(self)
        )
        self.sigRegionChanged.emit(self)
        return newRoi, h2

    def removeSegment(self, segment=None, finish=True):
        """Remove a segment from the ROI"""
        if segment is None:
            segment = self.removeLinkAction.data()
            if segment is None:
                return
        elif isinstance(segment, int):
            segment = self.lines[segment]

        segment.sigRegionChangeFinished.disconnect()
        segment.sigRegionChanged.disconnect()

        for h in segment.getHandles():
            if len(h.rois) == 2 and h.parentItem() == segment:
                otherROI = [line for line in h.rois if line != segment][0]
                h.setParentItem(otherROI)
                h.setPos(0, 0.5)
            h.disconnectROI(segment)
        if segment in self.lines:
            self.lines.remove(segment)

        segment.scene().removeItem(segment)
        if len(self.lines) == 0:
            self.delete()

    def extend(self, x, y, finish=True):
        self.blockSignals(True)
        point = pg.Point(x, y)

        if self.extendHandle is not None:
            for roi in self.lines:
                if self.extendHandle in roi.getHandles():
                    roi.movePoint(self.extendHandle, point, finish=False)
            # self.extendHandle.movePoint(self.window.imageview.getImageItem().mapToScene(point), finish=False)
        else:
            self.addSegment((x, y))
        self.blockSignals(False)

        self.sigRegionChanged.emit(self)
        if finish:
            self.sigRegionChangeFinished.emit(self)

    def drawFinished(self):
        ROI_Base.drawFinished(self)
        for l in self.lines:
            l._updateView()

    def extendFinished(self):
        self.extendHandle = None
        for l in (
            self.lines
        ):  # fix resizing handles. First link Viewbox was set to something different
            l._updateView()
        self.sigRegionChangeFinished.emit(self)

    def hoverEvent(self, l, ev):
        if ev.enter:
            pen = QtGui.QPen(QtGui.QColor(255, 0, 0))
            pen.setWidth(0)
            l.setPen(pen)
            l.mouseHovering = True
            # self.setCurrentPen(pen)
        elif ev.exit:
            l.setPen(self.pen)
            self.setCurrentPen(self.pen)
            l.mouseHovering = False

    def getMask(self):
        xxs = []
        yys = []
        for i in range(len(self.pts) - 1):
            p1, p2 = self.pts[i], self.pts[i + 1]
            xx, yy = skimage.draw.line(int(p1[0]), int(p1[1]), int(p2[0]), int(p2[1]))
            idx_to_keep = np.logical_not(
                (xx >= self.window.mx) | (xx < 0) | (yy >= self.window.my) | (yy < 0)
            )
            xx = xx[idx_to_keep]
            yy = yy[idx_to_keep]
            xxs.extend(xx)
            yys.extend(yy)

        return np.array(xxs, dtype=int), np.array(yys, dtype=int)

    def makeMenu(self):
        ROI_Base.makeMenu(self)
        self.menu.addAction(self.removeLinkAction)
        self.menu.addAction(self.setWidthAction)
        self.menu.addAction(self.kymographAct)
        self.kymographAct.setEnabled(self.window.image.ndim > 2)

    def raiseContextMenu(self, ev):
        currentLines = [line for line in self.lines if line.mouseHovering]
        if len(currentLines) > 0 and np.any(
            [len(i.rois) == 1 for i in currentLines[0].getHandles()]
        ):
            self.removeLinkAction.setText("Remove Link")
            self.removeLinkAction.setVisible(True)
            self.removeLinkAction.setData(currentLines[0])
        else:
            self.removeLinkAction.setVisible(False)

        ROI_Base.raiseContextMenu(self, ev)

    def boundingRect(self):
        return QtCore.QRectF()

    def paint(self, p, *args):
        pass

    def setPen(self, pen):
        pen = QtGui.QPen(pen)
        pen.setWidth(0)
        self.pen = pen
        self.setCurrentPen(pen)

    def setCurrentPen(self, pen):
        pen = QtGui.QPen(pen)
        pen.setWidth(0)
        for l in self.lines:
            l.currentPen = pen
            l.update()

    def update_kymograph(self):
        tif = self.window.image
        if tif.ndim != 3:
            g.alert("Can only kymograph on 3D movies")
            return

        if self.width == 1:
            w, h = self.window.imageDimensions()
            r = QtCore.QRect(0, 0, w, h)
            xx, yy = self.getMask()
            mn = tif[:, xx, yy].T
        else:
            region = self.getArrayRegion(
                self.window.imageview.image,
                self.window.imageview.getImageItem(),
                (1, 2),
            )
            mn = np.average(region, 2).T

        if self.kymograph is None:
            self.createKymograph(mn)
        else:
            if mn.size > 0:
                self.kymograph.imageview.setImage(mn, autoLevels=False, autoRange=False)
            # self.kymograph.imageview.view.setAspectLocked(lock=True,ratio=mn.shape[1]/mn.shape[0])

    def setWidth(self, newWidth=None):
        """Set the width of each segment in the ROI

        Args:
            newWidth (int): new width of all segments
        """
        s = True
        if newWidth is None:
            newWidth, s = QtWidgets.QInputDialog.getInt(
                None, "Enter a width value", "Float Value", value=self.width
            )
        if not s or s == 0:
            return
        for l in self.lines:
            l.scale([1.0, newWidth / self.width], center=[0.5, 0.5])
        self.width = newWidth
        self.sigRegionChangeFinished.emit(self)

    def createKymograph(self, mn):
        from .window import Window

        oldwindow = g.win
        name = oldwindow.name + " - Kymograph"
        self.kymograph = Window(mn, name, metadata=self.window.metadata)
        self.kymographproxy = pg.SignalProxy(
            self.sigRegionChanged, rateLimit=1, slot=self.update_kymograph
        )  # This will only update 3 Hz
        self.sigRegionChanged.connect(self.update_kymograph)
        self.kymograph.closeSignal.connect(self.deleteKymograph)

    def deleteKymograph(self):
        self.kymographproxy.disconnect()
        self.sigRegionChanged.disconnect(self.update_kymograph)
        self.kymograph.closeSignal.disconnect(self.deleteKymograph)
        self.kymograph = None


@beartype.beartype
def makeROI(kind, pts, window=None, color=None, **kargs):
    """Create an ROI object in window with the given points

    Args:
        kind (str): one of ['line', 'rectangle', 'freehand', 'rect_line']
        pts ([N, 2] list of coords): points used to draw the ROI, differs by kind
        window (window.Window): window to draw the ROI in, or currentWindow if not specified
        color (QtGui.QColor): pen color of the new ROI
        **kargs: additional arguments to pass to the ROI __init__ function

    Returns:
        ROI Object extending ROI_Base
    """
    if window is None:
        window = g.win
        if window is None:
            g.alert("ERROR: In order to make and ROI a window needs to be selected")
            return None

    if kind == "freehand":
        roi = ROI_freehand(window, pts, **kargs)
    elif kind == "rectangle":
        if len(pts) > 2:
            size = np.ptp(pts, 0)
            top_left = np.min(pts, 0)
        else:
            size = pts[1]
            top_left = pts[0]
        roi = ROI_rectangle(window, top_left, size, **kargs)
    elif kind == "line":
        roi = ROI_line(window, (pts), **kargs)
    elif kind == "rect_line":
        roi = ROI_rect_line(window, pts, **kargs)
    else:
        g.alert("ERROR: THIS KIND OF ROI COULD NOT BE FOUND: {}".format(kind))
        return None

    if color is None or not isinstance(color, QtGui.QColor):
        pen = QtGui.QPen(
            QtGui.QColor(g.settings["roi_color"])
            if g.settings["roi_color"] != "random"
            else random_color()
        )
    else:
        pen = QtGui.QPen(color)
    pen.setWidth(0)

    roi.drawFinished()
    roi.setPen(pen)
    return roi


def open_rois(filename=None):
    """
    Open an roi.txt file, creates ROI objects and places them in the current Window.

    Args:
        filename (str): The filename (including full path) of the roi.txt file.

    Returns:
        list: List of created ROI objects
    """
    if filename is None:
        filename = open_file_gui("Open ROI File", filetypes="*.txt")
        if filename is None:
            return
    if not os.path.isfile(filename):
        g.alert("Can't open roi file {}. File does not exist".format(filename))
        return
    try:
        with open(filename, "r") as file:
            text = file.read()

    except Exception:
        g.alert("Can't open roi file. Wrong file format")
        return
    if g.win is None:
        g.alert("You need to open an image window before opening ROIs.")
        return

    kinds = []
    roi_starts = []
    i = 0
    for line in text.split("\n"):
        # Check for ROI types in brackets [rectangle] or without brackets (rectangle)
        if line.startswith("[") or line.strip() in [
            "rectangle",
            "line",
            "freehand",
            "rect_line",
        ]:
            # Handle both bracketed and non-bracketed formats
            if line.startswith("["):
                kinds.append(line.strip("[], "))
            else:
                kinds.append(line.strip())

            roi_starts.append(i)
        i += 1
    roi_starts.append(i)  # add end of file

    text_lines = text.split("\n")

    rois = []
    for i in range(len(kinds)):
        roi_text_lines = text_lines[roi_starts[i] + 1 : roi_starts[i + 1]]
        pts = []
        for text_line in roi_text_lines:
            try:
                if text_line.strip() == "":
                    continue
            except Exception:
                pts = None
            else:
                pts.append(tuple(int(float(i)) for i in text_line.split()))

        if pts is not None and len(pts) > 0:
            roi = makeROI(kinds[i], pts)
            if roi is not None:
                rois.append(roi)

    return rois
