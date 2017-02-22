import numpy as np
from qtpy.QtCore import Qt, Signal, QRect, QRectF, QPointF, QSizeF
from qtpy.QtWidgets import qApp, QWidget, QGridLayout, QCheckBox, QComboBox, QFormLayout, QGraphicsPathItem, QGraphicsEllipseItem
from qtpy.QtGui import QPainterPath
import matplotlib
import pyqtgraph as pg
from pyqtgraph.dockarea import *
import pyqtgraph.opengl as gl
from .gaussianFitting import fitGaussian, fitRotGaussian



class puff_3D(gl.GLViewWidget):
    def __init__(self, parent=None):
        super(puff_3D, self).__init__(parent)
        self.setCameraPosition(distance=150, elevation=30, azimuth=90)
        image = np.zeros((10, 10))
        self.p1 = gl.GLSurfacePlotItem(z=image, shader='heightColor')
        ##    red   = pow(z * colorMap[0] + colorMap[1], colorMap[2])
        ##    green = pow(z * colorMap[3] + colorMap[4], colorMap[5])
        ##    blue  = pow(z * colorMap[6] + colorMap[7], colorMap[8])
        self.p1.shader()['colorMap'] = np.array([1, 0, 1, 1, .3, 2, 1, .4, 1])
        self.p1.scale(1, 1, 15.0)
        # self.p1.translate(-puff.udc['paddingXY'], -puff.udc['paddingXY'], 0)
        self.addItem(self.p1)
        self.p2 = gl.GLSurfacePlotItem(z=image, shader='heightColor')
        self.p2.shader()['colorMap'] = np.array([1, 0, 1, 1, .3, 2, 1, .4, 1])
        self.p2.scale(1, 1, 15.0)
        # self.p2.translate(-puff.udc['paddingXY'], -puff.udc['paddingXY'], 0)
        self.addItem(self.p2)

        self.shiftx = int(np.ceil(image.shape[0] / 2))
        self.p1.translate(self.shiftx, 0, 0)
        self.p2.translate(-self.shiftx, 0, 0)

    def update_images(self, image1, image2):
        self.p1.setData(z=image1)
        self.p2.setData(z=image2)
        self.p1.translate(-self.shiftx, 0, 0)
        self.p2.translate(self.shiftx, 0, 0)
        self.shiftx = int(np.ceil(image1.shape[0] / 2))
        self.p1.translate(self.shiftx, 0, 0)
        self.p2.translate(-self.shiftx, 0, 0)


def scatterRemovePoints(scatterplot, idxs):
    i2 = [i for i in np.arange(len(scatterplot.data)) if i not in idxs]
    points = scatterplot.points()
    points = points[i2]
    spots = [{'pos': points[i].pos(), 'data': points[i].data(), 'brush': points[i].brush()} for i in
             np.arange(len(points))]
    scatterplot.clear()
    scatterplot.addPoints(spots)


def scatterAddPoints(scatterplot, pos, data):
    points = scatterplot.points()
    spots = [{'pos': points[i].pos(), 'data': points[i].data()} for i in np.arange(len(points))]
    spots.extend([{'pos': pos[i], 'data': data[i]} for i in np.arange(len(pos))])
    scatterplot.clear()
    scatterplot.addPoints(spots)


class Groups(list):
    def __init__(self,puffAnalyzer):
        super(Groups,self).__init__()
        self.puffAnalyzer=puffAnalyzer
    def removePuffs(self,puffs):
        s2=self.puffAnalyzer.s2
        print(puffs[0].starting_idx)
        idxs=[]
        for puff in puffs:
            try:
                idx=[puff in self[i].puffs for i in np.arange(len(self))].index(True)
                idxs.append(idx)
            except ValueError:
                pass
        idxs=np.unique(idxs)
        idxs=list(idxs)
        idxs.sort(reverse=True)
        if len(idxs)>0:
            for i in idxs:
                group=self[i]
                scatterRemovePoints(s2,[iidx for iidx, pt in enumerate(s2.points()) if pt.data()==group])
                group.removePuffs(puffs)
                if len(group.puffs)==0:
                    self.remove(group)
                else:
                    scatterAddPoints(s2,[group.pos],[group])
                    #self.puffAnalyzer.s2.addPoints(pos=[group.pos],data=group)


class Group(object):
    def __init__(self,puffs):
        self.puffs=puffs
        self.pos=self.getPos()
    def getPos(self):
        x=np.mean(np.array([p.kinetics['x'] for p in self.puffs]))
        y=np.mean(np.array([p.kinetics['y'] for p in self.puffs]))
        return [x,y]
    def removePuffs(self,puffs):
        for puff in puffs:
            if puff in self.puffs:
                self.puffs.remove(puff)
        if len(self.puffs)==0:
            self.pos=[np.nan,np.nan]
        else:
            self.pos=self.getPos()


