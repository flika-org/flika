# -*- coding: utf-8 -*-
"""
Created on Fri Apr 22 10:58:29 2016

@author: kyle
"""
import numpy as np
import global_vars as g
from qtpy.QtGui import *
from qtpy.QtCore import *
from qtpy.QtWidgets import *
from qtpy.QtWidgets import qApp
import pyqtgraph as pg
import matplotlib
from window import Window #to display any 3d array in Flika, just call Window(array_name)
from .puffs import Puffs
cmap=matplotlib.cm.gist_rainbow

class Point():
    def __init__(self,idx, idxs):
        self.children=[]
        self.idx = idx
        self.idxs = idxs
    def __repr__(self):
        return str(self.idx)
    def getDescendants(self,N=-1):
        ''' N says how far down to look.  If N is -1, find all descendants.  If N is 0, stop looking '''
        self.descendants=self.children[:]
        if N==0:
            return []
        elif N==-1:
            N=-1
        else:
            N-=1
        for child in self.children:
            self.descendants.extend(child.getDescendants(N))
        return self.descendants
        
    def getMeanDescendantPathLength(self):
        if len(self.descendants)==0:
            return 0
        pos=self.idxs[self.idx]
        pos2=self.idxs[[d.idx for d in self.descendants]]
        d=np.sqrt(np.sum((pos2-pos)**2,1))
        return np.mean(d)
