# -*- coding: utf-8 -*-
"""
Created on Tue Aug 05 15:41:02 2014

@author: Kyle Ellefsen
"""
from __future__ import (absolute_import, division,print_function, unicode_literals)
from future.builtins import (bytes, dict, int, list, object, range, str, ascii, chr, hex, input, next, oct, open, pow, round, super, filter, map, zip)

import numpy as np
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtCore import pyqtSignal as Signal
import pyqtgraph as pg
from pyqtgraph import plot, show
from scipy.ndimage.measurements import center_of_mass
from shapely.geometry import Point, LineString, MultiPoint, Polygon
from skimage.draw import polygon
from shapely.affinity import translate,rotate,scale
from leastsqbound import leastsqbound
from .attention import getAttention
import global_vars as g



def launchRodentTracker():
    for i in np.arange(len(g.m.windows)):
        if type(g.m.windows[i]) is RodentTracker:
            g.m.windows[i].close()
    rodentTracker=RodentTracker()
    return rodentTracker

class RodentTracker(QWidget):
    closeSignal=Signal()
    def __init__(self,boolWindow=None,parent=None):
        super(RodentTracker,self).__init__(parent) ## Create window with ImageView widget
        g.m.rodentTracker=self
        self.setWindowTitle('Rodent Tracker')
        self.setGeometry(QRect(422, 35, 222, 86))
        self.l = QVBoxLayout()
        self.show()
        self.analyzeButton=QPushButton('Analyze')
        
        self.status=QLabel("Press 'Analyze' to track rodent")
        self.analyzeButton.pressed.connect(self.analyze)
        self.l.addWidget(self.status)
        self.l.addWidget(self.analyzeButton)
        self.setLayout(self.l)
        self.boolWindow=boolWindow
        self.analysisDone=False
        self.nosePoints=[None] # This will fill to be a list with all the different nose positions, one per frame
        self.bodyLines=[None] # This will fill to be a list with all the different body positions, one per frame
        self.attention_im=None
    def save(self):
        print('Save not implemented')
    def analyze(self):
        ## Set up items for displaying results
        
        if self.boolWindow is None:
            if g.m.currentWindow is None:
                self.setStatus("You must select a window before running the Rodent Tracker")
                return
            if set(np.unique(g.m.currentWindow.image.astype(np.int)))!=set([0,1]): #tests if image is not boolean
                self.setStatus('The Rodent Tracker only accepts boolean windows as input.  Select a boolean window.')
                return
            self.boolWindow=g.m.currentWindow
        self.analyzeButton.hide()
        self.scatter= pg.ScatterPlotItem(size=5, pen=pg.mkPen(None), brush=pg.mkBrush(0, 255, 0, 255))
        self.boolWindow.imageview.addItem(self.scatter)
        self.viewbox=self.boolWindow.imageview.view
        self.pathitem=QGraphicsPathItem(self.viewbox)
        self.pathitem.setPen(QPen(Qt.red,.4))
        self.viewbox.addItem(self.pathitem)
        self.boolWindow.sigTimeChanged.connect(self.updateTime)
        self.boolWindow.closeSignal.connect(self.close)
        nFrames=len(self.boolWindow.image)
        self.bodyLines=[None]*nFrames
        self.nosePoints=[None]*nFrames
        self.centers=[None]*nFrames
        self.attention=None
        self.analyzeThread=AnalyzeThread(self.bodyLines,self.nosePoints,self.boolWindow.image,self.centers)
        self.analyzeThread.finishedFrame.connect(lambda i: self.setStatus('Finished frame {}/{}'.format(i,nFrames-1)))
        self.analyzeThread.finishedAllFrames.connect(self.finishedAllFrames)
        self.analyzeThread.start()
    def setStatus(self,status):
        self.status.setText(str(status))
    def draw(self,thing):
        if type(thing) is Point:
            pos=list(thing.coords)
            self.scatter.setPoints(pos=pos)
        if type(thing) is LineString:
            points=list(thing.coords)
            path=QPainterPath(QPointF(*points[0]))
            for i in np.arange(1,len(points)):
                path.lineTo(QPointF(*points[i]))
            self.pathitem.setPath(path)
        if type(thing) is Polygon:
            points=list(thing.exterior.coords)
            path=QPainterPath(QPointF(*points[0]))
            for i in np.arange(1,len(points)):
                path.lineTo(QPointF(*points[i]))
            self.pathitem.setPath(path)
    def updateTime(self,t):
        if self.bodyLines[t] is not None:
            self.draw(self.bodyLines[t])
        if self.nosePoints[t] is not None:
            self.draw(self.nosePoints[t])
        if self.attention is not None:
            self.attention_im.setImage(self.attention[t])
    def finishedAllFrames(self):
        nFrames=len(self.boolWindow.image)
        self.headVectors=[None]*nFrames
        for t in np.arange(nFrames):
            npt=self.nosePoints[t]
            line=self.bodyLines[t]
            if npt.distance(Point(line.coords[-1]))<npt.distance(Point(line.coords[0])): # if the tail comes first in the body line
                self.bodyLines[t]=LineString(reversed(line.coords)) #reverse points so head always comes first
        
        for t in np.arange(nFrames):
            vect=np.array(self.bodyLines[t].coords[0])-np.array(self.bodyLines[t].coords[1])
            vect/=np.sqrt(np.sum(np.square(vect)))
            self.headVectors[t]=vect
        self.headVectors=np.array(self.headVectors)
        self.nosePointsArray=np.array([np.array([p.x,p.y]) for p in self.nosePoints])
        
        
        self.plotTrajectoryButton=QPushButton('Plot Trajectory (of nose)')
        self.plotTrajectoryButton.pressed.connect(self.plotTrajectory)
        self.l.addWidget(self.plotTrajectoryButton)
        self.plotAttentionButton=QPushButton('Show attention heat map')
        self.plotAttentionButton.pressed.connect(self.plotAttention)
        self.l.addWidget(self.plotAttentionButton)
        self.saveButton=QPushButton('Save')
        self.saveButton.pressed.connect(self.save)
        self.l.addWidget(self.saveButton)
        self.analysisDone=True
        
    def plotTrajectory(self):
        self.trajectoryPlot=plot(self.nosePointsArray)
        plotitem=self.trajectoryPlot.getPlotItem()
        plotitem.invertY()
        plotitem.update()
        
    def plotAttention(self):
        self.attention=getAttention(self)
        self.attention_im=pg.ImageItem(self.attention[self.boolWindow.currentIndex]) #this image item is updated with where the rodent is looking
        self.attention_im.setCompositionMode(QPainter.CompositionMode_Plus)
        self.boolWindow.imageview.addItem(self.attention_im)
        self.attentionHeatMap=show(np.mean(self.attention,0))
        
    def closeEvent(self, event):
        if self.analysisDone:
            del self.attention #release memory
            self.boolWindow.closeSignal.disconnect(self.close)
            self.boolWindow.imageview.sigTimeChanged.disconnect(self.updateTime)
            self.viewbox.removeItem(self.pathitem)
            if self.attention_im is not None:
                self.boolWindow.imageview.removeItem(self.attention_im)
            self.boolWindow.imageview.removeItem(self.scatter)
        g.m.windows.remove(self)
        event.accept() # let the window close
        
