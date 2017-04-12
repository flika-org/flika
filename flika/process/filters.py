# -*- coding: utf-8 -*-
import numpy as np
import skimage
import skimage.filters
from qtpy import QtWidgets, QtGui, QtCore
import time
from .. import global_vars as g
from .BaseProcess import BaseProcess, SliderLabel, SliderLabelOdd, CheckBox
from .progress_bar import ProgressBar

__all__ = ['gaussian_blur','mean_filter','median_filter','butterworth_filter','boxcar_differential_filter','wavelet_filter','difference_filter', 'fourier_filter', 'bilateral_filter']
###############################################################################
##################   SPATIAL FILTERS       ####################################
###############################################################################
class Gaussian_blur(BaseProcess):
    """ gaussian_blur(sigma, norm_edges=False, keepSourceWindow=False)

    This applies a spatial gaussian_blur to every frame of your stack.  
    
    Args:
        sigma (float): The width of the gaussian
        norm_edges (bool): If true, this reduces the values of the pixels near the edges so they have the same standard deviation as the rest of the image

    Returns:
        flika.window.Window

    """
    def __init__(self):
        super().__init__()
        assert 'gaussian' in skimage.filters.__dict__  # Make sure your version of skimage is >= 0.12.3
    def gui(self):
        self.gui_reset()
        sigma=SliderLabel(2)
        sigma.setRange(0,100)
        sigma.setValue(1)
        norm_edges=CheckBox()
        norm_edges.setChecked(False)
        preview=CheckBox()
        preview.setChecked(True)
        self.items.append({'name': 'sigma', 'string': 'Sigma (pixels)', 'object': sigma})
        self.items.append({'name': 'norm_edges', 'string': 'Normalize Edges', 'object': norm_edges})
        self.items.append({'name': 'preview', 'string': 'Preview', 'object': preview})
        super().gui()
        self.preview()

    def __call__(self, sigma, norm_edges=False, keepSourceWindow=False):
        self.start(keepSourceWindow)
        if norm_edges == True:
            mode = 'constant'
        else:
            mode = 'nearest'
        if sigma>0:
            self.newtif=np.zeros(self.tif.shape)
            if len(self.tif.shape)==3:
                for i in np.arange(len(self.newtif)):
                    self.newtif[i]=skimage.filters.gaussian(self.tif[i].astype(np.float64),sigma, mode=mode)
            elif len(self.tif.shape)==2:
                self.newtif=skimage.filters.gaussian(self.tif.astype(np.float64),sigma, mode=mode)
            self.newtif=self.newtif.astype(g.settings['internal_data_type'])
        else:
            self.newtif=self.tif
        self.newname=self.oldname+' - Gaussian Blur sigma='+str(sigma)
        return self.end()
    def preview(self):
        norm_edges = self.getValue('norm_edges')
        if norm_edges == True:
            mode = 'constant'
        else:
            mode = 'nearest'
        sigma=self.getValue('sigma')
        preview=self.getValue('preview')
        if preview:
            if len(g.currentWindow.image.shape)==3:
                testimage=g.currentWindow.image[g.currentWindow.currentIndex].astype(np.float64)
            elif len(g.currentWindow.image.shape)==2:
                testimage=g.currentWindow.image.astype(np.float64)
            if sigma>0:
                testimage=skimage.filters.gaussian(testimage,sigma, mode=mode)
            g.currentWindow.imageview.setImage(testimage,autoLevels=False)            
        else:
            g.currentWindow.reset()
gaussian_blur=Gaussian_blur()
    
    
###############################################################################
##################   TEMPORAL FILTERS       ###################################
###############################################################################
from scipy.signal import butter, filtfilt
    

