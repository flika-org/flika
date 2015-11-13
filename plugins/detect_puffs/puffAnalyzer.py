# -*- coding: utf-8 -*-
"""
Created on Thu Jul 03 16:55:04 2014

@author: Kyle
"""
import numpy as np
import scipy
from scipy import ndimage
from scipy import stats
from window import ROI
import global_vars as g
from PyQt4 import QtGui, QtCore
import pyqtgraph.opengl as gl
from PyQt4.QtCore import pyqtSignal as Signal
from PyQt4.QtCore import pyqtSlot as Slot
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import pyqtgraph as pg
from .gaussianFitting import fitGaussian
from leastsqbound import leastsqbound
from pyqtgraph import plot, show
from scipy.ndimage.measurements import label
from .gaussianFittingReproducibility import ReproducibilityPlot


class Puff:
    def __init__(self,position,bounds,tiff,paddingXY=20,paddingT=30):
        self.position=position
        self.tiff=tiff
        self.paddingXY=paddingXY
        self.paddingT=paddingT
        self.originalbounds=bounds
        self.getbounds()
        self.trace=None
        self.gaussianFit=None
        self.gaussianParams=None #list of the form [frameN,x,y,sigma,amplitude,offset]
        self.kinetics=None
    def getbounds(self):
        p=self.position
        p=np.rint(p).astype(int)
        t0=p[0]-self.paddingT
        t1=p[0]+self.paddingT
        x0=p[1]-self.paddingXY
        x1=p[1]+self.paddingXY
        y0=p[2]-self.paddingXY
        y1=p[2]+self.paddingXY
        mt,mx,my=self.tiff.shape
        if t0<0:
            t0=0
        if y0<0:
            y0=0
        if x0<0:
            x0=0
        if t1>=mt:
            t1=mt-1
        if y1>=my:
            y1=my-1
        if x1>=mx:
            x1=mx-1
        self.bounds=[(t0,t1),(x0,x1),(y0,y1)]
    def getTrace(self,tif=None):
        if tif is None:
            tif=self.tiff
        tif=self.tiff    
        b=self.originalbounds
        b2=self.bounds
        stif=np.copy(tif[b2[0][0]:b2[0][1],b[0][1]:b[1][1]+1,b[0][2]:b[1][2]+1])
        self.trace=np.mean(np.mean(stif,1),1)
        return self.trace
    def getImage(self,frame,tiff=None):
        ''' In this function, frame is the frame number of the original video'''
        if tiff is None:
            tiff=self.tiff
        if frame>=len(tiff):
            frame=len(tiff)-1
        elif frame<0:
            frame=0
        x=np.arange(self.bounds[1][0],self.bounds[1][1])
        y=np.arange(self.bounds[2][0],self.bounds[2][1])
        return tiff[frame][x][:,y]
    def getVolume(self,tiff=None):
        if tiff is None:
            tiff=self.tiff
        t=np.arange(self.bounds[0][0],self.bounds[0][1])
        y=np.arange(self.bounds[2][0],self.bounds[2][1])
        x=np.arange(self.bounds[1][0],self.bounds[1][1])
        return tiff[t][:,x][:,:,y]
    def performGaussianFit(self):
        """This function performs a gaussian fit on every frame in self.getbounds()"""
        b=self.bounds        
        self.gaussianFit=np.zeros((b[0][1]-b[0][0],b[1][1]-b[1][0],b[2][1]-b[2][0]))
        self.gaussianParams=[]        
        p=self.position
        xorigin=p[1]-b[1][0]
        yorigin=p[2]-b[2][0]
        sigma=3
        #sigmax=1
        #sigmay=1
        #angle=0
        amplitude=1
        offset=1
        p0=(xorigin,yorigin,sigma,amplitude,offset) #(xorigin,yorigin,sigmax,sigmay,angle,amplitude,offset)
        bounds = [(0.0, 2*self.paddingXY), (0, 2*self.paddingXY),(2,5),(0,5),(0,2)]#[(0.0, 2*self.paddingXY), (0, 2*self.paddingXY),(0,10),(0,10),(0,90),(0,5),(0,2)]
        frames=np.arange(b[0][0],b[0][1])
        for i in np.arange(len(self.gaussianFit)):
            I=self.getImage(frames[i])
            p, I_fit= fitGaussian(I,p0,bounds)
            self.gaussianFit[i]=I_fit
            p[0]=p[0]+self.bounds[1][0] #Put back in regular coordinate system.  Add back x
            p[1]=p[1]+self.bounds[2][0] #add back y 
            p=list(p)
            p.insert(0,self.bounds[0][0]+i)
            p=np.array(p)
            self.gaussianParams.append(p)
        self.gaussianParams=np.array(self.gaussianParams)
                
    def getGaussianFit(self,frame):
        if self.gaussianFit is None:
            self.performGaussianFit()
        if frame<self.bounds[0][0]:
            frame=self.bounds[0][0]
        elif frame>=self.bounds[0][1]:
            frame=self.bounds[0][1]-1
        frame-=self.bounds[0][0]
        return np.copy(self.gaussianFit[frame])
        
    def getStartEndTimes(self):
        fit=np.copy(self.gaussianFit)
        offsets=self.gaussianParams[:,5]
        volume=np.copy(self.getVolume())
        mt=len(offsets)
        for i in np.arange(mt):
            volume[i]=volume[i]-offsets[i]
            fit[i]=fit[i]-offsets[i]
        remander=np.mean(np.mean(volume**2,1),1)-np.mean(np.mean((volume-fit)**2,1),1)
        remander/=(self.kinetics['delta']+1)
        #f=plot()
        #f.plot(remander)
        #f.plot(mean(mean(fit**2,1),1),pen=mkPen('g'))
        thresh=np.max(remander)*.05
        new_remander=np.copy(remander)
        labeled_array, num_features = label(new_remander>thresh)
        duration=np.where(labeled_array==labeled_array[int(mt/2)])[0]
        start=duration[0]
        end=duration[-1]        
        self.kinetics['remander']=remander
        return start, end
        
    def calculateKinetics(self):
        self.kinetics=dict()
        if self.gaussianFit is None:
            self.performGaussianFit()
            
        #### PERFORM FIT ########
        #trace=self.getTrace()
        #bounds=[(.0001,.1),(.001,10),(1,100),(.9,1.5)] #normal range: [(0,.02), (.6,1),(anything),(.9,1.2)] bounds=[(.0001,.1),(.001,10),(1,100),(.9,1.5)]
        #  # D, x0, t0, offset
        #p0=(.02,.4,20,1) #p0=(.02,.4,20,1)
        #t=np.arange(len(trace))
        #p=fitDiffusion(trace,t,p0,bounds)
        #fit=diffusion(t,*p)
        #self.kinetics['diffusion_fit_p']=p
        #self.kinetics['diffusion_fit']=fit
            
            
        sigma=self.gaussianParams[:,3]
        amplitude=self.gaussianParams[:,4]
        area=sigma**2*amplitude*2*np.pi
        self.kinetics['sigma']=sigma
        self.kinetics['amplitude']=amplitude
        self.kinetics['area']=area
        x=self.gaussianParams[:,1]
        y=self.gaussianParams[:,2]
        delta=np.sqrt((x-self.position[1])**2+(y-self.position[2])**2)
        self.kinetics['delta']=delta
        start_frame, end_frame=self.getStartEndTimes()  

        
        # another old try to get start and end points based on how much the frame-by-frame gaussian fits overlapped each other
        #        offset=self.gaussianParams[:,5]
        #        l=len(self.gaussianFit)
        #        f=np.copy(self.gaussianFit)
        #        for i in np.arange(l):
        #            f[i]=f[i]-offset[i]
        #        gaussDiff=np.zeros(self.gaussianFit.shape)
        #        for i in np.arange(2,l-2):
        #            gaussDiff[i]=f[i-1]*f[i]*f[i+1]/(area[i-1]*area[i+1])
        #        #pg.image(gaussDiff)
        #        v=np.mean(np.mean(gaussDiff,1),1)
        #        v[v<np.max(v)/10]=0
        #        pt=np.argmax(v)
        #        start_frame,end_frame=findNearestMin(v,pt)
        #        start_frame+=1
        #        end_frame-=1
        
        
        #starting point, peak point, end point
        #        ''' 
        #        To find the start and end points of the puff, I construct a distance matrix, where every element (i,j) in the matrix is the distance from the origin of the gaussian at i to the origin at j.  If you plot this matrix, for most puffs you'll see a basin in the middle.  This basin should represent the group of origins which were closest to each other.  If the origin slowly drifts over time, or moves quickly between several points, the basin still should be continous.  I threshold the matrix by half of the median matrix, find the largest continuous region in this boolean matrix.  The starting frame of the puff is the first frame in this continuous region; the ending frame is the last.
        #        '''
        #        distMat=np.zeros((len(x),len(x)))
        #        for i in np.arange(len(x)):
        #            for j in np.arange(len(x)):
        #                distMat[i,j]=np.sqrt((x[i]-x[j])**2+(y[i]-y[j])**2)
        #        #imshow(distMat)
        #        for i in np.arange(len(x)):
        #            distMat[i,i]=np.max(distMat) #the distance of 0 along the diagonals messes up segmentation, so I set this high.  
        #        distMat=distMat<np.median(distMat)/4
        #        #imshow(distMat)
        #        s=scipy.ndimage.generate_binary_structure(2,2)
        #        labeled_array, num_features = scipy.ndimage.measurements.label(distMat, structure=s)
        #        sizes = scipy.ndimage.sum(distMat,labeled_array,range(1,num_features+1)) 
        #        max_label=np.where(sizes==sizes.max())[0][0]+1
        #        start_frame=np.where(labeled_array==max_label)[0][0]
        #        end_frame=np.where(labeled_array==max_label)[0][-1]
        
        
        
        #  another old way to get start and end points as first and last frame where the value of the fitted curve rises 40% above baseline
        #        fit=fit-np.min(fit)
        #        fit=fit/np.max(fit)
        #        try:
        #            start_frame=np.where(fit>.2)[0][0]
        #        except IndexError:
        #            start_frame=0
        #        try:
        #            end_frame=np.where(fit>.4)[0][-1]
        #        except IndexError:
        #            end_frame=len(fit)-1
        
        self.kinetics['start_frame']=start_frame+self.bounds[0][0]
        self.kinetics['end_frame']=end_frame+self.bounds[0][0]
        x=x[start_frame:end_frame+1]
        y=y[start_frame:end_frame+1]
        x_0=np.mean(x)
        y_0=np.mean(y)
        delta=np.sqrt((x-x_0)**2+(y-y_0)**2)
        self.kinetics['origin']=(x_0,y_0)
        self.kinetics['sem']=stats.sem(delta)
        self.kinetics['x']=x
        self.kinetics['y']=y
        t0=self.kinetics['start_frame']-self.bounds[0][0]
        t1=self.kinetics['end_frame']-self.bounds[0][0]
        self.kinetics['mean_x']=np.mean(x)
        self.kinetics['mean_y']=np.mean(y)
        self.kinetics['mean_sigma']=np.mean(self.kinetics['sigma'][t0:t1])
        
    def getKinetics(self):
        if self.kinetics is None:
            self.calculateKinetics()
        return self.kinetics
        
    def updateStartEndFrame(self,start_frame,end_frame):
        k=self.kinetics
        k['start_frame']=start_frame
        k['end_frame']=end_frame
        x=self.gaussianParams[:,1]
        y=self.gaussianParams[:,2]
        t0=k['start_frame']-self.bounds[0][0]
        t1=k['end_frame']-self.bounds[0][0]
        k['mean_x']=np.mean(x[t0:t1])
        k['mean_y']=np.mean(y[t0:t1])
        k['mean_sigma']=np.mean(k['sigma'][t0:t1])
        