class AnalyzeThread(QThread):
    finishedFrame=Signal(int)
    finishedAllFrames=Signal()
    def __init__(self,bodyLines,nosePoints,movie,centers):
        QThread.__init__(self)
        self.bodyLines=bodyLines
        self.nosePoints=nosePoints
        self.movie=movie
        self.centers=centers
    def run(self):
        self.angle=None
        for t in np.arange(len(self.movie)):
            image=self.movie[t]
            self.bodyLines[t],self.angle, self.centers[t]=getLine(image,self.angle)
            self.finishedFrame.emit(t)
        self.nosePoints[0]=getFirstNosePoint(self.movie[0],self.bodyLines[0])
        for t in np.arange(1,len(self.movie)):
            self.nosePoints[t]=getNosePoints(self.bodyLines[t],self.nosePoints[t-1])
        self.finishedAllFrames.emit()
        return



def pts2line(pts):
    line=list(pts[0].coords)
    for i in np.arange(1,len(pts)):
        line.extend(pts[i].coords)
    return LineString(line)
def getMeanDistance(line,pts):
    return np.mean(np.array([line.distance(pt) for pt in pts]))

def crop_line(line,pts_array):
    line_start,line_end=list(line.coords)
    line_start=Point(line_start); line_end=Point(line_end)
    x=(line_start.x-line_end.x)/line.length
    y=(line_start.y-line_end.y)/line.length
    center=line.centroid
    pts=pts_array-np.array([center.x,center.y])
    pts=pts[:,0]*x+pts[:,1]*y
    return pts2line([translate(center,xoff=(np.min(pts)*x), yoff=np.min(pts)*y),translate(center,xoff=(np.max(pts)*x), yoff=np.max(pts)*y)])