class Butterworth_filter(BaseProcess):
    """ butterworth_filter(filter_order, low, high, keepSourceWindow=False)
    This filters a stack in time.
    
    Parameters:
        | filter_order (int) -- The order of the butterworth filter (higher->steeper).
        | low (float) -- The low frequency cutoff.  Must be between 0 and 1 and must be below high.
        | high (float) -- The high frequency cutoff.  Must be between 0 and 1 and must be above low.
    Returns:
        newWindow
    """
    def __init__(self):
        super().__init__()

    def gui(self):
        self.gui_reset()
        filter_order=QtWidgets.QSpinBox()
        filter_order.setRange(1,10)
        low=SliderLabel(5)
        low.setRange(0,1)
        low.setValue(0)
        high=SliderLabel(5)
        high.setRange(0,1)
        high.setValue(1)
        low.valueChanged.connect(lambda low: high.setMinimum(low))
        high.valueChanged.connect(lambda high: low.setMaximum(high))
        preview=CheckBox()
        preview.setChecked(True)
        self.items.append({'name':'filter_order','string':'Filter Order','object':filter_order})
        self.items.append({'name':'low','string':'Low Cutoff Frequency','object':low})
        self.items.append({'name':'high','string':'High Cutoff Frequency','object':high})
        self.items.append({'name':'preview','string':'Preview','object':preview})        
        super().gui()
        self.roi=g.currentWindow.currentROI
        if self.roi is not None:
            self.ui.rejected.connect(self.roi.redraw_trace)
            self.ui.accepted.connect(self.roi.redraw_trace)
        if self.roi is None or g.currentTrace is None:
            preview.setChecked(False)
            preview.setEnabled(False)
        
    def __call__(self,filter_order,low,high,keepSourceWindow=False):
        if low==0 and high==1:
            return
        self.start(keepSourceWindow)
        if self.tif.ndim != 3:
            g.alert("Butterworth filter only works on 3-dimensional movies.")
            return
        if g.settings['multiprocessing']:
            self.newtif=butterworth_filter_multi(filter_order,low,high,g.currentWindow.image)
        else:
            self.newtif=np.zeros(self.tif.shape,dtype=g.settings.d['internal_data_type'])
            mt,mx,my=self.tif.shape
            b,a,padlen=self.makeButterFilter(filter_order,low,high)
            for i in np.arange(mx):
                for j in np.arange(my):
                    self.newtif[:, i, j]=filtfilt(b,a, self.tif[:, i, j], padlen=padlen)
        self.newname=self.oldname+' - Butter Filtered'
        return self.end()
        
    def preview(self):
        if g.currentTrace is not None:
            filter_order=self.getValue('filter_order')
            low=self.getValue('low')
            high=self.getValue('high')
            preview=self.getValue('preview')
            if self.roi is not None:
                if preview:
                    if (low==0 and high==1) or (low==0 and high==0):
                        self.roi.onRegionChangeFinished() #redraw roi without filter
                    else:
                        b,a,padlen=self.makeButterFilter(filter_order,low,high)
                        trace=self.roi.getTrace()
                        trace=filtfilt(b,a, trace, padlen=padlen)
                        roi_index=g.currentTrace.get_roi_index(self.roi)
                        g.currentTrace.update_trace_full(roi_index,trace) #update_trace_partial may speed it up
                else:
                    self.roi.redraw_trace()
    def makeButterFilter(self,filter_order,low,high):
        padlen=0
        if high==1: 
            if low==0: #if there is no temporal filter at all,
                return None,None,None
            else: #if only high pass temporal filter
                [b,a]= butter(filter_order,low,btype='highpass')
                padlen=3
        else:
            if low==0:
                [b,a]= butter(filter_order,high,btype='lowpass')
            else:
                [b,a]=butter(filter_order,[low,high], btype='bandpass')
            padlen=6
        return b,a,padlen
        
butterworth_filter=Butterworth_filter()

        
def butterworth_filter_multi(filter_order,low,high,tif):
    nThreads= g.settings['nCores']
    mt,mx,my=tif.shape
    block_ends=np.linspace(0,mx,nThreads+1).astype(np.int)
    data=[tif[:, block_ends[i]:block_ends[i+1],:] for i in np.arange(nThreads)] #split up data along x axis. each thread will get one.
    args=(filter_order,low,high)
    progress = ProgressBar(butterworth_filter_multi_inner, data, args, nThreads, msg='Performing Butterworth Filter')
    if progress.results is None or any(r is None for r in progress.results):
        result=None
    else:
        result=np.concatenate(progress.results,axis=1).astype(g.settings['internal_data_type'])
    return result
    

