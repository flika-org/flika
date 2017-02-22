# -*- coding: utf-8 -*-
"""
Created on Wed Jun 25 13:45:36 2014

@author: Kyle
I found another library which performs a nearly identical function after I wrote this.  It is located in https://github.com/ZhuangLab/storm-analysis/blob/master/sa_library/gaussfit.py
"""
import numpy as np
import pyqtgraph as pg
import pyqtgraph.opengl as gl
from qtpy import QtCore, QtWidgets
from leastsqbound import leastsqbound

def cosd(degrees):
    return np.cos(np.radians(degrees))
def sind(degrees):
    return np.sin(np.radians(degrees))

#### SYMETRICAL GAUSSIAN  
def fitGaussian(I=None, p0=None, bounds=None, nGaussians=1, display=False):
    '''
    Takes an nxm matrix and returns an nxm matrix which is the gaussian fit
    of the first.  p0 is a list of parameters [xorigin, yorigin, sigma,amplitude]
    0-19 should be [-.2889 -.3265 -.3679 -.4263 -.5016 -.6006 ... -.0228 .01913]
    '''

    x=np.arange(I.shape[0])
    y=np.arange(I.shape[1])
    if display:
        data=Puff3d(I,'Original Data')
    X=[x,y]
    p0=[round(p,3) for p in p0] 
    if nGaussians==1:
        p, cov_x, infodic, mesg, ier = leastsqbound(err, p0,args=(I,X),bounds = bounds,ftol=.0000001,full_output=True)
        #xorigin,yorigin,sigmax,sigmay,angle,amplitude=p
        I_fit=gaussian(x[:,None], y[None,:],*p)
        if not display:
            return p, I_fit, I_fit
        else:
            fitted_data=Puff3d(I_fit,'Fitted')
            return data, fitted_data, p
    elif nGaussians>=2:
        p, cov_x, infodic, mesg, ier = leastsqbound(err2, p0,args=(I,X),bounds = bounds,ftol=.0000001,full_output=True)
        #xorigin,yorigin,sigmax,sigmay,angle,amplitude=p
        I_fit=gaussian(x[:,None], y[None,:],*(p[:4]))
        I_fit2=gaussian2(x[:,None], y[None,:],*p)
        return p[:4], I_fit, I_fit2
        
def gaussian(x,y,xorigin,yorigin,sigma,amplitude):
    '''xorigin,yorigin,sigmax,sigmay,angle'''
    return amplitude*(np.exp(-(x-xorigin)**2/(2.*sigma**2))*np.exp(-(y-yorigin)**2/(2.*sigma**2)))
def gaussian_1var(p, x): #INPUT_MAT,xorigin,yorigin,sigma):
    '''xorigin,yorigin,sigmax,sigmay,angle'''
    xorigin,yorigin,sigma,amplitude= p
    x0=x[0]
    x1=x[1]
    x0=x0[:,None]
    x1=x1[None,:]
    return amplitude*(np.exp(-(x0-xorigin)**2/(2.*sigma**2))*np.exp(-(x1-yorigin)**2/(2.*sigma**2)))
def err(p, y, x):
    ''' 
    p is a tuple contatining the initial parameters.  p=(xorigin,yorigin,sigma, amplitude)
    y is the data we are fitting to (the dependent variable)
    x is the independent variable
    '''
    remander=y - gaussian_1var(p, x)
    return remander.ravel()
    
def gaussian2(x,y,*args):
    '''xorigin,yorigin,sigma,angle'''
    answer=np.zeros((x.shape[0],y.shape[1]))
    for i in np.arange(0,len(args),4):
        xorigin,yorigin,sigma,amplitude=args[i:i+4]
        answer+=amplitude*(np.exp(-(x-xorigin)**2/(2.*sigma**2))*np.exp(-(y-yorigin)**2/(2.*sigma**2)))
    return answer