def fitDiffusion(I,t, p0, bounds):
    #data=plot(I,pen='y')
    p, cov_x, infodic, mesg, ier = leastsqbound(diffusion_err, p0,args=(I,t),bounds = bounds,ftol=.0000001,full_output=True)
    #I_fit=diffusion(t,*p)
    #data.plot(I_fit,pen='g')
    return p
        
def diffusion(t,D,x0,t0,offset):
    t=t-t0
    ans=np.zeros(len(t))
    T=t[t>0]
    ans[t>0]=np.exp(-(x0**2)/(4*D*T))/((4*np.pi*D*T)**3/2)
    ans+=offset
    return ans
def diffusion_1var(p,t):
    D,x0,t0,offset=p
    return diffusion(t,D,x0,t0,offset)
def diffusion_err(p,y,t):
    ''' 
    p is a tuple contatining the initial parameters.  p=(D,x0,t0)
    y is the data we are fitting to (the dependent variable)
    t is the independent variable
    '''
    remander=y - diffusion_1var(p, t)
    return remander
    

        

class Puffs:
    def __init__(self,positions,bounds,tiff):
        self.puffs=[]
        self.index=0
        self.puffs=[Puff(positions[i],bounds[i],tiff) for i in np.arange(len(positions))]
        self.tiff=tiff
    def __getitem__(self, item):
        return self.puffs[item]
    def removeCurrentPuff(self):
        del self.puffs[self.index]
        if len(self.puffs)>self.index+1:
            self.index-=1
        return self.index
    def getPuff(self):
        return self.puffs[self.index]
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
    #    def getFits(self):
    #        ps=[]
    #        for puff in self.puffs:
    #            if puff.kinetics is None:
    #                puff.calculateKinetics()
    #            ps.append(p.kinetics['fit_p'])
    #        ps=np.array(ps)
    #        plot(ps[:,0:1],pen=None, symbol='o')


    
    