def butterworth_filter_multi_inner(q_results, q_progress, q_status, child_conn, args):
    data=child_conn.recv()
    status=q_status.get(True) #this blocks the process from running until all processes are launched
    if status=='Stop':
        q_results.put(None)
    
    def makeButterFilter(filter_order,low,high):
        padlen=0
        if high==1: 
            if low==0: #if there is no temporal filter at all,
                return None,None,None
            else: #if only high pass temporal filter
                [b,a]= butter(filter_order,low,btype='highpass')
                padlen=3
        else:
            if low==0:
                [b,a]= butter(filter_order,high,btype='lowpass')
            else:
                [b,a]=butter(filter_order,[low,high], btype='bandpass')
            padlen=6
        return b,a,padlen
        
    filter_order,low,high = args
    b,a,padlen=makeButterFilter(filter_order,low,high)
    mt,mx,my=data.shape
    result=np.zeros(data.shape,g.settings['internal_data_type'])
    nPixels=mx*my
    pixel=0
    percent=0
    for x in np.arange(mx):
        for y in np.arange(my):
            if not q_status.empty():
                stop=q_status.get(False)
                q_results.put(None)
                return
            pixel+=1
            if percent<int(100*pixel/nPixels):
                percent=int(100*pixel/nPixels)
                q_progress.put(percent)
            result[:, x, y]=filtfilt(b,a, data[:, x, y], padlen=padlen)
    q_results.put(result)

from scipy.ndimage.filters import convolve
class Mean_filter(BaseProcess):
    """ mean_filter(nFrames, keepSourceWindow=False)
    This filters a stack in time.
    
    Parameters:
        | nFrames (int) -- Number of frames to average
    Returns:
        newWindow
    """
    def __init__(self):
        super().__init__()
    def gui(self):
        self.gui_reset()
        nFrames=SliderLabel(0)
        nFrames.setRange(1,100)
        preview=CheckBox()
        preview.setChecked(True)
        self.items.append({'name':'nFrames','string':'nFrames','object':nFrames})
        self.items.append({'name':'preview','string':'Preview','object':preview})        
        super().gui()
        self.roi=g.currentWindow.currentROI
        if self.roi is not None:
            self.ui.rejected.connect(self.roi.redraw_trace)
            self.ui.accepted.connect(self.roi.redraw_trace)
        else:
            preview.setChecked(False)
            preview.setEnabled(False)
            
    def __call__(self,nFrames,keepSourceWindow=False):
        self.start(keepSourceWindow)
        if self.tif.dtype == np.float16:
            g.alert("Mean Filter does not support float16 type arrays")
            return
        if self.tif.ndim != 3:
            g.alert("Mean Filter only supports 3-dimensional movies.")
            return
        self.newtif=convolve(self.tif,weights=np.full((nFrames,1,1),1.0/nFrames))        
        self.newname=self.oldname+' - Mean Filtered'
        return self.end()
    def preview(self):
        nFrames=self.getValue('nFrames')
        preview=self.getValue('preview')
        if self.roi is not None:
            if preview:
                if nFrames==1:
                    self.roi.redraw_trace() #redraw roi without filter
                else:
                    trace=self.roi.getTrace()
                    trace=convolve(trace,weights=np.full((nFrames),1.0/nFrames))        
                    roi_index=g.currentTrace.get_roi_index(self.roi)
                    g.currentTrace.update_trace_full(roi_index,trace) #update_trace_partial may speed it up
            else:
                self.roi.redraw_trace()
mean_filter=Mean_filter()


