import numpy as np
import pyqtgraph as pg
from qtpy import QtCore, QtGui, QtWidgets
from process.BaseProcess import BaseDialog, SliderLabel

class SLD_Histogram(QtWidgets.QWidget):
    def __init__(self, pynsight_pts):
        super(SLD_Histogram, self).__init__()
        self.pynsight_pts = pynsight_pts
        self.plotWidget = SLD_Histogram_Plot(pynsight_pts)
        self.trackLengthsGroup = self.makeTrackLengthsGroup()
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addWidget(self.plotWidget)
        self.layout.addWidget(self.trackLengthsGroup)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setWindowTitle('Flika - Pynsight Plugin - SLD')
        self.setWindowIcon(QtGui.QIcon('images/favicon.png'))
        self.show()

    def makeTrackLengthsGroup(self):
        trackLengthsGroup = QtWidgets.QGroupBox()
        trackLengthsGroup.setTitle('Track Lengths')
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(QtWidgets.QLabel('Only include particles with track lengths between'))
        min_track_spinbox = QtWidgets.QSpinBox()
        max_track_len = np.max([len(t) for t in self.pynsight_pts.tracks])
        min_track_spinbox.setRange(2, max_track_len)
        min_track_spinbox.valueChanged.connect(self.min_track_spinbox_updated)
        max_track_spinbox = QtWidgets.QSpinBox()
        max_track_spinbox.setRange(2, max_track_len)
        max_track_spinbox.setValue(max_track_len)

        max_track_spinbox.valueChanged.connect(self.max_track_spinbox_updated)
        layout.addWidget(min_track_spinbox)
        layout.addWidget(QtWidgets.QLabel('and'))
        layout.addWidget(max_track_spinbox)
        layout.addWidget(QtWidgets.QLabel('frames long (inclusive).'))
        layout.addItem(QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding))
        trackLengthsGroup.setLayout(layout)
        return trackLengthsGroup

    def min_track_spinbox_updated(self, val):
        self.plotWidget.min_tracklength = val
        self.plotWidget.tracks_updated()

    def max_track_spinbox_updated(self, val):
        self.plotWidget.max_tracklength = val
        self.plotWidget.tracks_updated()



class SLD_Histogram_Plot(pg.PlotWidget):
    def __init__(self, pynsight_pts):
        super(SLD_Histogram_Plot, self).__init__(title='Mean Single Lag Distance Histogram', labels={'left': 'Count', 'bottom': 'Mean SLD Per Track (Pixels)'})
        self.pynsight_pts = pynsight_pts
        self.plotitem = pg.PlotDataItem()
        self.addItem(self.plotitem)
        self.bins = np.zeros(1)
        self.n_bins = 0
        self.minimum = 0.
        self.maximum = 0.
        self.min_tracklength = 2
        self.max_tracklength = np.max([len(t) for t in self.pynsight_pts.tracks])
        self.plot_data = []
        self.bd = None
        self.tracks_updated()


    def tracks_updated(self):
        tracks = self.pynsight_pts.tracks
        pts = self.pynsight_pts.txy_pts
        mean_single_lags = []
        for track in tracks:
            if self.min_tracklength <= len(track) <= self.max_tracklength:
                txy = pts[track, :]
                dt_dx = txy[1:, :] - txy[:-1, :]
                velocities = np.sqrt(dt_dx[:, 1] ** 2 + dt_dx[:, 2] ** 2) / dt_dx[:, 0]  # velocities in pixels/frame
                velocities = np.mean(velocities)
                mean_single_lags.append(velocities)
        mean_single_lags = np.array(mean_single_lags)
        if len(mean_single_lags)>0:
            self.setData(mean_single_lags)

    def setData(self, data=np.array([]), n_bins=None):
        if n_bins is None:
            n_bins = data.size ** 0.5
        if len(data) == 0:
            data = self.plot_data

        minimum = 0
        maximum = np.max(data)

        # if this is the first histogram plotted, initialize settings
        self.minimum = minimum
        self.maximum = maximum
        self.n_bins = n_bins
        self.bins = np.linspace(self.minimum, self.maximum, int(self.n_bins + 1))

        # re-plot the other histograms with this new binning if needed
        re_hist = False
        if minimum < self.minimum:
            self.minimum = minimum
            re_hist = True
        if maximum > self.maximum:
            self.maximum = maximum
            re_hist = True
        if n_bins > self.n_bins:
            self.n_bins = n_bins
            re_hist = True

        if re_hist:
            self.reset()

        self._plot_histogram(data)

    def preview(self, n_bins=None):
        if n_bins is None:
            n_bins = len(self.plotitem.getData()[1])

        bins = np.linspace(np.min(self.plot_data), np.max(self.plot_data), int(n_bins + 1))
        y, x = np.histogram(self.plot_data, bins=bins)
        self.plotitem.setData(x=x, y=y, stepMode=True, fillLevel=0)

    def _plot_histogram(self, data):

        # Copy self.bins, otherwise it is returned as x, which we can accidentally modify
        # by x *= -1, leaving self.bins modified.
        bins = self.bins.copy()
        y, x = np.histogram(data, bins=bins)

        self.plotitem.setData(x=x, y=y, stepMode=True, fillLevel=0)

        self.plot_data = data

    def reset(self):
        self.bins = np.linspace(self.minimum, self.maximum, self.n_bins + 1)
        bins = self.bins.copy()
        y, x = np.histogram(self.plot_data, bins=bins)

        self.plotitem.setData(x, y)

    def mouseDoubleClickEvent(self, ev):
        ev.accept()
        super(SLD_Histogram_Plot, self).mouseDoubleClickEvent(ev)
        if len(self.plot_data) > 0:
            self.edit_histogram_gui()

    def export(self, filename):
        np.savetxt(filename, self.plot_data, header='Mean Single Lag Distances')

    def edit_histogram_gui(self):
        items = []
        binSlider = SliderLabel(0)
        binSlider.setMinimum(1)
        binSlider.setMaximum(len(self.plot_data))
        binSlider.setValue(self.n_bins)
        items.append({'name': 'Bins', 'string': 'Bins', 'object': binSlider})
        bd = BaseDialog(items, "Histogram options", 'Set the number of bins in the histogram')
        bd.accepted.connect(lambda : self.setData(n_bins=binSlider.value()))
        bd.rejected.connect(self.reset)
        bd.changeSignal.connect(lambda : self.preview(n_bins=binSlider.value()))
        bd.setMinimumWidth(400)
        bd.show()
        self.bd = bd