def getCentersOfMass(puffbool,A):
    s=ndimage.generate_binary_structure(3,2)
    lbl, num_features = ndimage.measurements.label(puffbool, structure=s)
    lbls = np.arange(1, num_features+1)
    positions=ndimage.measurements.center_of_mass(A,lbl,lbls)
    
    def fn(val,pos):
        pos=[np.unravel_index(p,A.shape) for p in pos]
        pos=np.array(pos)
        p0=np.min(pos,0)
        p1=np.max(pos,0)
        return (p0,p1)
        
    bounds=ndimage.labeled_comprehension(A,lbl,lbls,fn,tuple,0,True)
    return positions,bounds

class Puff3d(gl.GLViewWidget):
    def __init__(self,puffs,parent=None):
        super(Puff3d,self).__init__(parent)
        self.setCameraPosition(distance=50)
        self.grid= gl.GLGridItem()
        self.grid.scale(2,2,1)
        self.grid.setDepthValue(10) # draw grid after surfaces since they may be translucent
        self.addItem(self.grid)
        self.puffs=puffs
        puff=self.puffs.getPuff()
        volume=puff.getVolume()
        image=puff.getImage(0)
        image-=np.min(volume)
        image/=np.max(volume)
        #z = ndimage.gaussian_filter(np.random.normal(size=(50,50)), (1,1))
        self.p1 = gl.GLSurfacePlotItem(z=image, shader='heightColor')
        ##    red   = pow(z * colorMap[0] + colorMap[1], colorMap[2])
        ##    green = pow(z * colorMap[3] + colorMap[4], colorMap[5])
        ##    blue  = pow(z * colorMap[6] + colorMap[7], colorMap[8])
        self.p1.shader()['colorMap'] = np.array([2, .2, 3, 2, .3, 5, 2, .4, 5])  
        self.p1.scale(1, 1, 15.0)
        self.p1.translate(-puff.paddingXY, -puff.paddingXY, 0)
        self.addItem(self.p1)
        self.setMinimumHeight(300)
        #self.show()
    def setFrame(self,frame):
        puff=self.puffs.getPuff()
        volume=puff.getVolume()
        image=puff.getImage(frame)
        offsets=puff.gaussianParams[:,5]
        offset=np.mean(offsets)
        image-=np.min(offset)
        image/=np.max(volume)
        self.p1.setData(z=image)
        
