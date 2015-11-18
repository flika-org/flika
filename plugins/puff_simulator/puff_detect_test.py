# -*- coding: utf-8 -*-
"""
Created on Fri Oct 02 12:23:06 2015

@author: Kyle Ellefsen
"""
from __future__ import (absolute_import, division,print_function, unicode_literals)
from future.builtins import (bytes, dict, int, list, object, range, str, ascii, chr, hex, input, next, oct, open, pow, round, super, filter, map, zip)

import numpy as np
import tifffile
import os
import numpy.random as random
import shutil
from window import Windows
import global_vars as g
from process.file_ import close
from process.filters import gaussian_blur
from process.binary import threshold
from process.roi import set_value
from roi import makeROI
from plugins.detect_puffs.threshold_cluster import threshold_cluster

cwd=os.path.dirname(os.path.abspath(__file__)) # cwd=r'C:\Users\Kyle Ellefsen\Documents\GitHub\Flika\plugins\puff_simulator'



from process.BaseProcess import BaseProcess_noPriorWindow, WindowSelector, MissingWindowError, SliderLabel, CheckBox
class Simulate_Puffs(BaseProcess_noPriorWindow):
    def __init__(self):
        super().__init__()
    def gui(self):
        self.gui_reset()
        nFrames=SliderLabel(0)
        nFrames.setRange(0,10000)
        self.items.append({'name':'nFrames','string':'Movie Duration (frames)','object':nFrames})
        super().gui()
    def __call__(self,nFrames=10000):
        print('called')
        self.start()
        self.newtif=generatePuffImage()
        self.newname=' Simulated Puffs '
        return self.end()
simulate_puffs=Simulate_Puffs()

def generatePuffImage(amplitude=5):
    tif=tifffile.TIFFfile(os.path.join(cwd,'model_puff.stk'))
    model_puff=tif.asarray()
    model_puff=model_puff.reshape(model_puff.shape[0:3])
    model_puff=model_puff.astype(np.float64)
    model_puff-=model_puff[0:10].mean(0) #subtract baseline
    model_puff/=model_puff.max() # divide by max to normalize
    
    A = random.randn(1100,128,128) # tif.asarray() # A[t,y,x]
    
    #puffArray=[ x,    y,   ti, ] to create puffs
    puffArray=[[ 10,    115,  50 ], 
               [ 40,   22,   100],  
               [ 110,  10,   150], 
               [ 118,  76,   200], 
               [ 50,   50,   250], 
               [ 113,  10,   300],
               [ 11,   117,  350],
               [ 15,   22,   400],
               [ 65,   64,   450],
               [ 114,  110,  500],
               [ 10,   115,  550 ], 
               [ 40,   22,   600],  
               [ 110,  10,   650], 
               [ 118,  76,   700], 
               [ 50,   50,   750], 
               [ 113,  10,   800],
               [ 11,   117,  850],
               [ 15,   22,   900],
               [ 65,   64,   950],
               [ 114,  110,  1000]]
               
    (dt,dy,dx)=model_puff.shape  
    for p in puffArray:
        t=np.arange(p[2],p[2]+dt,dtype=np.int)
        y=np.arange(p[1]-dy/2,p[1]+dy/2,dtype=np.int)
        x=np.arange(p[0]-dx/2,p[0]+dx/2,dtype=np.int)
        A[np.ix_(t,y,x)]=A[np.ix_(t,y,x)]+amplitude*model_puff
    return Window(A)
    
def detect_simulated_puffs():
    tmpdir=os.path.join(os.path.dirname(g.m.settings.config_file),'tmp')
    flika_fn='simulated_puffs.flika'
    if os.path.isdir(tmpdir):
        if flika_fn in os.listdir(tmpdir):
            pass
        else:
            shutil.rmtree(tmpdir)
            os.mkdir(tmpdir)
    else:
        os.mkdir(tmpdir)
    data_window=Window(generatePuffImage(),filename=os.path.join(tmpdir,'simulated_puffs.tif'))
    mt,mx,my=data_window.image.shape
    data_window.setWindowTitle('Data Window')
    norm_window=data_window
    medB=3
    gaussian_blur(medB,keepSourceWindow=True)
    makeROI('rectangle',pts=np.array([[medB*2,medB*2],[medB*2,my-medB*2],[mx-medB*2,my-medB*2],[mx-medB*2,medB*2],[medB*2,medB*2]]))
    set_value(0,0,mt-1,restrictToOutside=True)
    g.m.currentWindow.setWindowTitle('Lightly Blurred')
    binary_window2=threshold(.4,keepSourceWindow=True)
    norm_window.setAsCurrentWindow()
    binary_window3=threshold(2,keepSourceWindow=True)
    binary_window=Window(binary_window2.image+binary_window3.image)
    close([binary_window2,binary_window3])
    binary_window=threshold(1.5)
    binary_window.setWindowTitle('Binary Window')
    threshold_cluster(binary_window,
                      data_window,
                      norm_window,
                      rotatedfit=False, 
                      density_threshold=4, 
                      time_factor=.2, 
                      roi_width=5,
                      maxPuffLen=20, 
                      maxSigmaForGaussianFit=20,
                      load_flika_file=True)

