# -*- coding: utf-8 -*-
"""
Created on Wed June 15 2016
@author: Kyle Ellefsen

Algorithm:
1) Gaussian Blur
2) High pass butterworth filter
3) Fit gaussian to several points to get point spread function
4)


"""

import numpy as np
import os
import global_vars as g
from process.BaseProcess import BaseProcess, WindowSelector, SliderLabel, CheckBox
import pickle
from qtpy.QtCore import QUrl, QRect, QPointF, Qt
from qtpy.QtGui import QDesktopServices, QIcon, QPainterPath, QPen, QColor
from qtpy.QtWidgets import QHBoxLayout, QGraphicsPathItem, qApp
from qtpy import uic
from window import Window
from process.file_ import save_file_gui
from .insight_writer import write_insight_bin
from .gaussianFitting import fitGaussian, gaussian, generate_gaussian
from .particle_simulator import simulate_particles
from .SLD_histogram import SLD_Histogram
from .MSD_Plot import MSD_Plot


def launch_docs():
    url='https://github.com/kyleellefsen/pynsight'
    QDesktopServices.openUrl(QUrl(url))


def simulate_particles_wrapper():
    A, true_pts = simulate_particles()
    Window(A)


def Export_pts_from_MotilityTracking():
    tracks = g.m.trackPlot.all_tracks
    t_out = []
    x_out = []
    y_out = []
    for i in np.arange(len(tracks)):
        track = tracks[i]
        t_out.extend(track['frames'])
        x_out.extend(track['x_cor'])
        y_out.extend(track['y_cor'])
    p_out = np.array([t_out, x_out, y_out]).T
    filename = r'C:\Users\kyle\Desktop\trial8_pts.txt'
    np.savetxt(filename, p_out)


def getSigma():
    ''' This function isn't complete.  I need to cut out a 20x20 pxl window around large amplitude particles '''
    I = g.m.currentWindow.image
    xorigin = 8
    yorigin = 9
    sigma = 2
    amplitude = 50
    p0 = [xorigin, yorigin, sigma, amplitude]
    p, I_fit, _ = fitGaussian(I, p0)
    xorigin, yorigin, sigma, amplitude = p
    return sigma


def convolve(I, sigma):
    from scipy.signal import convolve2d
    G = generate_gaussian(17, sigma)
    newI = np.zeros_like(I)
    for t in np.arange(len(I)):
        print(t)
        newI[t] = convolve2d(I[t], G, mode='same', boundary='fill', fillvalue=0)
    return newI


def get_points(I):
    import scipy.ndimage
    s = scipy.ndimage.generate_binary_structure(3, 1)
    s[0] = 0
    s[2] = 0
    labeled_array, num_features = scipy.ndimage.measurements.label(I, structure=s)
    objects = scipy.ndimage.measurements.find_objects(labeled_array)

    all_pts = []
    for loc in objects:
        offset = np.array([a.start for a in loc])
        pts = np.argwhere(labeled_array[loc] != 0) + offset
        ts = np.unique(pts[:, 0])
        for t in ts:
            pts_t = pts[pts[:, 0] == t]
            x = np.mean(pts_t[:, 1])
            y = np.mean(pts_t[:, 2])
            all_pts.append([t, x, y])
    all_pts = np.array(all_pts)
    return all_pts


def cutout(pt, Movie, width):
    assert width % 2 == 1  # mx must be odd
    t, x, y = pt
    t=int(t)
    mid = int(np.floor(width / 2))
    x0 = int(x - mid)
    x1 = int(x + mid)
    y0 = int(y - mid)
    y1 = int(y + mid)
    mt, mx, my = Movie.shape
    if y0 < 0: y0 = 0
    if x0 < 0: x0 = 0
    if y1 >= my: y1 = my - 1
    if x1 >= mx: x1 = mx - 1
    corner = [x0, y0]
    I = Movie[t, x0:x1 + 1, y0:y1 + 1]
    return I, corner