class Puff3d_fit(gl.GLViewWidget):
    def __init__(self,puffs,parent=None):
        super(Puff3d_fit,self).__init__(parent)
        self.setCameraPosition(distance=50)
        #self.grid= gl.GLGridItem()
        #self.grid.scale(2,2,1)
        #self.grid.setDepthValue(10) # draw grid after surfaces since they may be translucent
        #self.addItem(self.grid)
        self.puffs=puffs
        puff=self.puffs.getPuff()
        volume=puff.getVolume()
        image=puff.getImage(0)
        image-=np.min(volume)
        image/=np.max(volume)
        #z = ndimage.gaussian_filter(np.random.normal(size=(50,50)), (1,1))
        self.p1 = gl.GLSurfacePlotItem(z=image, shader='heightColor')
        self.p1.shader()['colorMap'] = np.array([2, .2, 3, 2, .3, 5, 2, .4, 5])
        self.p1.scale(1, 1, 15.0)
        self.p1.translate(-puff.paddingXY, -puff.paddingXY, 0)
        self.addItem(self.p1)
        self.setMinimumHeight(300)
        #self.show()
    def setFrame(self,frame):
        puff=self.puffs.getPuff()
        volume=puff.getVolume()
        image=self.puffs.getPuff().getGaussianFit(frame)
        offsets=puff.gaussianParams[:,5]
        offset=np.mean(offsets)
        image-=np.min(offset)
        image/=np.max(volume)
        self.p1.setData(z=image)
        