def err(p,coor,pts,pt):
    line=LineString([coor[0]+p[0]*(coor[1]-coor[0]),pt])
    distance=[line.distance(pt) for pt in pts]
    return distance
def line2vector(line):
    start,end=list(line.coords)
    start=np.array(start); end=np.array(end);
    v=end-start
    v/=np.sqrt(np.sum(np.square(v)))
    return v
def multidim_intersect(A, B):
    nrows, ncols = A.shape
    dtype={'names':['f{}'.format(i) for i in range(ncols)],
           'formats':ncols * [A.dtype]}
    C = np.intersect1d(A.view(dtype), B.view(dtype))
    C = C.view(A.dtype).reshape(-1, ncols) 
    return C
def getMeanPoint(outer_axis,inner_axis,pts_array):
    poly=np.array([p for p in inner_axis.coords]+[p for p in reversed(outer_axis.coords)])
    rr, cc = polygon(poly[:, 0], poly[:, 1])
    box_array=np.column_stack((rr,cc))
    pts_inside=multidim_intersect(pts_array,box_array)
    x,y=line2vector(outer_axis)
    center=outer_axis.centroid
    pts_shifted=pts_inside-np.array([center.x,center.y])
    pts_mean=np.mean(pts_shifted[:,0]*x+pts_shifted[:,1]*y)
    new_pt=translate(center,xoff=pts_mean*x, yoff=pts_mean*y)
    return new_pt


