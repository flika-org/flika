# -*- coding: utf-8 -*-
"""
Created on Thu Jun 26 16:18:16 2014

@author: Kyle Ellefsen
"""
from __future__ import (absolute_import, division,print_function, unicode_literals)
from future.builtins import (bytes, dict, int, list, object, range, str, ascii, chr, hex, input, next, oct, open, pow, round, super, filter, map, zip)

from window import Window
import numpy as np
import global_vars as g
from process.BaseProcess import BaseProcess, WindowSelector, MissingWindowError
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from trace import TraceFig

__all__ = ['deinterleave','trim','zproject','image_calculator','add_background', 'pixel_binning', 'frame_binning']

class Deinterleave(BaseProcess):
    """ deinterleave(nChannels, keepSourceWindow=False)
    This deinterleaves a stack into nChannels
    
    Parameters:
        | nChannels (int) -- The number of channels to deinterleave.
    Returns:
        newWindow
    """
    def __init__(self):
        super().__init__()
    def gui(self):
        self.gui_reset()
        nChannels=QSpinBox()
        nChannels.setMinimum(2)
        self.items.append({'name':'nChannels','string':'How many Channels?','object':nChannels})
        super().gui()
    def __call__(self,nChannels,keepSourceWindow=False):
        self.start(keepSourceWindow)

        newWindows=[]
        for i in np.arange(nChannels):
            newtif=self.tif[i::nChannels]
            name=self.oldname+' - Channel '+str(i)
            newWindow=Window(newtif,name,self.oldwindow.filename)
            newWindows.append(newWindow)
        
        if keepSourceWindow is False:
            self.oldwindow.close()  
        g.m.statusBar().showMessage('Finished with {}.'.format(self.__name__))
        return newWindows
deinterleave=Deinterleave()

class Pixel_binning(BaseProcess):
    """ pixel_binning(nPixels, keepSourceWindow=False)
    This bins the pixels to reduce the file size
    
    Parameters:
        | nPixels (int) -- The number of pixels to bin.  Example: a value of 2 will reduce file size from 256x256->128x128.
    Returns:
        newWindow
    """
    def __init__(self):
        super().__init__()
    def gui(self):
        self.gui_reset()
        nPixels=QSpinBox()
        nPixels.setMinimum(2)
        nPixels.setMaximum(2)
        self.items.append({'name':'nPixels','string':'How many adjacent pixels to bin?','object':nPixels})
        super().gui()
    def __call__(self,nPixels,keepSourceWindow=False):
        self.start(keepSourceWindow)
        tif=self.tif
        nDim=len(tif.shape)
        if nPixels==2:
            if nDim==3:
                image1=tif[:,0::2,0::2]
                image2=tif[:,1::2,0::2]
                image3=tif[:,0::2,1::2]
                image4=tif[:,1::2,1::2]
                self.newtif=(image1+image2+image3+image4)/4
                self.newname=self.oldname+' - Binned'
                return self.end()
            elif nDim==2:
                image1=tif[0::2,0::2]
                image2=tif[1::2,0::2]
                image3=tif[0::2,1::2]
                image4=tif[1::2,1::2]
                self.newtif=(image1+image2+image3+image4)/4
                self.newname=self.oldname+' - Binned'
                return self.end()
        else:
            print("2 is the only supported value for binning at the moment")
pixel_binning=Pixel_binning()

class Frame_binning(BaseProcess):
    """ frame_binning(nFrames, keepSourceWindow=False)
    This bins the pixels to reduce the file size
    
    Parameters:
        | nFrames (int) -- The number of frames to bin.  Example: a value of 2 will reduce number of frames from 1000 to 500.
    Returns:
        newWindow
    """
    def __init__(self):
        super().__init__()
    def gui(self):
        self.gui_reset()
        nFrames=QSpinBox()
        nFrames.setMinimum(2)
        nFrames.setMaximum(10000)
        self.items.append({'name':'nFrames','string':'How many frames to bin?','object':nFrames})
        super().gui()
    def __call__(self,nFrames,keepSourceWindow=False):
        self.start(keepSourceWindow)
        tif=self.tif
        nDim=len(tif.shape)
        self.newtif=np.array([np.mean(tif[i:i+nFrames],0) for i in np.arange(0,len(tif),nFrames)])
        self.newname=self.oldname+' - Binned {} frames'.format(nFrames)
        return self.end()
frame_binning=Frame_binning()