def refine_pts(pts, blur_window, sigma, amplitude):
    if blur_window is None:
        return None, False
    new_pts = []
    old_frame = -1
    for pt in pts:
        new_frame = int(pt[0])
        if old_frame != new_frame:
            old_frame = new_frame
            blur_window.imageview.setCurrentIndex(old_frame)
            qApp.processEvents()
            if g.halt_current_computation:
                g.halt_current_computation = False
                return new_pts, False
        width = 9
        mid = int(np.floor(width / 2))
        I, corner = cutout(pt, blur_window.image, width)
        xorigin = mid
        yorigin = mid
        p0 = [xorigin, yorigin, sigma, amplitude]
        fit_bounds = [(0, 9), (0, 9), (0, 4), (0, 1000)]
        p, I_fit, _ = fitGaussian(I, p0, fit_bounds)
        xfit = p[0] + corner[0]
        yfit = p[1] + corner[1]
        #                t,  old x, old y, new_x, new_y, sigma, amplitude
        new_pts.append([pt[0], pt[1], pt[2], xfit, yfit, p[2], p[3]])
    new_pts = np.array(new_pts)
    return new_pts, True


class Points(object):
    def __init__(self, txy_pts):
        self.frames = np.unique(txy_pts[:, 0]).astype(np.int)
        self.txy_pts = txy_pts
        self.pts_by_frame = []
        self.pts_remaining = []
        self.pts_idx_by_frame = []  # this array has the same structure as points_by_array but contains the index of the original txy_pts argument
        curr_idx = 0
        self.window = None
        self.pathitems = []

        for frame in np.arange(0, np.max(self.frames) + 1):
            pos = txy_pts[txy_pts[:, 0] == frame, 1:]
            self.pts_by_frame.append(pos)
            self.pts_remaining.append(np.ones(pos.shape[0], dtype=np.bool))
            old_curr_idx = curr_idx
            curr_idx = old_curr_idx + len(pos)
            self.pts_idx_by_frame.append(np.arange(old_curr_idx, curr_idx))

    def link_pts(self, maxFramesSkipped, maxDistance):
        tracks = []
        for frame in self.frames:
            for pt_idx in np.where(self.pts_remaining[frame])[0]:
                self.pts_remaining[frame][pt_idx] = False
                abs_pt_idx = self.pts_idx_by_frame[frame][pt_idx]
                track = [abs_pt_idx]
                track = self.extend_track(track, maxFramesSkipped, maxDistance)
                tracks.append(track)
        self.tracks = tracks

    def extend_track(self, track, maxFramesSkipped, maxDistance):
        pt = self.txy_pts[track[-1]]
        # pt can move less than two pixels in one frame, two frames can be skipped
        for dt in np.arange(maxFramesSkipped)+1:
            frame = int(pt[0]) + dt
            if frame >= len(self.pts_remaining):
                return track
            candidates = self.pts_remaining[frame]
            nCandidates = np.count_nonzero(candidates)
            if nCandidates == 0:
                continue
            else:
                distances = np.sqrt(np.sum((self.pts_by_frame[frame][candidates] - pt[1:]) ** 2, 1))
            if any(distances < maxDistance):
                next_pt_idx = np.where(candidates)[0][np.argmin(distances)]
                abs_next_pt_idx = self.pts_idx_by_frame[frame][next_pt_idx]
                track.append(abs_next_pt_idx)
                self.pts_remaining[frame][next_pt_idx] = False
                track = self.extend_track(track, maxFramesSkipped, maxDistance)
                return track
        return track

    def get_tracks_by_frame(self):
        tracks_by_frame = [[] for frame in np.arange(np.max(self.frames)+1)]
        for i, track in enumerate(self.tracks):
            frames = self.txy_pts[track][:,0].astype(np.int)
            for frame in frames:
                tracks_by_frame[frame].append(i)
        self.tracks_by_frame = tracks_by_frame

    def clearTracks(self):
        for pathitem in self.pathitems:
            self.window.imageview.view.removeItem(pathitem)
        self.pathitems = []

    def showTracks(self):
        # clear self.pathitems
        self.clearTracks()

        frame = self.window.imageview.currentIndex
        if frame<len(self.tracks_by_frame):
            tracks = self.tracks_by_frame[frame]
            pen = QPen(Qt.green, .4)
            pen.setCosmetic(True)
            for track_idx in tracks:
                pathitem = QGraphicsPathItem(self.window.imageview.view)
                pathitem.setPen(pen)
                self.window.imageview.view.addItem(pathitem)
                self.pathitems.append(pathitem)
                pts = self.txy_pts[self.tracks[track_idx]]
                x = pts[:, 1]+.5; y = pts[:,2]+.5
                path = QPainterPath(QPointF(x[0],y[0]))
                for i in np.arange(1, len(pts)):
                    path.lineTo(QPointF(x[i],y[i]))
                pathitem.setPath(path)