class PuffAnalyzer(QtGui.QWidget):
    closeSignal=Signal()
    def __init__(self,puffs,parent=None):
        super(PuffAnalyzer,self).__init__(parent) ## Create window with ImageView widget
        self.puffs=puffs
        self.setWindowTitle('Puff Analyzer')
        self.setGeometry(QtCore.QRect(360, 368, 1552, 351))
        self.l = QtGui.QVBoxLayout()
        self.l_mid=QtGui.QGridLayout()
        self.threeD_Holder=QtGui.QHBoxLayout()
        self.l_bottom=QtGui.QGridLayout()
        self.p1=pg.PlotWidget()
        self.p4=pg.PlotWidget()
        self.p1.setMaximumWidth(600)
        #self.p1.setAutoVisible(y=True)
        self.p2=Puff3d(self.puffs)
        self.p3=Puff3d_fit(self.puffs)
        self.show()
        self.vLine = pg.InfiniteLine(angle=90, movable=True)
        self.vLine.setPos(self.puffs[0].position[0])
        self.startLine = pg.InfiniteLine(pen=QPen(Qt.green),angle=90, movable=True)
        self.startLine.setPos(self.puffs[0].position[0])
        self.endLine = pg.InfiniteLine(pen=QPen(Qt.cyan),angle=90, movable=True)
        self.endLine.setPos(self.puffs[0].position[0])        
        
        self.proxy = pg.SignalProxy(self.vLine.sigDragged, rateLimit=60, slot=self.lineDragged)
        self.proxy2 = pg.SignalProxy(self.startLine.sigDragged, rateLimit=60, slot=self.startlineDragged)
        self.proxy3 = pg.SignalProxy(self.endLine.sigDragged, rateLimit=60, slot=self.endlineDragged)
        
        self.prevButton=QtGui.QPushButton('Previous')
        self.currentPuff_spinbox=QtGui.QSpinBox()
        self.currentPuff_spinbox.setMaximum(len(self.puffs.puffs)-1)
        self.nextButton=QtGui.QPushButton('Next')
        self.nextButton.pressed.connect(self.increment)
        self.currentPuff_spinbox.valueChanged.connect(self.setCurrPuff)
        self.prevButton.pressed.connect(self.decrement)
        self.discardButton=QtGui.QPushButton('Discard')
        self.analyzeButton=QtGui.QPushButton('Reproducibility')
        self.analyzeButton.pressed.connect(self.getGaussianReproducibility)
        self.l_bottom.addWidget(self.prevButton,0,0)
        self.l_bottom.addWidget(self.currentPuff_spinbox,0,1)
        self.l_bottom.addWidget(self.nextButton,0,2)
        self.l_bottom.addWidget(self.discardButton,0,5)
        self.l_bottom.addWidget(self.analyzeButton,0,6)
        self.l.addLayout(self.threeD_Holder)
        self.l.addLayout(self.l_mid)
        self.l.addLayout(self.l_bottom)
        self.threeD_Holder.addWidget(self.p2)
        self.threeD_Holder.addWidget(self.p3)
        self.l_mid.addWidget(self.p1,0,0)
        self.l_mid.addWidget(self.p4,0,1)
        self.setLayout(self.l)
        self.tifs=[]
        #self.changePuff()
        
    def increment(self):
        self.puffs.increment()
        self.changePuff()
    def decrement(self):
        self.puffs.decrement()
        self.changePuff()
    def getGaussianReproducibility(self):
        mat=g.m.currentWindow.image[200:300].mean(0)
        self.reproducibility=ReproducibilityPlot(mat)
    def getGaussianFit(self):
        self.puffs.getPuff().performGaussianFit()
    @Slot(int)
    def setCurrPuff(self,value):
        self.puffs.setIndex(value)
        self.changePuff()
    def changePuff(self):
        self.vLine.setPos(self.puffs[self.puffs.index].position[0])
        self.puffChanged()
        if self.currentPuff_spinbox.value()!=self.puffs.index:
            self.currentPuff_spinbox.setValue(self.puffs.index)
        puff=self.puffs.getPuff()
        x=puff.kinetics['mean_x']; y=puff.kinetics['mean_y']; sigma=puff.kinetics['mean_sigma']
        (t0,t1),(x0,x1),(y0,y1)=tuple(puff.bounds)
        for tif in self.tifs:
            tif['roi_big'].draw_from_points([(x0,y0),(x0,y1),(x1,y1),(x1,y0),(x0,y0)])
            tif['roi_small'].draw_from_points([(x-sigma,y-sigma),(x-sigma,y+sigma),(x+sigma,y+sigma),(x+sigma,y-sigma),(x-sigma,y-sigma)])
            tif['roi_small'].translate_done.emit()
            tif['tif'].setIndex(np.mean([t0,t1]))
        g.m.currentTrace.region.setRegion([t0, t1])
        #self.traceWidget.getPlotItem().getViewBox().setXRange(min(trace[0]),max(trace[0]))

    @Slot()
    def puffChanged(self):
        frame=self.vLine.value()
        frame=int(np.floor(frame))
        puff=self.puffs.getPuff()
        if puff.gaussianFit is None:
            puff.performGaussianFit()
        self.p2.setFrame(frame)
        self.p3.setFrame(frame)
        
        self.p1.clear()
        self.p4.clear()
        labelStyle={'color':'magenta','font-size':'12pt','font-family':'Helvetica'}
        self.p1.plotItem.axes['left']['item'].setLabel('Original Trace',**labelStyle)
        k=puff.getKinetics()
        trace=puff.getTrace()
        x=k['x']
        y=k['y']
        amp=k['amplitude']
        sig=k['sigma']
        #fit=k['diffusion_fit']
        
        x=x-np.mean(x)
        y=y-np.mean(y)
        
        
        self.p1.plot(trace,pen=QPen(Qt.magenta))
        self.startLine.setPos(k['start_frame'])
        self.endLine.setPos(k['end_frame'])

        
        self.plotOrigin(frame)
        self.p4.plot(puff.kinetics['remander'], pen=QPen(Qt.cyan))
        self.p4.startLine = pg.InfiniteLine(angle=90, movable=False)
        self.p4.startLine.setPos(k['start_frame']-puff.bounds[0][0])
        self.p4.endLine = pg.InfiniteLine(angle=90, movable=False)
        self.p4.endLine.setPos(k['end_frame']-puff.bounds[0][0])
        self.p4.plotItem.addItem(self.p4.startLine)
        self.p4.plotItem.addItem(self.p4.endLine)
        labelStyle['color']='cyan'
        self.p4.plotItem.axes['left']['item'].setLabel('Remander',**labelStyle)
        self.p4.plotItem.axes['left']['item'].show()
        
        #for tif in self.tifs:
            #x=kinetics['origin'][0]; y=kinetics['origin'][1]
            #sem=kinetics['sem']
            #path = QPainterPath()
            #path.addEllipse(QRectF(x-sem,y-sem,2*sem,2*sem))
            #tif['sem_circle'].setPath(path)
        
    @Slot()
    def lineDragged(self):
        frame=self.vLine.value()
        frame=int(np.floor(frame))
        self.p2.setFrame(frame)
        self.p3.setFrame(frame)
        self.plotOrigin(frame)
    @Slot()
    def startlineDragged(self):
        frame=self.startLine.value()
        frame=int(np.floor(frame))
        puff=self.puffs.getPuff()
        puff.updateStartEndFrame(frame,puff.kinetics['end_frame'])
        x=puff.kinetics['mean_x']; y=puff.kinetics['mean_y']; sigma=puff.kinetics['mean_sigma']
        for tif in self.tifs:
            tif['roi_small'].draw_from_points([(x-sigma,y-sigma),(x-sigma,y+sigma),(x+sigma,y+sigma),(x+sigma,y-sigma),(x-sigma,y-sigma)])
            tif['roi_small'].translate_done.emit()
        self.p2.setFrame(frame)
        self.p3.setFrame(frame)
        self.plotOrigin(frame)
    @Slot()
    def endlineDragged(self):
        frame=self.endLine.value()
        frame=int(np.floor(frame))
        puff=self.puffs.getPuff()
        puff.updateStartEndFrame(puff.kinetics['start_frame'],frame)
        x=puff.kinetics['mean_x']; y=puff.kinetics['mean_y']; sigma=puff.kinetics['mean_sigma']
        for tif in self.tifs:
            tif['roi_small'].draw_from_points([(x-sigma,y-sigma),(x-sigma,y+sigma),(x+sigma,y+sigma),(x+sigma,y-sigma),(x-sigma,y-sigma)])
            tif['roi_small'].translate_done.emit()
        self.p2.setFrame(frame)
        self.p3.setFrame(frame)
        self.plotOrigin(frame)
        
    def plotOrigin(self,frame):
        puff=self.puffs.getPuff()
        if frame>=puff.bounds[0][0] and frame<=puff.bounds[0][1]:
            x,y=puff.gaussianParams[frame-puff.bounds[0][0],1:3]
            for tif in self.tifs:
                if frame>=puff.kinetics['start_frame'] and frame<=puff.kinetics['end_frame']:
                    tif['pathitem'].setPen(QPen(Qt.red))
                else:
                    tif['pathitem'].setPen(QPen(Qt.green))
                path=QPainterPath(QPointF(x-.5,y-.5))
                path.lineTo(QPointF(x+.5,y-.5))
                path.lineTo(QPointF(x+.5,y+.5))
                path.lineTo(QPointF(x-.5,y+.5))
                path.lineTo(QPointF(x-.5,y-.5))
                tif['pathitem'].setPath(path)
    def linkTif(self,tif):
        roi_big=ROI(tif,0,0)
        roi_small=ROI(tif,0,0)
        tif.currentROI=roi_small
        tif.rois.append(roi_big)
        tif.rois.append(roi_small)
        puff=self.puffs.getPuff()
        (t0,t1),(x0,x1),(y0,y1)=tuple(puff.bounds)
        roi_big.draw_from_points([(x0,y0),(x0,y1),(x1,y1),(x1,y0),(x0,y0)])
        roi_small.draw_from_points([(x0,y0),(x0,y1),(x1,y1),(x1,y0),(x0,y0)])
        tif.setIndex(np.mean([t0,t1]))
        roi_small.plot()
        if self.vLine not in g.m.currentTrace.p1.plotItem.items:
            g.m.currentTrace.p1.getPlotItem().addItem(self.vLine, ignoreBounds=True)
        if self.startLine not in g.m.currentTrace.p1.plotItem.items:
            g.m.currentTrace.p1.getPlotItem().addItem(self.startLine, ignoreBounds=True)
        if self.endLine not in g.m.currentTrace.p1.plotItem.items:
            g.m.currentTrace.p1.getPlotItem().addItem(self.endLine, ignoreBounds=True)
        pathitem=QGraphicsPathItem(tif.imageview.view)
        pathitem.setPen(QPen(Qt.red))
        tif.imageview.view.addItem(pathitem)
        
        #sem_circle=QGraphicsPathItem(tif.imageview.view)
        #sem_circle.setPen(QPen(QColor('#00bfff')))
        #tif.imageview.view.addItem(sem_circle)
        self.tifs.append({'tif':tif,'roi_big':roi_big,'roi_small':roi_small,'pathitem':pathitem})#,'sem_circle':sem_circle})
    def closeEvent(self, event):
        self.closeSignal.emit()
        for tif in self.tifs:
            tif['roi_big'].delete()
            tif['roi_small'].delete()
            tif['tif'].imageview.view.removeItem(tif['pathitem'])
            #tif['tif'].imageview.view.removeItem(tif['sem_circle'])
        self.vLine.deleteLater()
        event.accept() # let the window close


def findNearestMin(v,pt):
    v_prime=np.concatenate(([0], np.diff(v)))
    zero_crossing=np.concatenate((np.diff(np.sign(v_prime)),[0]))
    minima=[1 if i > 1 else 0 for i in zero_crossing]
    minima[0]=1; minima[-1]=1
    minima=np.argwhere(minima)
    minima=np.union1d(minima,np.argwhere(v==0))
    return (minima[minima<pt][-1], minima[minima>pt][0])