'''
self=g.m.puffAnalyzer.clusters
from plugins.detect_puffs.clusters import *
cluster_movie=g.m.currentWindow
'''
class Clusters():
    def __init__(self,higher_pts, idxs, movieShape, puffAnalyzer, persistentInfo=None):
        self.persistentInfo=persistentInfo
        if persistentInfo is not None:
            self.idxs=persistentInfo.pixel_idxs
            self.movieShape=persistentInfo.movieShape
            self.clusters=persistentInfo.clusters
            self.puffAnalyzer=puffAnalyzer
            self.getPuffs()
        else:
            self.higher_pts=higher_pts
            self.idxs=idxs
            self.movieShape=movieShape
            self.puffAnalyzer=puffAnalyzer
            self.vb=ClusterViewBox()
            self.pw=pg.PlotWidget(viewBox=self.vb)
            #  Only plot the points that are at least 1 pixel away from the next higher point, because pixels this close
            #  are guaranteed to be clustered together.
            higher_pts_tmp=self.higher_pts[self.higher_pts[:, 0] > 1]
            y = [d[0] for d in higher_pts_tmp]  # smallest distance to higher point
            x = [d[2] for d in higher_pts_tmp]  # density
            pts = np.array([x,np.log(y)]).T
            self.scatterPlot=pg.ScatterPlotItem(size=5, pen=pg.mkPen([0,0,0,255]), brush=pg.mkBrush([0,0,255,255]))      
            self.scatterPlot.setPoints(pos=pts)
            self.pw.addItem(self.scatterPlot)
            self.pw.plotItem.axes['left']['item'].setLabel('Smallest distance to brighter pixel (natural logarithm)')
            self.pw.plotItem.axes['bottom']['item'].setLabel('Pixel Intensity')
            layout = self.puffAnalyzer.algorithm_gui.circle_clusters_layout
            for i in reversed(range(layout.count())):
                layout.itemAt(i).widget().setParent(None)
            layout.addWidget(self.pw)
            self.vb.drawFinishedSignal.connect(self.manuallySelectClusterCenters)
            self.puffAnalyzer.algorithm_gui.fitGaussianButton.pressed.connect(self.finished)
        
    def getPuffs(self):
        if self.persistentInfo is None:
            cluster_sizes=np.array([len(cluster) for cluster in self.clusters])
            for i in np.arange(len(self.clusters),0,-1)-1:
                if cluster_sizes[i]<self.thresh_line.value(): 
                    del self.clusters[i]             # This gets rid of clusters that contain very few True pixels
        
        bounds=[]
        standard_deviations=[]
        origins=[]
        for i in np.arange(len(self.clusters)):
            pos=self.idxs[self.clusters[i]]
            bounds.append(np.array([np.min(pos,0),np.max(pos,0)]))
            standard_deviations.append(np.std(pos[:,1:]-np.mean(pos[:,1:],0)))
            origins.append(np.mean(pos,0))
        self.bounds=np.array(bounds)
        self.standard_deviations=np.array(standard_deviations)
        self.origins=np.array(origins)

        if self.puffAnalyzer.puffs is not None:
            self.puffAnalyzer.close()

        if self.persistentInfo is None:
            self.puffAnalyzer.puffs=Puffs(self,self.cluster_im,self.puffAnalyzer)
            self.puffAnalyzer.preSetupUI()
            self.cluster_movie.close()
        else:
            self.cluster_im = self.make_cluster_im()
            self.puffAnalyzer.puffs=Puffs(self,self.cluster_im,self.puffAnalyzer,self.persistentInfo)
        
    def finished(self):
        print('Finished with clusters! Getting puffs')
        self.getPuffs()
        
    def manuallySelectClusterCenters(self):
        if self.puffAnalyzer.generatingClusterMovie:
            return
        self.puffAnalyzer.generatingClusterMovie = True
        centers = []
        outsideROI = []
        #  Only plot the points that are at least 1 pixel away from the next higher point, because pixels this close
        #  are guaranteed to be clustered together.
        for i in np.arange(len(self.higher_pts))[self.higher_pts[:, 0] > 1]:
            y = np.log(self.higher_pts[i][0])  # smallest distance to higher point
            x = self.higher_pts[i][2]  # density
            if self.vb.currentROI.contains(x, y):
                centers.append(i)
            else:
                outsideROI.append(i)
        higher_pts2 = self.higher_pts[:, 1].astype(np.int)
        points=[Point(i, self.idxs) for i in np.arange(len(higher_pts2))]
        loop=np.arange(len(higher_pts2))
        loop=np.delete(loop,centers)
        for i in loop:
            if higher_pts2[i] != i:
                points[higher_pts2[i]].children.append(points[i])
        self.scatterPlot.clear()
        pts_outsideROI=np.array([self.higher_pts[outsideROI,2], np.log(self.higher_pts[outsideROI,0])]).T
        self.scatterPlot.addPoints(pos=pts_outsideROI, brush=pg.mkBrush([0,0,255,255]))
        pts_centers_with_large_cluster=np.array([self.higher_pts[centers, 2], np.log(self.higher_pts[centers,0])]).T
        self.scatterPlot.addPoints(pos=pts_centers_with_large_cluster, brush=pg.mkBrush([0, 255, 0, 255]))
        qApp.processEvents()
        if len(centers) == 0:
            self.puffAnalyzer.generatingClusterMovie = False
            return None

        self.puffAnalyzer.algorithm_gui.tabWidget.setCurrentIndex(2)
        self.clusters=[]
        for i, center in enumerate(centers):
            descendants=points[center].getDescendants()
            cluster=[d.idx for d in descendants]
            cluster=np.array(cluster+[center])
            self.clusters.append(cluster)
        '''
        for i, cluster in enumerate(self.clusters):
            pos = self.idxs[cluster]
            mean_pos = np.mean(pos, 0)
            values = np.exp(self.puffAnalyzer.blurred_window.image[pos[:, 0], pos[:, 1], pos[:, 2]])
            mean_pos = np.dot(values, pos) / np.sum(values)
            distances_from_center = np.sqrt(np.sum((pos[:, 1:] - mean_pos[1:]) ** 2, 1))
            times_from_center = np.abs(pos[:, 0] - mean_pos[0])
            pos_to_keep = np.logical_and(times_from_center <= self.puffAnalyzer.udc['maxPuffDiameter'],
                                         distances_from_center <= self.puffAnalyzer.udc['maxPuffLen'])
            self.clusters[i] = cluster[pos_to_keep]
        '''
        for i in np.arange(len(self.clusters), 0, -1)-1:
            if len(self.clusters[i])==0:
                del self.clusters[i]
        
        self.cluster_im = self.make_cluster_im()
        self.cluster_movie=Window(self.cluster_im, 'Cluster Movie')
        self.cluster_movie.link(self.puffAnalyzer.blurred_window)
        
        sizes=np.array([len(cluster) for cluster in self.clusters])
        sizes_bin=np.histogram(sizes,bins=np.arange(np.max(sizes)+1))
        self.p1=pg.PlotWidget()
        self.p1_curve = pg.PlotCurveItem(sizes_bin[1], sizes_bin[0], stepMode=True, fillLevel=0, brush=(0, 0, 255, 80))
        self.p1.addItem(self.p1_curve)
        self.thresh_line = pg.InfiniteLine(pos=0,movable=True)         # Add the LinearRegionItem to the ViewBox, but tell the ViewBox to exclude this item when doing auto-range calculations.
        self.p1.addItem(self.thresh_line)
        
        layout=self.puffAnalyzer.algorithm_gui.filter_clusters_layout
        for i in reversed(range(layout.count())):
            layout.itemAt(i).widget().setParent(None)
        layout.addWidget(self.p1)
        
        self.set_thresh_button = self.puffAnalyzer.algorithm_gui.threshold_button_2
        self.set_thresh_button.clicked.connect(self.set_threshold)
        self.puffAnalyzer.algorithm_gui.nClusters.setText('Number of Clusters: {}'.format(len(self.clusters)))
        self.puffAnalyzer.generatingClusterMovie=False
        
    def make_cluster_im(self):
        print('Generating Cluster Movie')
        mt, mx, my=self.movieShape
        try:
            cluster_im=np.zeros((mt,mx,my,4),dtype=np.float16)
        except MemoryError:
            g.alert('There is not enough memory to create the image of clusters (error in function clusters.make_cluster_im).')
            return None
        for i, cluster in enumerate(self.clusters):
            color = cmap(int(((i%5)*255./6)+np.random.randint(255./12)))
            pos = self.idxs[cluster]
            cluster_im[pos[:, 0], pos[:, 1], pos[:, 2], :] = color
        return cluster_im
        
    def set_threshold(self):
        threshold = self.thresh_line.value()
        n = 0
        for i, cluster in enumerate(self.clusters):
            if len(cluster) > threshold:
                n += 1
                color=cmap(int(((n % 5)*255./6)+np.random.randint(255./12)))
            else:
                color = np.zeros(4)
            pos = self.idxs[cluster]
            self.cluster_im[pos[:, 0], pos[:, 1], pos[:,2], :] = color
        self.puffAnalyzer.algorithm_gui.nClusters.setText('Number of Clusters: {}'.format(n))
        self.cluster_movie.setIndex(self.cluster_movie.currentIndex)  # This forces the movie to refresh
        self.puffAnalyzer.algorithm_gui.tabWidget.setCurrentIndex(3)
                