class Trim(BaseProcess):
    """ trim(firstFrame,lastFrame,increment,keepSourceWindow=False)
    This creates a new stack from the frames between the firstFrame and the lastFrame
    
    Parameters:
        | firstFrame (int) -- The index of the first frame in the stack to be kept.
        | lastFrame (int) -- The index of the last frame in the stack to be kept.
        | increment (int) -- if increment equals, then every ith frame is kept.
    Returns:
        newWindow
    """
    def __init__(self):
        super().__init__()
    def gui(self):
        self.gui_reset()
        nFrames=1
        if g.m.currentWindow is not None:
            nFrames=g.m.currentWindow.image.shape[0]
        firstFrame=QSpinBox()
        firstFrame.setMaximum(nFrames-1)
        self.items.append({'name':'firstFrame','string':'First Frame','object':firstFrame})
        lastFrame=QSpinBox()
        lastFrame.setRange(0,nFrames-1)
        lastFrame.setValue(nFrames-1)
        self.items.append({'name':'lastFrame','string':'Last Frame','object':lastFrame})
        increment=QSpinBox()
        increment.setMaximum(nFrames)
        increment.setMinimum(1)
        self.items.append({'name':'increment','string':'Increment','object':increment})
        super().gui()
    def __call__(self,firstFrame,lastFrame,increment,keepSourceWindow=False):
        self.start(keepSourceWindow)
        self.newtif=self.tif[firstFrame:lastFrame+1:increment]
        self.newname=self.oldname+' - Kept Stack'
        return self.end()
trim=Trim()


class ZProject(BaseProcess):
    """ zproject(firstFrame,lastFrame,projection_type,keepSourceWindow=False)
    This creates a new stack from the frames between the firstFrame and the lastFrame
    
    Parameters:
        | firstFrame (int) -- The index of the first frame in the stack to be kept.
        | lastFrame (int) -- The index of the last frame in the stack to be kept.
        | projection_type (str) -- Method used to combine the frames.
    Returns:
        newWindow
    """
    def __init__(self):
        super().__init__()
    def gui(self):
        self.gui_reset()
        nFrames=1
        if len(g.m.currentWindow.image.shape)!=3:
            g.m.statusBar().showMessage('zproject only works on 3 dimensional windows')
            return False
        if g.m.currentWindow is not None:
            nFrames=g.m.currentWindow.image.shape[0]
        firstFrame=QSpinBox()
        firstFrame.setMaximum(nFrames)
        self.items.append({'name':'firstFrame','string':'First Frame','object':firstFrame})
        lastFrame=QSpinBox()
        lastFrame.setRange(1,nFrames-1)
        lastFrame.setValue(nFrames-1)
        self.items.append({'name':'lastFrame','string':'Last Frame','object':lastFrame})
        projection_type=QComboBox()
        projection_type.addItem('Average')
        projection_type.addItem('Max Intensity')
        projection_type.addItem('Min Intensity')
        projection_type.addItem('Sum Slices')
        projection_type.addItem('Standard Deviation')
        projection_type.addItem('Median')
        self.items.append({'name':'projection_type','string':'Projection Type','object':projection_type})
        super().gui()
    def __call__(self,firstFrame,lastFrame,projection_type,keepSourceWindow=False):
        self.start(keepSourceWindow)
        if len(self.tif.shape)!=3:
            g.m.statusBar().showMessage('zproject only works on 3 dimensional windows')
            return False
        self.newtif=self.tif[firstFrame:lastFrame+1]
        p=projection_type
        if p=='Average':
            self.newtif=np.mean(self.newtif,0)
        elif p=='Max Intensity':
            self.newtif=np.max(self.newtif,0)
        elif p=='Min Intensity':
            self.newtif=np.min(self.newtif,0)
        elif p=='Sum Slices':
            self.newtif=np.sum(self.newtif,0)
        elif p=='Standard Deviation':
            self.newtif=np.std(self.newtif,0)
        elif p=='Median':
            self.newtif=np.median(self.newtif,0)
        self.newname=self.oldname+' {} Projection'.format(projection_type)
        return self.end()
zproject=ZProject()

