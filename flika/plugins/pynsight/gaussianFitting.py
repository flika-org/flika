# -*- coding: utf-8 -*-
"""
Created on Wed Jun 25 13:45:36 2014

@author: Kyle
I found another library which performs a nearly identical function after I wrote this.  It is located in https://github.com/ZhuangLab/storm-analysis/blob/master/sa_library/gaussfit.py
"""
import numpy as np
from leastsqbound import leastsqbound


def cosd(degrees):
    return np.cos(np.radians(degrees))


def sind(degrees):
    return np.sin(np.radians(degrees))


def fitGaussian(I=None, p0=None, bounds=None):
    """
    SYMETRICAL GAUSSIAN
    Takes an nxm matrix and returns an nxm matrix which is the gaussian fit
    of the first.  p0 is a list of parameters [xorigin, yorigin, sigma,amplitude]
    0-19 should be [-.2889 -.3265 -.3679 -.4263 -.5016 -.6006 ... -.0228 .01913]
    """

    x=np.arange(I.shape[0])
    y=np.arange(I.shape[1])
    X=[x,y]
    p0=[round(p,3) for p in p0] 
    p, cov_x, infodic, mesg, ier = leastsqbound(err, p0,args=(I,X),bounds = bounds, maxfev=100, full_output=True)
    #  xorigin, yorigin, sigma, amplitude=p
    I_fit=gaussian(x[:,None], y[None,:],*p)
    return p, I_fit, I_fit

        
def gaussian(x, y, xorigin, yorigin, sigma, amplitude):
    """ xorigin, yorigin, sigma, amplitude """
    return amplitude*(np.exp(-(x-xorigin)**2/(2.*sigma**2))*np.exp(-(y-yorigin)**2/(2.*sigma**2)))


def generate_gaussian(mx, sigma=1.15):
    assert mx % 2 == 1  # mx must be odd
    x = np.arange(mx)
    y = np.arange(mx)
    xorigin = int(np.floor(mx / 2.))
    yorigin = xorigin
    amplitude = 1
    I = gaussian(x[:, None], y[None, :], xorigin, yorigin, sigma, amplitude)
    I = I - (np.sum(I) / mx ** 2)
    return I
    
def gaussian_1var(p, x):
    """ xorigin, yorigin, sigma, amplitude """
    xorigin,yorigin,sigma,amplitude= p
    x0=x[0]
    x1=x[1]
    x0=x0[:,None]
    x1=x1[None,:]
    return amplitude*(np.exp(-(x0-xorigin)**2/(2.*sigma**2))*np.exp(-(x1-yorigin)**2/(2.*sigma**2)))
    
    
def err(p, y, x):
    """
    p is a tuple contatining the initial parameters.  p = (xorigin, yorigin, sigma, amplitude)
    y is the data we are fitting to (the dependent variable)
    x is the independent variable
    """
    remander = y - gaussian_1var(p, x)
    remander = remander**2
    return remander.ravel()
    

    
    
    
    
    

