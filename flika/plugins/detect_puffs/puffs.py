# -*- coding: utf-8 -*-
"""
Created on Thu Apr 28 12:13:09 2016

@author: Kyle Ellefsen
"""
import numpy as np
from qtpy.QtCore import Qt
from qtpy.QtWidgets import qApp
import pyqtgraph as pg
from .gaussianFitting import fitGaussian, fitRotGaussian


def scatterRemovePoints(scatterplot,idxs):
    i2=[i for i in np.arange(len(scatterplot.data)) if i not in idxs]
    points=scatterplot.points()
    points=points[i2]
    spots=[{'pos':points[i].pos(),'data':points[i].data(),'brush':points[i].brush()} for i in np.arange(len(points))]
    scatterplot.clear()
    scatterplot.addPoints(spots)
    
def scatterAddPoints(scatterplot,pos,data):
    points=scatterplot.points()
    spots=[{'pos':points[i].pos(),'data':points[i].data()} for i in np.arange(len(points))]
    spots.extend([{'pos':pos[i],'data':data[i]} for i in np.arange(len(pos))])
    scatterplot.clear()
    scatterplot.addPoints(spots)


class Puffs:
    def __init__(self,clusters,cluster_im,puffAnalyzer,persistentInfo=None):#weakfilt,strongfilt,paddingXY,paddingT_pre,paddingT_post,maxSigmaForGaussianFit,rotatedfit):
        self.puffAnalyzer=puffAnalyzer
        self.udc=puffAnalyzer.udc        
        self.puffs=[]
        self.index=0
        self.clusters=clusters
        self.normalized_window=puffAnalyzer.normalized_window
        self.data_window=puffAnalyzer.data_window
        self.cluster_im=cluster_im
        
        self.puffs=[]
        nClusters=len(self.clusters.clusters)
        for i in np.arange(nClusters):
            percent=i/nClusters
            self.puffAnalyzer.algorithm_gui.gaussianProgress.setValue(percent*100); qApp.processEvents();
            self.puffs.append(Puff(i,self.clusters,self,persistentInfo))
        self.puffAnalyzer.algorithm_gui.gaussianProgress.setValue(100)
        qApp.processEvents()

    def refit_gaussians(self):
        for i in np.arange(len(self.puffs)):
            percent = i / len(self.puffs)
            self.puffAnalyzer.algorithm_gui.gaussianProgress.setValue(percent * 100)
            qApp.processEvents()
            puff = self.puffs[i]
            puff.refit_gaussian()
        self.puffAnalyzer.algorithm_gui.gaussianProgress.setValue(100)
        qApp.processEvents()

    def __getitem__(self, item):
        if len(self.puffs)>0:
            return self.puffs[item]
        else:
            return None

    def removeCurrentPuff(self):
        del self.puffs[self.index]
        if self.index==0:
            return self.index
        else:
            self.index-=1
        return self.index

    def getPuff(self):
        if len(self.puffs)>0:
            return self.puffs[self.index]
        else:
            return None

    def increment(self):
        self.index+=1
        if len(self.puffs)<self.index+1:
            self.index=0

    def decrement(self):
        self.index-=1
        if self.index<0:
            self.index=len(self.puffs)-1

    def setIndex(self,index):
        self.index=index
        if len(self.puffs)<self.index+1:
            self.index=0
        elif self.index<0:
            self.index=len(self.puffs)-1

    def removePuffs(self,puffs):
        idxs=[]
        for puff in puffs:
            idxs.append([point['data'] for point in self.puffAnalyzer.s1.data].index(puff))
            self.puffs.remove(puff)
        scatterRemovePoints(self.puffAnalyzer.s1,idxs)
        if self.index>=len(self.puffs):
            self.index=len(self.puffs)-1

    def addPuffs(self,puffs):
        s=self.puffAnalyzer.s1
        self.puffs.extend(puffs)
        pos=[[puff.kinetics['x'],puff.kinetics['y']] for puff in puffs]
        scatterAddPoints(s,pos,puffs)
        self.puffAnalyzer.updateScatter()
        #s.addPoints(pos=pos,data=puffs)