from scipy.signal import medfilt
class Median_filter(BaseProcess):
    """ median_filter(nFrames, keepSourceWindow=False)
    This filters a stack in time.
    
    Parameters:
        | nFrames (int) -- Number of frames to average.  This must be an odd number
    Returns:
        newWindow
    """
    def __init__(self):
        super().__init__()
    def gui(self):
        self.gui_reset()
        nFrames=SliderLabelOdd()
        nFrames.setRange(1,100)
        preview=CheckBox()
        preview.setChecked(True)
        self.items.append({'name':'nFrames','string':'nFrames','object':nFrames})
        self.items.append({'name':'preview','string':'Preview','object':preview})        
        super().gui()
        self.roi=g.currentWindow.currentROI
        if self.roi is not None:
            self.ui.rejected.connect(self.roi.redraw_trace)
            self.ui.accepted.connect(self.roi.redraw_trace)
        else:
            preview.setChecked(False)
            preview.setEnabled(False)
            
    def __call__(self, nFrames, keepSourceWindow=False):
        if nFrames%2 == 0: #if value is even:
            g.alert('median_filter only takes odd numbers.  Operation cancelled')
            return None
        self.start(keepSourceWindow)
        if self.tif.ndim < 3:
            g.alert("Median filter requires at least 3 dimensions. %d < 3" % self.tif.ndim)
            return
        mx=self.tif.shape[2]
        my=self.tif.shape[1]
        self.newtif=np.zeros(self.tif.shape)
        for i in np.arange(my):
            for j in np.arange(mx):
                self.newtif[:, i, j]=medfilt(self.tif[:, i, j], kernel_size=nFrames)      
        self.newname=self.oldname+' - Median Filtered'
        return self.end()
    def preview(self):
        nFrames=self.getValue('nFrames')
        preview=self.getValue('preview')
        if self.roi is not None:
            if preview:
                print(nFrames)
                if nFrames==1:
                    self.roi.redraw_trace() #redraw roi without filter
                elif nFrames%2==0: #if value is even
                    return None
                else:
                    trace=self.roi.getTrace()
                    trace=medfilt(trace,kernel_size=nFrames)
                    roi_index=g.currentTrace.get_roi_index(self.roi)
                    g.currentTrace.update_trace_full(roi_index,trace) #update_trace_partial may speed it up
            else:
                self.roi.redraw_trace()
                
median_filter=Median_filter()




from scipy.fftpack import fft, ifft, fftfreq
class Fourier_filter(BaseProcess):
    """ fourier_filter(frame_rate, low, high, loglogPreview, keepSourceWindow=False)
    I'm going to eventually plot the trace in the frequency domain inside this box so you can see where the power is.

    Parameters:
        | frame_rate (int) -- Frame Rate in Hz
        | low (float) -- Low cutoff frequency for the fourier filter
        | high (float) -- High cutoff frequency for fourier filter
        | loglogPreview (boolean) -- whether or not to plot frequency spectrum on log log axes
    """
    def __init__(self):
        super().__init__()
    def gui(self):
        self.gui_reset()
        frame_rate=QtWidgets.QDoubleSpinBox()
        frame_rate.setRange(.01,1000)
        frame_rate.setValue(200)
        low=SliderLabel(5)
        low.setRange(0,1)
        low.setValue(0)
        high=SliderLabel(5)
        high.setRange(0,1)
        high.setValue(1)
        frame_rate.valueChanged.connect(self.frame_rate_changed)
        low.valueChanged.connect(lambda low: high.setMinimum(low))
        high.valueChanged.connect(lambda high: low.setMaximum(high))
        preview=CheckBox()
        preview.setChecked(True)
        loglogPreview=CheckBox()
        self.items.append({'name':'frame_rate','string':'Frame Rate (Hz)','object':frame_rate})
        self.items.append({'name':'low','string':'Low Cutoff Frequency','object':low})
        self.items.append({'name':'high','string':'High Cutoff Frequency','object':high})
        self.items.append({'name':'loglogPreview','string':'Plot frequency spectrum on log log axes','object':loglogPreview})    
        self.items.append({'name':'preview','string':'Preview','object':preview})        
        super().gui()
        self.roi=g.currentWindow.currentROI
        if self.roi is not None:
            self.ui.rejected.connect(self.roi.redraw_trace)
            self.ui.accepted.connect(self.roi.redraw_trace)
        else:
            preview.setChecked(False)
            preview.setEnabled(False)
            loglogPreview.setEnabled(False) 
    def __call__(self, frame_rate, low, high, loglogPreview, keepSourceWindow=False):
        self.start(keepSourceWindow)
        if self.tif.dtype == np.float16:
            g.alert("Fourier transform does not support float16 movies.")
            return
        if self.tif.ndim != 3 or self.tif.shape[2] == 3:
            g.alert('Fourier transform requires 3 dimensional movies.')
            return
        if low==0 and high==frame_rate/2.0:
            return
        mt,mx,my=self.tif.shape
        W = fftfreq(mt, d=1.0/frame_rate)
        filt=np.ones((mt))
        filt[(np.abs(W)<low)] = 0
        filt[(np.abs(W)>high)] = 0
        self.newtif=np.zeros(self.tif.shape)
        for i in np.arange(my):
            for j in np.arange(mx):
                f_signal = fft(self.tif[:, i, j])
                f_signal*=filt
                self.newtif[:, i, j]=np.real(ifft(f_signal))
        self.newname=self.oldname+' - Fourier Filtered'
        return self.end()
    def preview(self):
        frame_rate=self.getValue('frame_rate')
        low=self.getValue('low')
        high=self.getValue('high')
        loglogPreview=self.getValue('loglogPreview')
        preview=self.getValue('preview')
        if self.roi is not None:
            if preview:
                if (low==0 and high==frame_rate/2.0) or (low==0 and high==0):
                    self.roi.redraw_trace() #redraw roi without filter
                else:
                    trace=self.roi.getTrace()
                    W = fftfreq(len(trace), d=1.0/frame_rate)
                    f_signal = fft(trace)
                    f_signal[(np.abs(W)<low)] = 0
                    f_signal[(np.abs(W)>high)] = 0
                    cut_signal=np.real(ifft(f_signal))
                    roi_index=g.currentTrace.get_roi_index(self.roi)
                    g.currentTrace.update_trace_full(roi_index,cut_signal) #update_trace_partial may speed it up
            else:
                self.roi.redraw_trace()
                
    def frame_rate_changed(self):
        low=[item for item in self.items if item['name']=='low'][0]['object']
        high=[item for item in self.items if item['name']=='high'][0]['object']
        frame_rate=[item for item in self.items if item['name']=='frame_rate'][0]['object']
        f=frame_rate.value()
        low.setRange(0.0,f/2.0)
        high.setRange(0.0,f/2.0)
        low.setValue(0)
        high.setValue(f/2.0)