class Simulate_Blips(BaseProcess_noPriorWindow):
    def __init__(self):
        super().__init__()
    def gui(self):
        self.gui_reset()
        nFrames=SliderLabel(0)
        nFrames.setRange(0,10000)
        self.items.append({'name':'nFrames','string':'Movie Duration (frames)','object':nFrames})
        super().gui()
    def __call__(self,nFrames=10000):
        print('called')
        self.start()
        self.newtif=generateBlipImage()
        self.newname=' Simulated Blips '
        return self.end()
simulate_blips=Simulate_Blips()

def generateBlip(sigma=1,amplitude=1,duration=1):
    sigma=int(sigma)
    width=sigma*8+1
    xorigin=sigma*4
    yorigin=sigma*4
    x=np.arange(width)
    y=np.arange(width)
    x=x[:,None]
    y=y[None,:]
    gaussian=amplitude*(np.exp(-(x-xorigin)**2/(2.*sigma**2))*np.exp(-(y-yorigin)**2/(2.*sigma**2)))
    blip=np.repeat(gaussian[None,:,:],repeats=duration,axis=0)
    return blip
    

def generateBlipImage(amplitude=1):
    A = random.randn(1100,128,128) # tif.asarray() # A[t,y,x]
    
    #puffArray=[ x,    y,   ti, sigma, amplitude, duration] to create puffs
    puffArray=[[ 10,    115,  50, 2, .2, 20], 
               [ 40,   22,   100, 2, .2, 20],  
               [ 110,  10,   150, 2, .2, 20], 
               [ 118,  76,   200, 2, .2, 20], 
               [ 50,   50,   250, 2, .2, 20], 
               [ 113,  10,   300, 2, .2, 20],
               [ 11,   117,  350, 2, .2, 20],
               [ 15,   22,   400, 2, .2, 20],
               [ 65,   64,   450, 2, .2, 20],
               [ 114,  110,  500, 2, .2, 20],
               [ 10,   115,  550, 2, .2, 20], 
               [ 40,   22,   600, 2, .2, 20],  
               [ 110,  10,   650, 2, .2, 20], 
               [ 118,  76,   700, 2, .2, 20], 
               [ 50,   50,   750, 2, .2, 20], 
               [ 113,  10,   800, 2, .2, 20],
               [ 11,   117,  850, 2, .2, 20],
               [ 15,   22,   900, 2, .2, 20],
               [ 65,   64,   950, 2, .2, 20],
               [ 114,  110, 1000, 2, .2, 20]]
               
    for p in puffArray:
        x, y, ti, sigma, amp, duration=p
        amp*=2
        blip = 3*generateBlip(sigma,amp,duration)
        dt, dx, dy = blip.shape
        dx=(dx-1)/2
        dy=(dy-1)/2
        t=np.arange(ti,ti+duration,dtype=np.int)
        y=np.arange(y-dy,y+dy+1,dtype=np.int)
        x=np.arange(x-dx,x+dx+1,dtype=np.int)
        A[np.ix_(t,y,x)]=A[np.ix_(t,y,x)]+amplitude*blip
    return Window(A)

def detect_simulated_blips(amplitude=1):
    tmpdir=os.path.join(os.path.dirname(g.m.settings.config_file),'tmp')
    flika_fn='simulated_blips.flika'
    if os.path.isdir(tmpdir):
        if flika_fn in os.listdir(tmpdir):
            pass
        else:
            shutil.rmtree(tmpdir)
            os.mkdir(tmpdir)
    else:
        os.mkdir(tmpdir)
    data_window=Window(generateBlips(amplitude),filename=os.path.join(tmpdir,'simulated_blips.tif'))
    mt,mx,my=data_window.image.shape
    data_window.setWindowTitle('Data Window')
    norm_window=data_window
    medB=3
    gaussian_blur(medB,keepSourceWindow=True)
    makeROI('rectangle',pts=np.array([[medB*2,medB*2],[medB*2,my-medB*2],[mx-medB*2,my-medB*2],[mx-medB*2,medB*2],[medB*2,medB*2]]))
    set_value(0,0,mt-1,restrictToOutside=True)
    g.m.currentWindow.setWindowTitle('Lightly Blurred')
    binary_window2=threshold(.3,keepSourceWindow=True)
    norm_window.setAsCurrentWindow()
    binary_window3=threshold(1.5,keepSourceWindow=True)
    binary_window=Window(binary_window2.image+binary_window3.image)
    close([binary_window2,binary_window3])
    binary_window=threshold(1.5)
    binary_window.setWindowTitle('Binary Window')
    threshold_cluster(binary_window,
                      data_window,
                      norm_window,
                      rotatedfit=False, 
                      density_threshold=2, 
                      time_factor=.2, 
                      roi_width=5,
                      maxPuffLen=20, 
                      maxSigmaForGaussianFit=20,
                      load_flika_file=True)