def gaussian_1var2(p, X): #INPUT_MAT,xorigin,yorigin,sigma):
    '''xorigin,yorigin,sigma,angle'''
    answer=np.zeros((len(X[0]),len(X[1])))
    for i in np.arange(0,len(p),4):
        xorigin,yorigin,sigma,amplitude=p[i:i+4]
        x=X[0]-xorigin
        y=X[1]-yorigin
        x=x[:,None]
        y=y[None,:]
        answer+=amplitude*(np.exp(-x**2/(2.*sigma**2))*np.exp(-y**2/(2.*sigma**2)))
    return answer
    
def err2(p, y, x):
    ''' 
    p is a tuple contatining the initial parameters.  p=(xorigin,yorigin,sigma, amplitude)
    y is the data we are fitting to (the dependent variable)
    x is the independent variable
    '''
    remander=y - gaussian_1var2(p, x)
    return remander.ravel()
    

    
    
    
    
    
def leastsqboundWrapper(func, x0, args=(), bounds=None, Dfun=None, full_output=0, col_deriv=0, ftol=1.49012e-8, xtol=1.49012e-8, gtol=0.0, maxfev=0, epsfcn=0.0, factor=100, diag=None):
    '''Sometimes leastsqbound has a problem where if the input parameters have too many decimals, it won't change at all from the initial guess.  
    This is a hack around that by checking if the first two parameters have changed.  If they haven't, narrow the bounds by half and try again.
    '''
    x0=[round(x,3) for x in x0] 
    p, cov_x, infodic, mesg, ier = leastsqbound(func, x0, args, bounds, Dfun, full_output, col_deriv, ftol, xtol, gtol, maxfev, epsfcn, factor, diag)
    if p[0]==x0[0]:
        idx=0
    if p[1]==x0[1]:
        idx=1
    else:
        return p
    spread=bounds[idx][1]-bounds[idx][0]
    spread=spread/4
    if spread<.1 or p[-1]<.1:
        print('Origin did not shift during Gaussian Fitting')
        return p
    bounds=bounds[:] #this is required or else you permanently change the bounds
    bounds[idx]=(bounds[idx][0]+spread,bounds[idx][1]-spread)
    p=leastsqboundWrapper(func, x0, args, bounds, Dfun, full_output, col_deriv, ftol, xtol, gtol, maxfev, epsfcn, factor, diag)
    return p
    
    
    
#### ROTATABLE GAUSSIAN
def fitRotGaussian(I=None, p0=None, bounds=None, nGaussians=1, display=False):
    '''
    Takes an nxm matrix and returns an nxm matrix which is the gaussian fit
     p0 is a list of parameters [xorigin, yorigin, sigmax, sigmay, amplitude]
    '''
    x=np.arange(I.shape[0])
    y=np.arange(I.shape[1])
    if display:
        data=Puff3d(I,'Original Data')
    X=[x,y]
    if nGaussians==1:
        p= leastsqboundWrapper(err_rot, p0,args=(I,X),bounds = bounds,ftol=.0000001,full_output=True, factor=1)
        #xorigin,yorigin,sigmax,sigmay,angle,amplitude=p
        I_fit=gaussian_rot(x[:,None], y[None,:],*p)
        if not display:
            return p,I_fit, I_fit
        else:
            fitted_data=Puff3d(I_fit,'Fitted')
            return data, fitted_data, p
    elif nGaussians>=2:
        p = leastsqboundWrapper(err_rot2, p0,args=(I,X),bounds = bounds,ftol=.0000001,full_output=True)
        #xorigin,yorigin,sigmax,sigmay,angle,amplitude=p
        p_short=p[:6]
        I_fit=gaussian_rot(x[:,None], y[None,:],*p_short)
        I_fit2=gaussian_rot2(x[:,None], y[None,:],*p)
        
        return p[:6], I_fit, I_fit2
        
def gaussian_rot(x,y,xorigin,yorigin,sigmax,sigmay,angle,amplitude):
    '''xorigin,yorigin,sigmax,sigmay,angle'''
    x=x-xorigin
    y=y-yorigin
    x2=cosd(angle)*x-sind(angle)*y
    y2=sind(angle)*x+cosd(angle)*y
    return amplitude*(np.exp(-x2**2/(2.*sigmax**2))*np.exp(-y2**2/(2.*sigmay**2)))