""" This is demo code for plotting in the frequency domain, something I hoepfully will get around to implementing

from numpy import sin, linspace, pi
from pylab import plot, show, title, xlabel, ylabel, subplot
from scipy import fft, arange

def plotSpectrum(y,Fs):
    n = len(y) # length of the signal
    k = arange(n)
    W = fftfreq(len(y), d=1/Fs)

    Y = fft(y) # fft computing and normalization
    f_signal[(np.abs(W)>10)] = 0
    plot(abs(f_signal)[0:N/2])
    cut_signal=np.real(ifft(f_signal))
    p=plot(trace)
    p.plot(cut_signal,pen=pg.mkPen('r'))
    
    plot(frq,abs(f_signal),'r') # plotting the spectrum
    xlabel('Freq (Hz)')
    ylabel('|Y(freq)|')"""
        
fourier_filter=Fourier_filter()



class Difference_filter(BaseProcess):
    """ difference_filter(keepSourceWindow=False)
    subtracts each frame from the preceeding frame
    
    
    Parameters:
        | None
    Returns:
        newWindow
    """
    def __init__(self):
        super().__init__()
    def gui(self):
        self.gui_reset()
        if super().gui()==False:
            return False
    def __call__(self,keepSourceWindow=False):
        self.start(keepSourceWindow)
        self.newtif=np.zeros(self.tif.shape)
        for i in np.arange(1,len(self.newtif)):
            self.newtif[i]=self.tif[i]-self.tif[i-1]
        self.newname=self.oldname+' - Difference Filtered'
        return self.end()