class Image_calculator(BaseProcess):
    """ image_calculator(window1,window2,operation,keepSourceWindow=False)
    This creates a new stack by combining two windows in an operation
    
    Parameters:
        | window1 (Window) -- The first window 
        | window2 (Window) -- The second window
        | operation (str)  -- Method used to combine the frames.
    Returns:
        newWindow
    """
    def __init__(self):
        super().__init__()
    def gui(self):
        self.gui_reset()
        window1=WindowSelector()
        window2=WindowSelector()      
        operation=QComboBox()
        operation.addItems(['Add','Subtract','Multiply','Divide','AND','OR','XOR','Min','Max','Average'])
        self.items.append({'name':'window1','string':'Window 1','object':window1})
        self.items.append({'name':'window2','string':'Window 2','object':window2})
        self.items.append({'name':'operation','string':'Operation','object':operation})
        super().gui()
    def __call__(self,window1, window2, operation, keepSourceWindow=False):
        self.keepSourceWindow=keepSourceWindow
        g.m.statusBar().showMessage('Performing {}...'.format(self.__name__))
        if window1 is None or window2 is None:
            raise(MissingWindowError("You cannot execute '{}' without selecting a window first.".format(self.__name__)))
        A=window1.image
        B=window2.image
        nDim1=len(A.shape)
        nDim2=len(B.shape)
        xyshape1=A.shape
        xyshape2=B.shape
        if nDim1==3:
            xyshape1=xyshape1[1:]
        if nDim2==3:
            xyshape2=xyshape2[1:]
        if xyshape1!=xyshape2:
            g.m.statusBar().showMessage('The two windows have images of different shapes. They could not be combined')
            return None
        if nDim1==3 and nDim2==3:
            n1=A.shape[0]; n2=B.shape[0]
            if n1!=n2: #if the two movies have different # frames
                n=np.min([n1,n2])
                A=A[:n] #shrink them so they have the same length
                B=B[:n]
                
        
        if operation=='Add':
            self.newtif=np.add(A,B)
        elif operation=='Subtract':
            self.newtif=np.subtract(A,B)
        elif operation=='Multiply':
            self.newtif=np.multiply(A,B)
        elif operation=='Divide':
            self.newtif=np.divide(A,B)
            self.newtif[np.isnan(self.newtif)]=0
            self.newtif[np.isinf(self.newtif)]=0
        if operation=='AND':
            self.newtif=np.logical_and(window1.image,window2.image).astype('float64')
        elif operation=='OR':
            self.newtif=np.logical_or(window1.image,window2.image).astype('float64')
        elif operation=='XOR':
            self.newtif=np.logical_xor(window1.image,window2.image).astype('float64')
        elif operation=='Min':
            self.newtif=np.minimum(A,B)
        elif operation=='Max':
            self.newtif=np.maximum(A,B)
        elif operation=='Average':
            if nDim1==3 and nDim2==3:
                C=np.concatenate((np.expand_dims(A,4),np.expand_dims(B,4)),3)
                self.newtif=np.mean(C,3)
            elif nDim1==2 and nDim2==2:
                C=np.concatenate((np.expand_dims(A,3),np.expand_dims(B,3)),2)
                self.newtif=np.mean(C,2)
            else:
                if nDim1==3:
                    B=np.repeat(np.expand_dims(B,0),len(A),0)
                elif nDim2==3:
                    A=np.repeat(np.expand_dims(A,0),len(B),0)
                C=np.concatenate((np.expand_dims(A,4),np.expand_dims(B,4)),3)
                self.newtif=np.mean(C,3)
#            
        self.oldwindow=window1
        self.oldname=window1.name
        self.newname=self.oldname+' - {}'.format(operation)
        if keepSourceWindow is False:
            print('closing both windows')
            window1.close()
            window2.close()
        g.m.statusBar().showMessage('Finished with {}.'.format(self.__name__))
        newWindow=Window(self.newtif,str(self.newname),self.oldwindow.filename)
        del self.newtif
        return newWindow
        
image_calculator=Image_calculator()
    
class Add_Background(BaseProcess):
    """ 
    Kyle did not change this process?
    deinterleave(nChannels, keepSourceWindow=False)
    This deinterleaves a stack into nChannels
    
    Parameters:
        | nChannels (int) -- The number of channels to deinterleave.
    Returns:
        newWindow
    """
    def __init__(self):
        super().__init__()
    def gui(self):
        self.gui_reset()
        nChannels=QSpinBox()
        nChannels.setMinimum(2)
        self.items.append({'name':'nChannels','string':'How many Channels?','object':nChannels})
        super().gui()
    def __call__(self,nChannels,keepSourceWindow=False):
        self.start(keepSourceWindow)

        newWindows=[]
        for i in np.arange(nChannels):
            newtif=self.tif[i::nChannels]
            name=self.oldname+' - Channel '+str(i)
            newWindow=Window(newtif,name,self.oldwindow.filename)
            newWindows.append(newWindow)
        
        if keepSourceWindow is False:
            self.oldwindow.close()  
        g.m.statusBar().showMessage('Finished with {}.'.format(self.__name__))
        return newWindows
add_background=Add_Background()