class ClusterViewBox(pg.ViewBox):
    drawFinishedSignal=Signal()
    EnterPressedSignal=Signal()

    def __init__(self, *args, **kwds):
        pg.ViewBox.__init__(self, *args, **kwds)
        self.currentROI=None

    def keyPressEvent(self,ev):
        if ev.key() == Qt.Key_Enter or ev.key() == Qt.Key_Return:
            self.EnterPressedSignal.emit()

    def mouseDragEvent(self, ev):
        if ev.button() == Qt.RightButton:
            ev.accept()
            self.ev=ev
            if ev.isStart():
                pt=self.mapSceneToView(self.ev.buttonDownScenePos())
                self.x=pt.x() # this sets x and y to the button down position, not the current position
                self.y=pt.y()
                #print("Drag start x={},y={}".format(self.x,self.y))
                if self.currentROI is not None:
                    self.currentROI.delete()
                self.currentROI=ROI(self,self.x,self.y)
            if ev.isFinish():
                self.currentROI.drawFinished()
                self.drawFinishedSignal.emit()
            else: # if we are in the middle of the drag between starting and finishing
                pt=self.mapSceneToView(self.ev.scenePos())
                self.x=pt.x() # this sets x and y to the button down position, not the current position
                self.y=pt.y()
                #print("Drag continuing x={},y={}".format(self.x,self.y))
                self.currentROI.extend(self.x,self.y)
        else:
            g.m.ev=ev
            pg.ViewBox.mouseDragEvent(self, ev)
            
            
class ROI(QWidget):
    def __init__(self,viewbox,x,y):
        QWidget.__init__(self)
        self.viewbox=viewbox
        self.path=QPainterPath(QPointF(x,y))
        self.pathitem=QGraphicsPathItem(self.viewbox)
        self.color=Qt.yellow
        self.pathitem.setPen(QPen(self.color))
        self.pathitem.setPath(self.path)
        self.viewbox.addItem(self.pathitem,ignoreBounds=True)
        self.mouseIsOver=False
    def extend(self,x,y):
        self.path.lineTo(QPointF(x,y))
        self.pathitem.setPath(self.path)
    def getPoints(self):
        points=[]
        for i in np.arange(self.path.elementCount()):
            e=self.path.elementAt(i)
            x=e.x; y=e.y
            if len(points)==0 or points[-1]!=(x,y):
                points.append((x,y))
        self.pts=points
        return self.pts
    def drawFinished(self):
        self.path.closeSubpath()
        self.draw_from_points(self.getPoints())
    def contains(self,x,y):
        return self.path.contains(QPointF(x,y))
    def draw_from_points(self,pts):
        self.path=QPainterPath(QPointF(pts[0][0],pts[0][1]))
        for i in np.arange(len(pts)-1)+1:        
            self.path.lineTo(QPointF(pts[i][0],pts[i][1]))
        self.pathitem.setPath(self.path)
    def delete(self):
        self.viewbox.removeItem(self.pathitem)