difference_filter=Difference_filter()

    
class Boxcar_differential_filter(BaseProcess):
    """ boxcar_differential_filter(minNframes, maxNframes, keepSourceWindow=False)
    Applies a Boxcar differential filter by comparing each frameat index I to the frames in range [I+minNframes, I+maxNframes]

    Parameters:
        | minNframes (int) -- The starting point of your boxcar window.
        | maxNframes (int) -- The ending point of your boxcar window.
    Returns:
        newWindow
    """
    def __init__(self):
        super().__init__()
    def gui(self):
        self.gui_reset()
        minNframes=SliderLabel(0)
        minNframes.setRange(1,100)
        maxNframes=SliderLabel(0)
        maxNframes.setRange(2,101)
        minNframes.valueChanged.connect(lambda minn: maxNframes.setMinimum(minn+1))
        maxNframes.valueChanged.connect(lambda maxx: minNframes.setMaximum(maxx-1))
        preview=CheckBox()
        preview.setChecked(True)
        self.items.append({'name':'minNframes','string':'Minimum Number of Frames','object':minNframes})
        self.items.append({'name':'maxNframes','string':'Maximum Number of Frames','object':maxNframes})
        self.items.append({'name':'preview','string':'Preview','object':preview})  
        if super().gui()==False:
            return False
        self.roi=g.currentWindow.currentROI
        if self.roi is not None:
            self.ui.rejected.connect(self.roi.redraw_trace)
            self.ui.accepted.connect(self.roi.redraw_trace)
        else:
            preview.setChecked(False)
            preview.setEnabled(False)
    def __call__(self,minNframes,maxNframes,keepSourceWindow=False):
        self.start(keepSourceWindow)
        self.newtif=np.zeros(self.tif.shape)
        for i in np.arange(maxNframes,len(self.newtif)):
            self.newtif[i]=self.tif[i]-np.min(self.tif[i-maxNframes:i-minNframes],0)
        self.newname=self.oldname+' - Boxcar Differential Filtered'
        return self.end()
    def preview(self):
        minNframes=self.getValue('minNframes')
        maxNframes=self.getValue('maxNframes')
        preview=self.getValue('preview')
        if self.roi is not None:
            if preview:
                self.tif=self.roi.window.image
                (mt,mx,my)=self.tif.shape
                cnt=np.array([np.array([np.array([p[1],p[0]])]) for p in self.roi.pts ])
                mask=np.zeros(self.tif[0,:,:].shape,np.uint8)
                cv2.drawContours(mask,[cnt],0,255,-1)
                mask=mask.reshape(mx*my).astype(np.bool)
                tif=self.tif.reshape((mt,mx*my))
                tif=tif[:,mask]
                newtrace=np.zeros(mt)
                for i in np.arange(maxNframes,mt):
                    newtrace[i]=np.mean(tif[i]-np.min(tif[i-maxNframes:i-minNframes],0))
                roi_index=g.currentTrace.get_roi_index(self.roi)
                g.currentTrace.update_trace_full(roi_index,newtrace) #update_trace_partial may speed it up
            else:
                self.roi.redraw_trace()
boxcar_differential_filter=Boxcar_differential_filter()
    
    
from scipy import signal
class Wavelet_filter(BaseProcess):
    ''' wavelet_filter(low, high, keepSourceWindow=False)
    ***Warning!! This function is extremely slow.***
    
    Parameters:
        | low (int) -- The starting point of your boxcar window.
        | high (int) -- The ending point of your boxcar window.
    Returns:
        newWindow
    '''
    def __init__(self):
        super().__init__()
    def gui(self):
        self.gui_reset()
        low=SliderLabel(0)
        low.setRange(1,50)
        high=SliderLabel(0)
        high.setRange(2,50)
        low.valueChanged.connect(lambda minn: high.setMinimum(minn+1))
        high.valueChanged.connect(lambda maxx: low.setMaximum(maxx-1))
        preview=CheckBox()
        preview.setChecked(True)
        self.items.append({'name':'low','string':'Low Frequency Threshold','object':low})
        self.items.append({'name':'high','string':'High Frequency Threshold','object':high})
        self.items.append({'name':'preview','string':'Preview','object':preview})  
        super().gui()
        self.roi=g.currentWindow.currentROI
        if self.roi is not None:
            self.ui.rejected.connect(self.roi.redraw_trace)
            self.ui.accepted.connect(self.roi.redraw_trace)
        else:
            preview.setChecked(False)
            preview.setEnabled(False)
    def __call__(self,low,high,keepSourceWindow=False):
        self.start(keepSourceWindow)
        if self.tif.ndim != 3:
            g.alert("Wavelet filter only works on 3 dimensional movies")
            return
        mx=self.tif.shape[2]
        my=self.tif.shape[1]
        self.newtif=np.zeros(self.tif.shape)
        wavelet = signal.ricker
        widths = np.arange(low, high)
        for i in np.arange(my):
            print(i)
            for j in np.arange(mx):
                cwtmatr = signal.cwt(self.tif[:, i, j], wavelet, widths)
                self.newtif[:, i, j]=np.mean(cwtmatr,0)
        self.newname=self.oldname+' - Wavelet Filtered'
        return self.end()
    def preview(self):
        low=self.getValue('low')
        high=self.getValue('high')
        preview=self.getValue('preview')
        if self.roi is not None:
            if preview:
                trace=self.roi.getTrace()
                wavelet = signal.ricker
                widths = np.arange(low, high)
                cwtmatr = signal.cwt(trace, wavelet, widths)
                newtrace=np.mean(cwtmatr,0)
                roi_index=g.currentTrace.get_roi_index(self.roi)
                g.currentTrace.update_trace_full(roi_index,newtrace) #update_trace_partial may speed it up
            else:
                self.roi.redraw_trace()