class Pynsight():
    """pynsight()
    Tracks particles from STORM microscopy

    """

    def __init__(self):
        self.refining_points = False
        self.pts_refined = None
        self.txy_pts = None
        self.tracks_visible = False
        self.SLD_histogram = None

    def gui(self):
        gui = uic.loadUi(os.path.join(os.getcwd(), 'plugins', 'pynsight', 'pynsight.ui'))
        self.algorithm_gui = gui
        gui.setWindowIcon(QIcon('images/favicon.png'))
        gui.show()
        self.binary_window_selector = WindowSelector()
        gui.gridLayout_11.addWidget(self.binary_window_selector)
        gui.getPointsButton.pressed.connect(self.getPoints)
        gui.showPointsButton2.pressed.connect(self.showPoints_refined)
        gui.showPointsButton.pressed.connect(self.showPoints_unrefined)
        self.blurred_window_selector = WindowSelector()
        gui.gridLayout_9.addWidget(self.blurred_window_selector)
        gui.refine_points_button.pressed.connect(self.refinePoints)
        gui.skip_refine_button.pressed.connect(self.skip_refinePoints)
        gui.link_points_button.pressed.connect(self.linkPoints)
        gui.showTracksButton.pressed.connect(self.showTracks)
        gui.create_SLD_button.pressed.connect(self.create_SLD)
        gui.create_MSD_button.pressed.connect(self.create_MSD)
        gui.save_insight_button.pressed.connect(self.saveInsight)

    def getPoints(self):
        if self.binary_window_selector.window is None:
            g.alert('You must select a Binary Window before using it to determine where the points are.')
        else:
            self.txy_pts = get_points(self.binary_window_selector.window.image)
            self.algorithm_gui.showPointsButton.setEnabled(True)
            nPoints = len(self.txy_pts)
            self.algorithm_gui.num_pts_label.setText(str(nPoints))

    def refinePoints(self):
        if self.txy_pts is None:
            return None
        if self.refining_points:
            g.halt_current_computation = True
        else:
            self.refining_points = True
            blur_window = pynsight.blurred_window_selector.window
            sigma = self.algorithm_gui.gauss_sigma_spinbox.value()
            amp = self.algorithm_gui.gauss_amp_spinbox.value()
            self.pts_refined, completed = refine_pts(self.txy_pts, blur_window, sigma, amp)
            self.refining_points = False
            if not completed:
                print('The refinePoints function was interrupted.')
            else:
                self.algorithm_gui.showPointsButton2.setEnabled(True)

    def skip_refinePoints(self):
        if self.txy_pts is None:
            return None
        new_pts = []
        for pt in self.txy_pts:
                        #    t,  old x, old y, new_x, new_y, sigma, amplitude
            new_pts.append([pt[0], pt[1], pt[2], pt[1], pt[2], -1, -1])
        self.pts_refined = np.array(new_pts)
        self.algorithm_gui.showPointsButton2.setEnabled(True)

    def linkPoints(self):
        if self.pts_refined is None:
            return None
        txy_pts_refined = np.vstack((self.pts_refined[:, 0], self.pts_refined[:, 3], self.pts_refined[:, 4])).T
        self.points = Points(txy_pts_refined)
        maxFramesSkipped = self.algorithm_gui.maxFramesSkippedSpinBox.value()
        maxDistance = self.algorithm_gui.maxDistanceSpinBox.value()
        self.points.link_pts(maxFramesSkipped, maxDistance)
        tracks = self.points.tracks
        nTracks = len(tracks)
        self.algorithm_gui.num_tracks_label.setText(str(nTracks))
        self.algorithm_gui.showTracksButton.setEnabled(True)
        self.points.get_tracks_by_frame()

    def showPoints_unrefined(self):
        g.m.currentWindow.scatterPoints = [[] for _ in np.arange(g.m.currentWindow.mt)]
        for pt in self.txy_pts:
            t = int(pt[0])
            if g.m.currentWindow.mt == 1:
                t = 0
            pointSize = g.m.settings['point_size']
            pointColor = QColor(g.m.settings['point_color'])
            position = [pt[1]+.5, pt[2]+.5, pointColor, pointSize]
            g.m.currentWindow.scatterPoints[t].append(position)
        g.m.currentWindow.updateindex()

    def showPoints_refined(self):
        txy_pts_refined = np.vstack((self.pts_refined[:, 0], self.pts_refined[:, 3], self.pts_refined[:, 4])).T
        g.m.currentWindow.scatterPoints = [[] for _ in np.arange(g.m.currentWindow.mt)]
        for pt in txy_pts_refined:
            t = int(pt[0])
            if g.m.currentWindow.mt == 1:
                t = 0
            pointSize = g.m.settings['point_size']
            pointColor = QColor(g.m.settings['point_color'])
            position = [pt[1] + .5, pt[2] + .5, pointColor, pointSize]
            g.m.currentWindow.scatterPoints[t].append(position)
        g.m.currentWindow.updateindex()

    def showTracks(self):
        if not self.tracks_visible:
            self.points.window = g.m.currentWindow
            g.m.currentWindow.sigTimeChanged.connect(self.points.showTracks)
            self.tracks_visible = True
            self.algorithm_gui.showTracksButton.setText('Hide Tracks')
            self.points.showTracks()
        else:
            g.m.currentWindow.sigTimeChanged.disconnect(self.points.showTracks)
            self.points.clearTracks()
            self.tracks_visible = False
            self.algorithm_gui.showTracksButton.setText('Show Tracks')

    def create_MSD(self):
        self.MSD_plot = MSD_Plot(self.points)
    def create_SLD(self):
        self.SLD_histogram = SLD_Histogram(self.points)

    def saveInsight(self):
        tracks = self.points.tracks
        kwargs = {'pts': self.pts_refined, 'tracks':tracks}
        save_file_gui(write_insight_bin, '.bin', 'Save File', kwargs)


pynsight = Pynsight()
g.m.pynsight = pynsight


if __name__ == '__main__':
    from plugins.pynsight.pynsight import *
    A, true_pts = simulate_particles()
    data_window = Window(A)
    data_window.setName('Data Window (F/F0)')
    blur_window = gaussian_blur(2, norm_edges=True, keepSourceWindow=True)
    blur_window.setName('Blurred Window')
    binary_window = threshold(.7, keepSourceWindow=True)
    binary_window.setName('Binary Window')


    txy_pts = get_points(g.m.currentWindow.image)
    np.savetxt(r'C:\Users\kyle\Desktop\simulated.txt', txy_pts)
    refined_pts = refine_pts(txy_pts, blur_window.image)
    refined_pts_txy = np.vstack((refined_pts[:, 0], refined_pts[:, 3], refined_pts[:, 4])).T
    p = Points(refined_pts_txy)
    p.link_pts()
    tracks = p.tracks

    filename = r'C:\Users\kyle\Desktop\test_flika.bin'
    write_insight_bin(filename, refined_pts, tracks)