class Puff:
    def __init__(self, starting_idx, clusters, puffs, persistentInfo=None):
        self.starting_idx = starting_idx
        self.clusters = clusters
        self.puffs = puffs
        self.udc = puffs.udc
        self.color = (255, 0, 0, 255)
        kinetics = dict()
        originalbounds = self.clusters.bounds[starting_idx]  # 2x3 array: [[t_min,x_min,y_min],[t_max,x_max,y_max]]
        self.bounds = self.get_bounds(originalbounds)
        self.sisterPuffs = []  # This is a list of all puffs that are close enough to this puff that they would interfere with gaussian fitting, so we also fit to them at the same time.
        if persistentInfo is not None:
            self.load_persistentInfo(persistentInfo, starting_idx)
            return None
        kinetics, self.mean_image, self.gaussianFit, self.gaussianParams = self.get_xy_origin(kinetics)
        self.trace, kinetics['before'], kinetics['after'] = self.get_trace(kinetics)
        kinetics = self.calcRiseFallTimes(kinetics)
        self.kinetics = kinetics

    def refit_gaussian(self):
        """
        This function is meant to be called after the start and end times of events are manually adjusted.
        This information is stored in self.bounds, which is used to form the image that the gaussian is fit to.

        """
        kinetics = dict()
        kinetics, self.mean_image, self.gaussianFit, self.gaussianParams= self.get_xy_origin(kinetics)
        self.trace, kinetics['before'], kinetics['after'] = self.get_trace(kinetics)
        kinetics = self.calcRiseFallTimes(kinetics)
        self.kinetics = kinetics

    def load_persistentInfo(self, persistentInfo, starting_idx):
        assert persistentInfo is not None
        puff = persistentInfo.puffs[starting_idx]
        self.trace = puff['trace']
        self.kinetics = puff['kinetics']
        self.gaussianParams = puff['gaussianParams']
        self.mean_image = puff['mean_image']
        self.gaussianFit = puff['gaussianFit']
        try:
            self.color = puff.color  # (255,0,0,255)
        except:
            pass

    def get_bounds(self, originalbounds):
        t0 = originalbounds[0][0]
        t1 = originalbounds[1][0]
        x0 = originalbounds[0][1]-self.udc['paddingXY']
        x1 = originalbounds[1][1]+self.udc['paddingXY']
        y0 = originalbounds[0][2]-self.udc['paddingXY']
        y1 = originalbounds[1][2]+self.udc['paddingXY']
        mt, mx, my = self.puffs.data_window.image.shape
        if t0 < 0:
            t0 = 0
        if y0 < 0:
            y0 = 0
        if x0 < 0:
            x0 = 0
        if t1 >= mt:
            t1 = mt-1
        if y1 >= my:
            y1 = my-1
        if x1 >= mx:
            x1 = mx-1
        bounds = [(t0, t1), (x0, x1), (y0, y1)]
        return bounds

    def get_xy_origin(self, kinetics):
        #######################################################################
        #############          FIND (x,y) ORIGIN       ########################
        #######################################################################
        '''
        For debugging, use the following code:
        self=g.m.puffAnalyzer.puffs.getPuff()
        from plugins.detect_puffs.threshold_cluster import *
        '''

        [(t0, t1), (x0, x1), (y0, y1)] = self.bounds
        self.sisterPuffs = []  # the length of this list will show how many gaussians to fit
        for idx, cluster in enumerate(self.clusters.bounds):
            if np.any(np.intersect1d(np.arange(cluster[0, 0], cluster[1,0]),np.arange(t0, t1))):
                if np.any(np.intersect1d(np.arange(cluster[0, 1], cluster[1,1]),np.arange(x0, x1))):
                    if np.any(np.intersect1d(np.arange(cluster[0, 2], cluster[1,2]), np.arange(y0, y1))):
                        if idx != self.starting_idx:
                            self.sisterPuffs.append(idx)
        I = self.puffs.normalized_window.image[t0:t1+1, x0:x1+1, y0:y1+1]
        I = np.mean(I, 0)
        p0, fit_bounds = self.getStartingFitParams(self.starting_idx, I)
        for puff in self.sisterPuffs:
            sister_p0, sister_fit_bounds = self.getStartingFitParams(puff, I)
            p0 = p0+sister_p0
            fit_bounds = fit_bounds+sister_fit_bounds
        if self.udc['rotatedfit']:
            p, I_fit, I_fit2 = fitRotGaussian(I,p0,fit_bounds,nGaussians=1+len(self.sisterPuffs))
            mean_image = I
            gaussianFit = I_fit2
            p[0] = p[0]+self.bounds[1][0] #Put back in regular coordinate system.  Add back x
            p[1] = p[1]+self.bounds[2][0] #add back y
            xorigin, yorigin, sigmax, sigmay, angle, amplitude = p
            kinetics['sigmax'] = sigmax
            kinetics['sigmay'] = sigmay
            kinetics['angle'] = angle
        else:
            p, I_fit, I_fit2 = fitGaussian(I, p0, fit_bounds, nGaussians=1+len(self.sisterPuffs))
            mean_image = I
            gaussianFit = I_fit2
            p[0] = p[0]+self.bounds[1][0] #Put back in regular coordinate system.  Add back x
            p[1] = p[1]+self.bounds[2][0] #add back y
            xorigin, yorigin, sigma, amplitude = p
            kinetics['sigma'] = sigma
        kinetics['x'] = xorigin
        kinetics['y'] = yorigin
        kinetics['gaussian_amplitude'] = amplitude
        return kinetics, mean_image, gaussianFit, p

    def getStartingFitParams(self, idx, I):
        [_, (x0, x1), (y0, y1)] = self.bounds
        xorigin, yorigin = self.clusters.origins[idx, 1:] - np.array([x0, y0])
        sigma = self.clusters.standard_deviations[idx]
        if sigma < 1:
            sigma = 1
        x_lower = xorigin - sigma
        x_upper = xorigin + sigma
        y_lower = yorigin - sigma
        y_upper = yorigin + sigma
        amplitude = np.max(I) / 2
        sigma = 3
        if self.udc['rotatedfit']:
            sigmax = sigma
            sigmay = sigma
            angle = 45
            p0 = (xorigin, yorigin, sigmax, sigmay, angle, amplitude)
            #                 xorigin                   yorigin             sigmax, sigmay, angle,    amplitude
            fit_bounds = [(x_lower, x_upper), (y_lower, y_upper), (2, self.udc['maxSigmaForGaussianFit']),
                          (2, self.udc['maxSigmaForGaussianFit']), (0, 90), (0, np.max(I))]
        else:
            p0 = (xorigin, yorigin, sigma, amplitude)
            #                 xorigin                   yorigin            sigma    amplitude
            fit_bounds = [(x_lower, x_upper), (y_lower, y_upper), (2, self.udc['maxSigmaForGaussianFit']),
                          (0, np.max(I))]  # [(0.0, 2*self.paddingXY), (0, 2*self.paddingXY),(0,10),(0,10),(0,90),(0,5)]
        return p0, fit_bounds

    def get_trace(self, kinetics):
        [(t0,t1), (x0, x1), (y0, y1)] = self.bounds
        mt, mx, my = self.puffs.data_window.image.shape
        before = t0-self.udc['paddingT_pre']  # 'before' is the frame where the trace starts
        after = t1+self.udc['paddingT_post']  # 'after' is the frame where the trace ends
        if before < 0:
            before = 0
        if after >= mt:
            after = mt-1
        I = self.puffs.data_window.image[before:after+1, x0:x1+1, y0:y1+1]
        trace = np.zeros((len(I)))
        x = kinetics['x']-x0
        y = kinetics['y']-y0
        roi_width = self.udc['roi_width']
        r = roi_width/2
        bb = [x-r, x+r+1, y-r, y+r+1]
        bb = [int(round(n)) for n in bb]
        if I[0, bb[0]:bb[1], bb[2]:bb[3]].size==0: # check if roi exceeds the region we cut out of the window
            if bb[0] < 0:
                bb[0] = 0
            if bb[2] < 0:
                bb[2] = 0
            if bb[1] > I.shape[1]:
                bb[1] = I.shape[1]
            if bb[3] > I.shape[2]:
                bb[3] = I.shape[2]
        for i in np.arange(len(trace)):
            trace[i] = np.mean(I[i, bb[0]:bb[1], bb[2]:bb[3]])
        return trace, before, after

    def calcRiseFallTimes(self, kinetics):
        [(t0, t1), (x0, x1), (y0, y1)] = self.bounds
        trace = self.trace
        before = kinetics['before']
        t_start = t0-before  # t_start is how many frames into the peri-event trace the event begins
        t_end = t1-before  # t_end is how many frames into the peri-event trace the event ends
        baseline = trace[t_start]
        t_peak = np.argmax(trace[t_start:t_end+1])+t_start
        f_peak = trace[t_peak]
        amplitude = f_peak-baseline
        thresh20 = baseline+amplitude*.2
        thresh50 = baseline+amplitude*.5
        thresh80 = baseline+amplitude*.8
        tmp=np.argwhere(trace>thresh20); tmp=tmp[np.logical_and(tmp>=t_start,tmp<=t_peak)]
        if len(tmp)==0: r20=np.nan
        else:  r20=tmp[0]-t_start
        tmp=np.argwhere(trace>thresh50); tmp=tmp[np.logical_and(tmp>=t_start,tmp<=t_peak)]
        if len(tmp)==0: r50=np.nan
        else:  r50=tmp[0]-t_start
        tmp=np.argwhere(trace>thresh80); tmp=tmp[np.logical_and(tmp>=t_start,tmp<=t_peak)]
        if len(tmp)==0: r80=np.nan
        else:  r80=tmp[0]-t_start
        tmp=np.argwhere(trace<thresh80); tmp=tmp[tmp>=t_peak]
        if len(tmp)==0: f80=np.nan
        else: f80=tmp[0]-t_peak
        
        tmp=np.argwhere(trace<thresh50); tmp=tmp[tmp>=t_peak]
        if len(tmp)==0: f50=np.nan
        else: f50=tmp[0]-t_peak
        
        tmp=np.argwhere(trace<thresh20); tmp=tmp[tmp>=t_peak]
        if len(tmp)==0: f20=np.nan
        else: f20=tmp[0]-t_peak
        
        tmp=np.argwhere(trace<baseline); tmp=tmp[tmp>=t_peak]
        if len(tmp)==0:
            f0=np.nan
        else: 
            f0=tmp[0]
            if f0<t_end:
                t_end=f0
            f0=f0-t_peak
            
        kinetics['amplitude'] = amplitude
        kinetics['baseline'] = baseline
        kinetics['r20'] = r20
        kinetics['r50'] = r50
        kinetics['r80'] = r80
        kinetics['f20'] = f20
        kinetics['f50'] = f50
        kinetics['f80'] = f80
        kinetics['f0'] = f0
        kinetics['t_peak'] = t_peak+before
        kinetics['t_start'] = t0
        kinetics['t_end'] = t1
        return kinetics

    def plot(self,figure=None):
        if figure is None:
            figure=pg.plot()
        k=self.kinetics
        baseline=k['baseline']; amplitude=k['amplitude']
        #thresh20=baseline+amplitude*.2
        #thresh50=baseline+amplitude*.5
        #thresh80=baseline+amplitude*.8
        x=np.arange(len(self.trace))+k['before']
        figure.plot(x,self.trace,pen=pg.mkPen(width=2))
        #figure.plot(x,self.fStrong,pen=pg.mkPen('g'))
        #figure.plot(x,self.fWeak,pen=pg.mkPen('r'))
        self.peakLine=figure.addLine(y=baseline,pen=pg.mkPen('y',style=Qt.DashLine))
        self.baselineLine=figure.addLine(y=baseline+amplitude,pen=pg.mkPen('y',style=Qt.DashLine))
        self.startLine=figure.addLine(x=k['t_start'],pen=pg.mkPen('y',style=Qt.DashLine),movable=True,bounds=(k['before'], k['t_peak']))
        self.endLine=figure.addLine(x=k['t_end'],pen=pg.mkPen('y',style=Qt.DashLine),movable=True, bounds=(k['t_peak'], k['after']))
        self.startLine.sigDragged.connect(self.changeStartTime)
        self.endLine.sigDragged.connect(self.changeEndTime)

    def changeStartTime(self,line):
        time = line.value()
        time = int(np.round(time))
        if time != line.value():
            self.startLine.setValue(time)
        oldstart = self.kinetics['t_start']
        self.bounds[0] = (time, self.bounds[0][1])
        self.kinetics['t_start'] = time
        if oldstart!=time:
            self.kinetics = self.calcRiseFallTimes(self.kinetics)
            self.baselineLine.setValue(self.kinetics['baseline'])
            self.peakLine.setValue(self.kinetics['baseline']+self.kinetics['amplitude'])
            self.endLine.setValue(self.kinetics['t_end'])
            self.puffs.puffAnalyzer.drawRedOverlay()

    def changeEndTime(self,line):
        time = line.value()
        time = int(np.round(time))
        if time!=line.value():
            self.endLine.setValue(time)
        oldend = self.kinetics['t_end']
        if oldend!=time:   
            self.kinetics['t_end'] = time

            self.bounds[0] = (self.bounds[0][0], time)
            self.puffs.puffAnalyzer.drawRedOverlay()
    