class GroupAnalyzer(QWidget):
    sigTimeChanged = Signal(int)

    def __init__(self, group, parent=None):
        super(GroupAnalyzer, self).__init__(parent)  ## Create window with ImageView widget
        # self=QWidget()
        self.group = group
        nPuffs = len(self.group.puffs)
        self.offsets = [puff.kinetics['t_start'] for puff in self.group.puffs]

        cmap = matplotlib.cm.gist_rainbow
        self.colors = [cmap(int(i * 255. / nPuffs)) for i in np.arange(nPuffs)]
        self.colors = [tuple([int(c * 255) for c in col]) for col in self.colors]

        self.setGeometry(QRect(1065, 121, 749, 948))
        self.setWindowTitle('Group Analyzer')

        self.hbox = QGridLayout()
        self.setLayout(self.hbox)
        self.area = DockArea()
        self.hbox.addWidget(self.area)
        self.d1 = Dock("Measured amplitude over time", size=(500, 300))
        self.d2 = Dock("Variables", size=(146, 400))
        self.d3 = Dock("Event View", size=(500, 400))
        self.d4 = Dock("X over time", size=(500, 300))
        self.d5 = Dock("Y over time", size=(500, 300))
        self.d6 = Dock("Fitted amplitude over time", size=(500, 300))
        self.d7 = Dock("Sigma over time", size=(500, 300))
        self.d8 = Dock("3D fit", size=(500, 400))
        self.d9 = Dock("Puff Data", size=(500, 400))
        self.area.addDock(self.d6,
                          'left')  ## place d1 at left edge of dock area (it will fill the whole space since there are no other docks yet)
        self.area.addDock(self.d2, 'right', self.d6)  ## place d2 at right edge of dock area
        self.area.addDock(self.d8, 'bottom')
        self.area.addDock(self.d9, 'below', self.d8)
        self.area.addDock(self.d3, 'above', self.d8)  ## place d3 at bottom edge of d1
        self.area.addDock(self.d4, 'below', self.d6)
        self.area.addDock(self.d5, 'below', self.d4)
        self.area.addDock(self.d7, 'below', self.d5)
        self.area.addDock(self.d1, 'above', self.d6)

        self.p1 = pg.PlotWidget(title="Measured amplitude over time")
        self.d1.addWidget(self.p1)
        self.p2 = pg.PlotWidget(title="Fitted amplitude over time")
        self.d6.addWidget(self.p2)
        self.p3 = pg.PlotWidget(title="Fitted X over time")
        self.d4.addWidget(self.p3)
        self.p4 = pg.PlotWidget(title="Fitted Y over time")
        self.d5.addWidget(self.p4)
        self.p5 = pg.PlotWidget(title="Fitted Sigma over time")
        self.d7.addWidget(self.p5)
        self.puff_3D = puff_3D()
        self.d8.addWidget(self.puff_3D)
        self.table = pg.TableWidget()
        self.d9.addWidget(self.table)
        self.formlayout = QFormLayout()
        self.puffCheckBoxes = [QCheckBox() for puff in group.puffs]
        for i in np.arange(nPuffs):
            self.puffCheckBoxes[i].setChecked(True)
            self.puffCheckBoxes[i].stateChanged.connect(self.replot)
            self.formlayout.addRow('Puff ' + str(i), self.puffCheckBoxes[i])
        self.alignAverageCheckBox = QCheckBox()
        self.formlayout.addRow('Align Average', self.alignAverageCheckBox)
        self.currentPuff = QComboBox()
        for i in np.arange(nPuffs):
            self.currentPuff.addItem('Puff ' + str(i))
        self.currentPuff.currentIndexChanged.connect(self.changeCurrentPuff)
        self.formlayout.addRow('Current Puff', self.currentPuff)
        # self.exportButton=QPushButton("Export")
        # self.exportButton.clicked.connect(self.export)
        # self.formlayout.addWidget(self.exportButton)
        self.formWidget = QWidget()
        self.formWidget.setLayout(self.formlayout)
        self.d2.addWidget(self.formWidget)
        self.imageview = pg.ImageView()
        puff = self.group.puffs[self.currentPuff.currentIndex()]
        self.bounds = np.copy(puff.bounds)
        self.bounds[0, 0] = puff.kinetics['before']
        self.bounds[0, 1] = puff.kinetics['after']

        bb = self.bounds
        self.I = self.group.puffs[0].puffs.normalized_window.image[bb[0][0]:bb[0][1] + 1, bb[1][0]:bb[1][1] + 1,
                 bb[2][0]:bb[2][1] + 1]

        self.imageview.setImage(self.I)
        self.addedItems = []
        self.sigTimeChanged.connect(self.updateTime)
        self.imageview.timeLine.sigPositionChanged.connect(self.updateindex)
        self.d3.addWidget(self.imageview)
        self.params = []
        self.I_fits = []
        for puff in self.group.puffs:
            param, I_fit = self.getParamsOverTime(puff)
            self.params.append(param)
            self.I_fits.append(I_fit)
        self.previousframe = -1
        self.replot()
        self.updatePuffTable()
        self.updateTime(0)
        self.show()

    def updatePuffTable(self):
        idx = self.currentPuff.currentIndex()
        puff = self.group.puffs[idx]
        dt = -(puff.kinetics['t_start'] - puff.kinetics['before'])

        params = self.params[idx]
        peak_amp = np.max(params[:, 3])
        if len(self.params) > 1:
            dtype = [('Frame (absolute)', int), ('Frame (relative)', int), ('x', float), ('y', float), ('sigma', float),
                     ('amplitude', float), ('x relative to mean (exclusive)', float),
                     ('y relative to mean (exclusive)', float), ('distance to puff center (exclusive)', float),
                     ('peak amplitude', float)]
            other_params = []
            for i in np.arange(len(self.params)):
                if i != idx:
                    other_params.append(self.params[i])
            other_params = np.vstack(other_params)
            other_x = np.sum(other_params[:, 0] * other_params[:, 3]) / np.sum(other_params[:, 3])
            mean_x = np.sum(params[:, 0] * params[:, -3]) / np.sum(params[:, -3])
            rel_x = mean_x - other_x
            other_y = np.sum(other_params[:, 1] * other_params[:, 3]) / np.sum(other_params[:, 3])
            mean_y = np.sum(params[:, 1] * params[:, -3]) / np.sum(params[:, -3])
            rel_y = mean_y - other_y
            dist = np.sqrt(rel_x ** 2 + rel_y ** 2)

            data = [tuple([i + dt + puff.kinetics['t_start']] + [i + dt] + list(row) + [rel_x, rel_y, dist, peak_amp])
                    for i, row in enumerate(params)]
        else:
            dtype = [('Frame (absolute)', int), ('Frame (relative)', int), ('x', float), ('y', float), ('sigma', float),
                     ('amplitude', float), ('peak amplitude', float)]
            data = [tuple([i + dt + puff.kinetics['t_start']] + [i + dt] + list(row) + [peak_amp]) for i, row in
                    enumerate(params)]
        data = np.array(data, dtype=dtype)
        self.table.setData(data)

    def updateindex(self):
        (idx, t) = self.imageview.timeIndex(self.imageview.timeLine)
        t = int(np.ceil(t))
        self.currentIndex = t
        self.sigTimeChanged.emit(t)

    def replot(self):
        self.error_bars = []
        for p in [self.p1, self.p2, self.p3, self.p4, self.p5]:
            p.clear()
        currentPuff = self.group.puffs[self.currentPuff.currentIndex()]
        x = -(currentPuff.kinetics['t_start'] - currentPuff.kinetics['before'])
        self.vLine1 = self.p1.addLine(x=x, pen=pg.mkPen('y'))
        self.vLine2 = self.p2.addLine(x=x, pen=pg.mkPen('y'))
        # self.vLine3=self.p3.addLine(x=x,pen=pg.mkPen('y'))
        ##self.vLine4=self.p4.addLine(x=x,pen=pg.mkPen('y'))
        self.vLine5 = self.p5.addLine(x=x, pen=pg.mkPen('y'))
        for i, puff in enumerate(self.group.puffs):
            if self.puffCheckBoxes[i].isChecked():
                pen = pg.mkPen(pg.mkColor(self.colors[i]))
                x = np.arange(len(puff.trace)) + puff.kinetics['before'] - self.offsets[i]
                self.p1.plot(x, puff.trace, pen=pen)
                self.p2.plot(x, self.params[i][:, 3], pen=pen)  # amplitude
                self.p3.plot(x, self.params[i][:, 0], pen=pen)  # x
                self.p4.plot(x, self.params[i][:, 1], pen=pen)  # y
                self.p5.plot(x, self.params[i][:, 2], pen=pen)  # sigma

    def getParamsOverTime(self, puff):
        print('getting parameters')
        bb = puff.bounds
        puff.udc['rotatedfit'] = False

        def getFitParams(idx):
            xorigin, yorigin = puff.clusters.origins[idx, 1:] - np.array([bb[1][0], bb[2][0]])
            sigma = puff.clusters.standard_deviations[idx]
            x_lower = xorigin - sigma
            x_upper = xorigin + sigma
            y_lower = yorigin - sigma
            y_upper = yorigin + sigma
            amplitude = np.max(I) / 2
            sigma = 3
            if puff.udc['rotatedfit']:
                sigmax = sigma
                sigmay = sigma
                angle = 45
                p0 = (xorigin, yorigin, sigmax, sigmay, angle, amplitude)
                #                 xorigin                   yorigin             sigmax, sigmay, angle,    amplitude
                fit_bounds = [(x_lower, x_upper), (y_lower, y_upper), (2, puff.udc['maxSigmaForGaussianFit']),
                              (2, puff.udc['maxSigmaForGaussianFit']), (0, 90), (0, np.max(I))]
            else:
                p0 = (xorigin, yorigin, sigma, amplitude)
                #                 xorigin                   yorigin            sigma    amplitude
                fit_bounds = [(x_lower, x_upper), (y_lower, y_upper), (1.5, puff.udc['maxSigmaForGaussianFit']), (
                0, np.max(I))]  # [(0.0, 2*self.paddingXY), (0, 2*self.paddingXY),(0,10),(0,10),(0,90),(0,5)]
            return p0, fit_bounds

        [(t0, t1), (x0, x1), (y0, y1)] = puff.bounds
        params = []
        I = puff.puffs.normalized_window.image[puff.kinetics['before']:puff.kinetics['after'] + 1,
            bb[1][0]:bb[1][1] + 1, bb[2][0]:bb[2][1] + 1]
        p0, fit_bounds = getFitParams(puff.starting_idx)

        puff.sisterPuffs = []  # the length of this list will show how many gaussians to fit
        for idx, cluster in enumerate(puff.clusters.bounds):
            if np.any(np.intersect1d(np.arange(cluster[0, 0], cluster[1, 0]), np.arange(t0, t1))):
                if np.any(np.intersect1d(np.arange(cluster[0, 1], cluster[1, 1]), np.arange(x0, x1))):
                    if np.any(np.intersect1d(np.arange(cluster[0, 2], cluster[1, 2]), np.arange(y0, y1))):
                        if idx != puff.starting_idx:
                            puff.sisterPuffs.append(idx)
        for puf in puff.sisterPuffs:
            sister_p0, sister_fit_bounds = getFitParams(puf)
            p0 = p0 + sister_p0
            fit_bounds = fit_bounds + sister_fit_bounds
        Is = []
        for t in np.arange(len(I)):
            I_t = I[t]
            if puff.udc['rotatedfit']:
                p, I_fit, I_fit2 = fitRotGaussian(I_t, p0, fit_bounds, nGaussians=1 + len(puff.sisterPuffs))
                p[0] = p[0] + bb[1][0]  # Put back in regular coordinate system.  Add back x
                p[1] = p[1] + bb[2][0]  # add back y
                # xorigin,yorigin,sigmax,sigmay,angle,amplitude=p
            else:

                p, I_fit, I_fit2 = fitGaussian(I_t, p0, fit_bounds, nGaussians=1 + len(puff.sisterPuffs))
                p[0] = p[0] + bb[1][0]  # Put back in regular coordinate system.  Add back x
                p[1] = p[1] + bb[2][0]  # add back y
                # xorigin,yorigin,sigma,amplitude=p
            params.append(np.array(p))
            Is.append(I_fit2)
        params = np.array(params)
        Is = np.array(Is)
        return params, Is

    def changeCurrentPuff(self):
        idx = self.currentPuff.currentIndex()
        puff = self.group.puffs[idx]
        self.bounds = np.copy(puff.bounds)
        self.bounds[0, 0] = puff.kinetics['before']
        self.bounds[0, 1] = puff.kinetics['after']
        bb = self.bounds
        self.I = self.group.puffs[idx].puffs.normalized_window.image[bb[0][0]:bb[0][1] + 1, bb[1][0]:bb[1][1] + 1,
                 bb[2][0]:bb[2][1] + 1]
        self.imageview.setImage(self.I)
        self.updatePuffTable()
        # self.params=[self.getParamsOverTime(puff) for puff in self.group.puffs]
        self.updateTime(0)

    def updateTime(self, frame):
        if frame == self.previousframe:
            return
        self.previousframe = frame
        idx = self.currentPuff.currentIndex()
        currentPuff = self.group.puffs[idx]

        image1 = np.copy(self.I[frame])
        mmax = np.max(self.I)
        image1 = image1 / mmax
        image2 = np.copy(self.I_fits[idx][frame])
        image2 = image2 / mmax
        self.puff_3D.update_images(image1, image2)

        rel_frame = frame - (currentPuff.kinetics['t_start'] - currentPuff.kinetics['before'])
        for line in [self.vLine1, self.vLine2, self.vLine5]:  # self.vLine3,self.vLine4,self.vLine5]:
            line.setValue(rel_frame)
        for bar in self.error_bars:
            bar.plot.removeItem(bar)
        self.error_bars = []
        for item in self.addedItems:
            self.imageview.view.removeItem(item)
        self.addedItems = []

        scatter = pg.ScatterPlotItem(size=8, pen=pg.mkPen(None))
        self.imageview.view.addItem(scatter)
        self.addedItems.append(scatter)
        spots = []
        for i in np.arange(len(self.group.puffs)):
            rel_frame2 = frame - ((currentPuff.kinetics['t_start'] - currentPuff.kinetics['before']) - (
            self.group.puffs[i].kinetics['t_start'] - self.group.puffs[i].kinetics['before']))
            if self.puffCheckBoxes[i].isChecked() and rel_frame2 >= 0 and rel_frame2 < self.params[i].shape[0]:
                centers = self.params[i][:, :2] - self.bounds[1:, 0]
                center = centers[rel_frame2, :]
                amps = np.copy(self.params[i][:, -1])
                amps[amps <= 0] = .00000001
                amp = amps[rel_frame2]
                std = self.group.puffs[0].clusters.standard_deviations[i]
                color = np.array(self.colors[i])
                color[3] = 50
                ### FIRST ADD THE POINT TO THE SCATTER PLOT
                if 0.8 / amp < std:  # if the amplitude>0 and the error (0.8/SNR) is within the fitting bounds
                    ### FIRST PLOT THE

                    """ WARNING!!! the amp should really be the signal to noise ratio, so it is only valid when the image has been ratiod by the standard deviation of the noise """
                    sigma = 0.8 / amp
                    sigmas = 0.8 / amps
                    # add error bars to x and y
                    # first add X
                    color[3] = 255
                    err = pg.ErrorBarItem(x=np.array([rel_frame]), y=np.array([self.params[i][rel_frame2, 0]]),
                                          top=np.array([sigma]), bottom=np.array([sigma]), beam=0.5,
                                          pen=pg.mkPen(pg.mkColor(tuple(color))))
                    self.p3.addItem(err)
                    err.plot = self.p3
                    self.error_bars.append(err)
                    # second add Y
                    err = pg.ErrorBarItem(x=np.array([rel_frame]), y=np.array([self.params[i][rel_frame2, 1]]),
                                          top=np.array([sigma]), bottom=np.array([sigma]), beam=0.5,
                                          pen=pg.mkPen(pg.mkColor(tuple(color))))
                    self.p4.addItem(err)
                    err.plot = self.p4
                    self.error_bars.append(err)

                    reasonable_fit = sigmas < 2 * std
                    bounds = QRectF(QPointF(center[0] - sigma, center[1] - sigma), QSizeF(2 * sigma, 2 * sigma))

                    ### plot outer circle
                    pathitem = QGraphicsEllipseItem(bounds)
                    color[-1] = 127  # alpha channel
                    pathitem.setPen(pg.mkPen(pg.mkColor(tuple(color))))
                    pathitem.setBrush(pg.mkColor((0, 0, 0, 0)))
                    self.imageview.view.addItem(pathitem)
                    self.addedItems.append(pathitem)

                    ### plot line
                    frame_i = rel_frame2 - 6
                    if frame_i < 0:
                        frame_i = 0
                    alpha = 255
                    for ii in np.arange(rel_frame2, frame_i, -1) - 1:
                        if alpha <= 0 or not reasonable_fit[ii]:
                            break
                        color[-1] = alpha  # alpha channel
                        alpha = alpha - (255 * 1. / 6.)
                        pathitem = QGraphicsPathItem()
                        pathitem.setPen(pg.mkColor(tuple(color)))
                        path = QPainterPath(QPointF(*centers[ii]))
                        path.lineTo(QPointF(*centers[ii + 1]))
                        pathitem.setPath(path)
                        self.imageview.view.addItem(pathitem)
                        self.addedItems.append(pathitem)
                    color[3] = 255  # make the spot transparent
                spots.append({'pos': center, 'brush': pg.mkBrush(pg.mkColor(tuple(color)))})
        scatter.addPoints(spots)