def getLine(image,angle=None):
    """
    This function takes a boolean image of a rodent, performs several steps, and returns a line running down the middle of the rodent from nose to tail.
    The steps are:
    1) Find the point at the center of mass.
    2) Draw a horizontal line through this point.
    3) Find the mean distance from the line to every point in the rodent. Rotate the line and find the angle which gives the minimum such distance. Keep the line at this angle. This line gives a good approximation for position.
    4) Draw 7 points on the line: one at the midpoint, two at the ends, two 3/4 away from the midpoint, and two halfway between the ends and the midpoint.
    5) Construct 7 lines which run through the 7 points at an angle perpendicular to the main line.
    6) Draw 6 boxes between these 7 lines.  Find the center of mass for each box along the axes parallel to these lines.  Move each of the 7 points (except the midpoint) along their lines to the center of mass of their respective region.
    7) Draw a box around the end segment of the line.  The bounds for the box lie parallel and perpendicular to this segment.  Fixing the inner point and allowing the end point to vary, fit the segment so that the average distance from the segment to the points in the box are a minimum. This step is done for both ends of the line, because we don't as yet know which end is the head and which is the tail.
    
    """
    pts=np.where(image)
    pts_array=np.column_stack((pts[0],pts[1]))
    pts=MultiPoint([(pts[0][i],pts[1][i]) for i in np.arange(len(pts[0]))])
    # STEP 1
    x0,y0=center_of_mass(image)
    center=Point(x0,y0)
    bounds=pts.bounds
    b_len=((bounds[2]-bounds[0])**2+(bounds[3]-bounds[1])**2)**(1/2) #this is the length of the diagonal, the maximum possible length of an object inside a box
    # STEP 2
    line=pts2line([translate(center,b_len),translate(center,-b_len)])
    # STEP 3
    if angle is None:
        angles=np.arange(-90,90,10)
    else:
        angles=np.arange(angle-20,angle+20,10) #this assumes the angle changes at most 10 degrees between frames
    distances=np.zeros(angles.shape,dtype=np.float)
    for i in np.arange(len(angles)):
        distances[i]=getMeanDistance(rotate(line,angles[i]),pts)
    angle=angles[np.argmin(distances)]
    line=rotate(line,angle)
    line=crop_line(line,pts_array)
    
    # STEP 4 & 5
    # now that we have the approximate line down the main axis, let's divide it in half and allow the endpoints and midpoint to be translated along the perpendicular axis
    start,end=list(line.coords)
    start=np.array(start); end=np.array(end)
    mid=(start+end)/2
    mid_axis=rotate(line,90)
    mid_axis=crop_line(mid_axis,pts_array)
    axis1=translate(mid_axis,xoff=start[0]-mid[0],yoff=start[1]-mid[1])
    axis2=translate(mid_axis,xoff=(start[0]-mid[0])/(4./3),yoff=(start[1]-mid[1])/(4./3.))
    axis3=translate(mid_axis,xoff=(start[0]-mid[0])/2,yoff=(start[1]-mid[1])/2.)
    axis4=translate(mid_axis,xoff=(end[0]-mid[0])/2,yoff=(end[1]-mid[1])/2)
    axis5=translate(mid_axis,xoff=(end[0]-mid[0])/(4./3.),yoff=(end[1]-mid[1])/(4./3.))
    axis6=translate(mid_axis,xoff=end[0]-mid[0],yoff=end[1]-mid[1])
    
    # STEP 6
    pt1=getMeanPoint(axis1,axis2,pts_array)
    pt2=getMeanPoint(axis2,axis3,pts_array)
    pt3=getMeanPoint(axis3,mid_axis,pts_array)
    pt4=getMeanPoint(axis4,mid_axis,pts_array)
    pt5=getMeanPoint(axis5,axis4,pts_array)
    pt6=getMeanPoint(axis6,axis5,pts_array)
    
    # STEP 7
    start=pt1.coords[0]
    end=pt2.coords[0]
    headLine=LineString([start,end])
    headLine=scale(headLine,2,2)
    start=np.array(start); end=np.array(end)
    mid=(start+end)/2
    mid_axis=rotate(headLine,90)
    axis1=translate(mid_axis,xoff=(start[0]-mid[0])*2,yoff=(start[1]-mid[1])*2)
    axis2=translate(mid_axis,xoff=end[0]-mid[0],yoff=end[1]-mid[1])
    #poly=Polygon([p for p in axis1.coords]+[p for p in reversed(axis2.coords)]) #draws a box around one half of the mouse
    #pts_inside=MultiPoint([pt for pt in pts if poly.contains(pt)])
    poly=np.array([p for p in axis1.coords]+[p for p in reversed(axis2.coords)])
    rr, cc = polygon(poly[:, 0], poly[:, 1])
    box_array=np.column_stack((rr,cc))
    pts_inside=multidim_intersect(pts_array,box_array)
    if len(pts_inside)==0: #this only happens when the object lies completely outside of the box at the end of the line
        pts_inside=pts_array 
    pts_inside=MultiPoint([tuple(p) for p in pts_inside])
    
    coor=np.array([np.array(s) for s in axis1.coords])
    pt=end
    p0=(.5,)
    bounds=[(0.0,1.0)]
    p, cov_x, infodic, mesg, ier = leastsqbound(err, p0,args=(coor,pts_inside,pt),bounds = bounds,ftol=.1, full_output=True)     
    headLine=LineString([coor[0]+p[0]*(coor[1]-coor[0]),pt])
    headLine=crop_line(headLine,np.array([np.array([p.x,p.y]) for p in pts_inside]))
    pt1=Point(headLine.coords[1])
    
    start=pt6.coords[0]
    end=pt5.coords[0]
    headLine=LineString([start,end])
    headLine=scale(headLine,2,2)
    start=np.array(start); end=np.array(end)
    mid=(start+end)/2
    mid_axis=rotate(headLine,90)
    axis1=translate(mid_axis,xoff=(start[0]-mid[0])*2,yoff=(start[1]-mid[1])*2)
    axis2=translate(mid_axis,xoff=end[0]-mid[0],yoff=end[1]-mid[1])
    
    #poly=Polygon([p for p in axis1.coords]+[p for p in reversed(axis2.coords)]) #draws a box around one half of the mouse
    #pts_inside=MultiPoint([pt for pt in pts if poly.contains(pt)])
    
    poly=np.array([p for p in axis1.coords]+[p for p in reversed(axis2.coords)])
    rr, cc = polygon(poly[:, 0], poly[:, 1])
    box_array=np.column_stack((rr,cc))
    pts_inside=multidim_intersect(pts_array,box_array)
    if len(pts_inside)==0: #this only happens when the object lies completely outside of the box at the end of the line
        pts_inside=pts_array 
    pts_inside=MultiPoint([tuple(p) for p in pts_inside])
    
    
    
    coor=np.array([np.array(s) for s in axis1.coords])
    pt=end
    p0=(.5,)
    bounds=[(0.0,1.0)]
    p, cov_x, infodic, mesg, ier = leastsqbound(err, p0,args=(coor,pts_inside,pt),bounds = bounds,ftol=.1, full_output=True)     
    headLine=LineString([coor[0]+p[0]*(coor[1]-coor[0]),pt])
    headLine=crop_line(headLine,np.array([np.array([p.x,p.y]) for p in pts_inside]))
    pt6=Point(headLine.coords[1])
    
    line=pts2line([pt1,pt2,pt3,pt4,pt5,pt6])
    return line, angle, center