def gaussian_rot_1var(p, X): #INPUT_MAT,xorigin,yorigin,sigma):
    '''xorigin,yorigin,sigmax,sigmay,angle, amplitude'''
    xorigin,yorigin,sigmax,sigmay,angle,amplitude = p
    x=X[0]-xorigin
    y=X[1]-yorigin
    x=x[:,None]
    y=y[None,:]
    x2=cosd(angle)*x-sind(angle)*y
    y2=sind(angle)*x+cosd(angle)*y
    return amplitude*(np.exp(-x2**2/(2.*sigmax**2))*np.exp(-y2**2/(2.*sigmay**2)))
def err_rot(p,y,x):
    remander=y - gaussian_rot_1var(p, x)
    return remander.ravel()
    
def gaussian_rot2(x,y,*args):
    '''xorigin,yorigin,sigmax,sigmay,angle'''
    answer=np.zeros((x.shape[0],y.shape[1]))
    for i in np.arange(0,len(args),6):
        xorigin,yorigin,sigmax,sigmay,angle,amplitude=args[i:i+6]
        x2=x-xorigin
        y2=y-yorigin
        x3=cosd(angle)*x2-sind(angle)*y2
        y3=sind(angle)*x2+cosd(angle)*y2
        answer+=amplitude*(np.exp(-x3**2/(2.*sigmax**2))*np.exp(-y3**2/(2.*sigmay**2)))
    return answer
def gaussian_rot_1var2(p, X): #INPUT_MAT,xorigin,yorigin,sigma):
    '''xorigin,yorigin,sigmax,sigmay,angle, amplitude'''
    answer=np.zeros((len(X[0]),len(X[1])))
    for i in np.arange(0,len(p),6):
        xorigin,yorigin,sigmax,sigmay,angle,amplitude = p[i:i+6]
        x=X[0]-xorigin
        y=X[1]-yorigin
        x=x[:,None]
        y=y[None,:]
        x2=cosd(angle)*x-sind(angle)*y
        y2=sind(angle)*x+cosd(angle)*y
        answer+=amplitude*(np.exp(-x2**2/(2.*sigmax**2))*np.exp(-y2**2/(2.*sigmay**2)))
    return answer
def err_rot2(p,y,x):
    remander=y - gaussian_rot_1var2(p, x)
    return remander.ravel()







class Puff3d(gl.GLViewWidget):
    def __init__(self,image,title,parent=None):
        super(Puff3d,self).__init__(parent)
        self.setCameraPosition(distance=50)
        self.grid= gl.GLGridItem()
        #self.grid.scale(2,2,1)
        self.grid.setDepthValue(10) # draw grid after surfaces since they may be translucent
        self.addItem(self.grid)
        #z = ndimage.gaussian_filter(np.random.normal(size=(50,50)), (1,1))
        self.p1 = gl.GLSurfacePlotItem(z=image, shader='shaded', color=(0.5, 0.5, 1, 1))
        self.p1.scale(1, 1, 10.0)
        #self.p1.translate(-volume.shape[1]/2, -volume.shape[2]/2, -volume.shape[0]/4)
        self.addItem(self.p1)
        #self.setMinimumHeight(300)
        self.setWindowTitle(title)
        self.show()
    def updateimage(self,image):
        self.p1.setData(z=image)
        
        
        
        

if __name__=='__main__':
    app = QtWidgets.QApplication([])
    x = np.arange(30,dtype=float)
    y = np.arange(30,dtype=float)
    I=gaussian_rot(x[:,None], y[None,:],xorigin=5.1,yorigin=18.5777,sigmax=1,sigmay=3,angle=45,amplitude=2)
    I+=.5*(np.random.rand(I.shape[0],I.shape[1])-.5)
    p0=(1,15,1,1,0,1)
    bounds = [(0.0, 30.0), (0, 30.0),(0,10),(0,10),(0,90),(0,5)]
    data,fitted_data,p = fitGaussian(I,p0,bounds,display=True)
    print("Fitted Values: {}".format(p))
    import sys
    sys.exit(app.exec_())