wavelet_filter=Wavelet_filter()
    
    
    
    
    
    
    
    
    
    
class Bilateral_filter(BaseProcess):
    ''' bilateral_filter( keepSourceWindow=False)
    
    Parameters:
        | soft (bool)  --     True for guassian, False for hard filter
        | beta (float) --     beta of kernel
        | width (float) --    width of kernel
        | stoptol (float) --  tolerance for convergence
        | maxiter (int)  --   maximum number of iterations
    Returns:
        newWindow
    '''
    def __init__(self):
        super().__init__()
    def gui(self):
        self.gui_reset()
        
        soft=CheckBox()
        soft.setChecked(True)
        beta=SliderLabel(2)
        beta.setRange(1,500)
        beta.setValue(200)
        width=SliderLabel(2)
        width.setRange(1,50)
        width.setValue(8)
        stoptol=SliderLabel(4)
        stoptol.setRange(0,.02)
        stoptol.setValue(.001)
        maxiter=SliderLabel(0)
        maxiter.setRange(1,100)
        maxiter.setValue(10)
        preview=CheckBox()
        preview.setChecked(True)
        self.items.append({'name':'soft','string':'soft','object':soft})  
        self.items.append({'name':'beta','string':'beta','object':beta})  
        self.items.append({'name':'width','string':'width','object':width})  
        self.items.append({'name':'stoptol','string':'stop tolerance','object':stoptol})  
        self.items.append({'name':'maxiter','string':'Maximum Iterations','object':maxiter})  
        self.items.append({'name':'preview','string':'Preview','object':preview})  
        super().gui()
        self.roi=g.currentWindow.currentROI
        if self.roi is not None:
            self.ui.rejected.connect(self.roi.redraw_trace)
            self.ui.accepted.connect(self.roi.redraw_trace)
        else:
            preview.setChecked(False)
            preview.setEnabled(False)
        
    def __call__(self,soft, beta, width, stoptol, maxiter, keepSourceWindow=False):
        
        self.start(keepSourceWindow)
        if self.tif.ndim != 3:
            g.alert("Bilateral filter requires 3-dimensional image.")
            return
        if g.settings['multiprocessing']:
            self.newtif=bilateral_filter_multi(soft,beta,width,stoptol,maxiter,g.currentWindow.image)
        else:
            self.newtif=np.zeros(self.tif.shape)
            mt,mx,my=self.tif.shape
            for i in np.arange(mx):
                for j in np.arange(my):
                    self.newtif[:, i, j]=bilateral_smooth(soft,beta,width,stoptol,maxiter,self.tif[:,i,j])
        self.newname=self.oldname+' - Bilateral Filtered'
        return self.end()

    def preview(self):
        soft=self.getValue('soft')
        beta=self.getValue('beta')
        width=self.getValue('width')
        stoptol=self.getValue('stoptol')
        maxiter=self.getValue('maxiter')
        preview=self.getValue('preview')
        
        if self.roi is not None:
            if preview:
                trace=self.roi.getTrace()
                trace=bilateral_smooth(soft,beta,width,stoptol,maxiter,trace)
                roi_index=g.currentTrace.get_roi_index(self.roi)
                g.currentTrace.update_trace_full(roi_index,trace) #update_trace_partial may speed it up
            else:
                self.roi.redraw_trace()
        