def getFirstNosePoint(image,line):
    pts=np.where(image)
    pts=MultiPoint([(pts[0][i],pts[1][i]) for i in np.arange(len(pts[0]))])
    line_pts=list(line.coords)
    start_line=LineString([line_pts[0],line_pts[1]])
    end_line=LineString([line_pts[-1],line_pts[-2]])
    if getMeanDistance(start_line,pts)<getMeanDistance(end_line,pts):
        nose=Point(line_pts[0])
    else:
        nose=Point(line_pts[-1])
    return nose

def getNosePoints(line,prevPoint):
        start=Point(line.coords[0])
        end=Point(line.coords[-1])
        if start.distance(prevPoint)<end.distance(prevPoint):
            return start
        else:
            return end

if __name__=='__main__':
    from skimage.io import imread, imsave
    movie=imread('D:\\Desktop\\bwmouse.tif',plugin='tifffile').astype(np.float64)
    movie=np.squeeze(movie) #this gets rid of the meaningless 4th dimention in .stk files
    movie=np.transpose(movie,(0,2,1)) # This keeps the x and y the same as in FIJI. 
    angle=30
    nFrames=len(movie)
    bodyLines=[None]*nFrames
    nosePoints=[None]*nFrames
    for t in np.arange(0,10):
        image=movie[t]
        bodyLines[t],angle=getLine(image,angle)
    nosePoints[0]=getFirstNosePoint(movie[0],bodyLines[0])
else:
    import global_vars as g

    



