# -*- coding: utf-8 -*-
"""
Created on Wed Aug 06 15:51:52 2014

@author: Kyle Ellefsen
"""
from __future__ import (absolute_import, division,print_function, unicode_literals)
from future.builtins import (bytes, dict, int, list, object, range, str, ascii, chr, hex, input, next, oct, open, pow, round, super, filter, map, zip)
import numpy as np
from skimage.transform import rotate


class AttentionBox(object):
    def __init__(self,angle=40,radius=80):
        self.angle=np.pi*angle/180
        self.radius=radius
        self.box=np.zeros((radius*2,radius*2))
        self.center=np.array(self.box.shape)/2
        for i in np.arange(self.box.shape[0]):
            for j in np.arange(self.box.shape[1]):
                self.box[i,j]=self.calcValue(i,j)
        self.box/=np.sum(self.box)
    def gaussian(self, x, sigma):
        return 1/(sigma*np.sqrt(2*np.pi))*np.exp(-(x**2/(2*sigma**2)))
        #return np.exp(-np.power(x, 2.) / 2 * np.power(sig, 2.))
    def calcValue(self,x,y):
        x-=self.center[0]
        y-=self.center[1]
        r=np.sqrt(x**2+y**2)
        if r>=self.radius:
            return 0
        if r<self.radius/4:
            r=self.radius/2-r
        theta=np.arctan2(y,x)
        #        if np.abs(theta)>self.angle/2:
        #            return 0
        d=(self.radius-r)/self.radius
        
        return d*self.gaussian(theta,self.angle)
    def getBox(self, angle,origin,final_shape):
        '''
        Given an angle, origin, and final image shape, this returns a single 2D image of a shape placed at the 'origin' and rotated to be facing 'angle'.
        
        '''
        image=np.zeros(final_shape)
        r=self.radius
        x0=int(np.round(origin[0]-r))
        y0=int(np.round(origin[1]-r))
        bbox=[x0,y0,x0+int(2*r),y0+int(2*r)]
        box=rotate(self.box,angle)
        outOfBounds=[0,0,0,0] #This tells us how many pixels out of bounds our box is, so we can crop it. 
        if bbox[0]<0:
            outOfBounds[0]=0-bbox[0]
            bbox[0]=0
        if bbox[1]<0:
            outOfBounds[1]=0-bbox[1]
            bbox[1]=0
        if bbox[2]>final_shape[0]:
            outOfBounds[2]=bbox[2]-final_shape[0]
            bbox[2]=final_shape[0]
        if bbox[3]>final_shape[1]:
            outOfBounds[3]=bbox[3]-final_shape[1]
            bbox[3]=final_shape[1]
        box=box[outOfBounds[0]:box.shape[0]-outOfBounds[2],outOfBounds[1]:box.shape[1]-outOfBounds[3]]
        image[bbox[0]:bbox[2],bbox[1]:bbox[3]]=box
        return image
        
        

def getAttention(rTracker):
    attBox=AttentionBox()
    attention=np.zeros(rTracker.boolWindow.image.shape)
    for t in np.arange(len(attention)):
        origin=np.array(rTracker.bodyLines[t].coords[1])
        headVector=rTracker.headVectors[t]
        angle= np.arctan2(headVector[1],headVector[0])*180/np.pi
        attention[t]=attBox.getBox(angle,origin,attention[0].shape)
    return attention


if __name__=="__main__":
    #r=rodentTracker()
    attention=getAttention(r)
    
    self=AttentionBox(40,80)
    show(self.getBox(0,[100,100,200,200],(400,400)))
    
    
#    
#    
#def rf(x):
#    return np.exp(-10/x)/x
#x=np.arange(0,100,.01)
#plot(x,rf(x))