def bilateral_filter_multi(soft,beta,width,stoptol,maxiter,tif):
    nThreads= g.settings['nCores']
    mt,mx,my=tif.shape
    block_ends=np.linspace(0,mx,nThreads+1).astype(np.int)
    data=[tif[:, block_ends[i]:block_ends[i+1],:] for i in np.arange(nThreads)] #split up data along x axis. each thread will get one.
    args=(soft,beta,width,stoptol,maxiter)
    progress = ProgressBar(bilateral_filter_inner, data, args, nThreads, msg='Performing Bilateral Filter')
    if progress.results is None or any(r is None for r in progress.results):
        result=None
    else:
        result=np.concatenate(progress.results,axis=1)
    return result
    
    
def bilateral_filter_inner(q_results, q_progress, q_status, child_conn, args):
    data=child_conn.recv() # unfortunately this step takes a long time
    percent=0  # This is the variable we send back which displays our progress
    status=q_status.get(True) #this blocks the process from running until all processes are launched
    if status=='Stop':
        q_results.put(None) # if the user presses stop, return None
    
    
    # Here is the meat of the inner_func.
    soft,beta,width,stoptol,maxiter=args #unpack all the variables inside the args tuple
    result=np.zeros(data.shape)
    tt,xx,yy=data.shape
    for x in np.arange(xx):
        for y in np.arange(yy):
            result[:,x,y]=bilateral_smooth(soft,beta,width,stoptol,maxiter,data[:,x,y])
            if not q_status.empty(): #check if the stop button has been pressed
                stop=q_status.get(False)
                q_results.put(None)
                return
        if percent<int(100*x/xx):
            percent=int(100*x/xx)
            q_progress.put(percent)
                    
    # finally, when we've finished with our calculation, we send back the result
    q_results.put(result)
    
def bilateral_smooth(soft,beta,width,stoptol,maxiter,y):
    display=False       # 1 to report iteration values
    
    y=np.array(y[:])
    N=np.size(y,0)
    w=np.zeros((N,N))
    j=np.arange(0,N)
    
    #construct initial bilateral kernel
    for i in np.arange(0,N):
        w[i,np.arange(0,N)]=(abs(i-j) <= width)
    
    #initial guess from input signal
    xold=np.copy(y)
    
    #new matrix for storing distances
    d=np.zeros((N,N))
    
    #fig1 = plt.plot(y)
    
    if (display):
        if (soft):
            print('Soft kernel')
        else:
            print('Hard kernel')
        print('Kernel parameters beta= %d, W= %d' % (beta,width))
        print('Iter# Change')
    
    #start iteration
    iterate=1
    gap=np.inf
    
    while (iterate < maxiter):
    
        if (display):
            print('%d %f'% (iterate,gap))
    
        # calculate paiwise distances for all points
        for i in np.arange(0,N):
            d[:,i] = (0.5 * (xold - xold[i]) ** 2)
        
        #create kernel
        if (soft):
            W=np.multiply(np.exp(-beta*d),w)
    
        else:
            W=np.multiply((d <= beta ** 2),w)
        
        #apply kernel to get weighted mean shift   
        xnew1=np.sum(np.multiply(np.transpose(W),xold), axis=1)
        xnew2=np.sum(W, axis=1)
        xnew=np.divide(xnew1,xnew2)
       
        #plt.plot(xnew)   
        
        #check for convergence
        gap=np.sum(np.square(xold-xnew))
    
        if (gap < stoptol):
            if (display):
                print('Converged in %d iterations' % iterate)
            break
    
        xold=np.copy(xnew)
        iterate+=1
    return xold
    
bilateral_filter=Bilateral_filter()






#from scipy import signal
#data=g.currentTrace.rois[0]['roi'].getTrace()
#wavelet = signal.ricker
#widths = np.arange(1, 200)
#cwtmatr = signal.cwt(data, wavelet, widths)
#import pyqtgraph as pg
#i=pg.image(cwtmatr.T)
#i.view.setAspectLocked(lock=True, ratio=cwtmatr.shape[0]/cwtmatr.shape[1]*20)