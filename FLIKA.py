# -*- coding: utf-8 -*-
"""
Created on Thu Jun 26 14:17:38 2014
updated 2015.01.27
@author: Kyle Ellefsen
"""
from __future__ import (absolute_import, division,print_function, unicode_literals)
from future.builtins import (bytes, dict, int, list, object, range, str, ascii, chr, hex, input, next, oct, open, pow, round, super, filter, map, zip)
import time
tic=time.time()
import os, sys
sys.path.insert(0, "C:/Users/Kyle Ellefsen/Documents/GitHub/pyqtgraph")
from os.path import expanduser
import numpy as np
from PyQt4.QtCore import * # Qt is Nokias GUI rendering code written in C++.  PyQt4 is a library in python which binds to Qt
from PyQt4.QtGui import *
from PyQt4.QtCore import pyqtSignal as Signal
from pyqtgraph import plot, show
from scripts import getScriptList
from roi import load_roi_gui, load_roi
import global_vars as g
from window import Window
import cPickle as pickle # pickle serializes python objects so they can be saved persistantly.  It converts a python object into a savable data structure
from process.file_ import open_gui, save_as_gui, open_file, load_metadata, close, save_file, save_movie_gui, save_movie, change_internal_data_type, change_internal_data_type_gui, save_points_gui
from process.stacks import deinterleave, slicekeeper, zproject, image_calculator, pixel_binning, frame_binning
from process.math_ import multiply, subtract, power, ratio, absolute_value, subtract_trace
from process.filters import gaussian_blur, butterworth_filter,boxcar_differential_filter, wavelet_filter, difference_filter, fourier_filter
from process.binary import threshold, adaptive_threshold, canny_edge_detector, remove_small_blobs, logically_combine, binary_dilation, binary_erosion
from process.roi import set_value
from analyze.measure import measure
from analyze.puffs.frame_by_frame_origin import frame_by_frame_origin
from analyze.puffs.average_origin import average_origin
from analyze.puffs.threshold_cluster import threshold_cluster

from process.overlay import time_stamp,background

from analyze.behavior.rodentTracker import launchRodentTracker

os.chdir(os.path.split(os.path.realpath(__file__))[0])

class Settings:
    def __init__(self):
        self.config_file=os.path.join(expanduser("~"),'.FLIKA','config.p')
        try:
            self.d=pickle.load(open(self.config_file, "rb" ))
        except IOError:
            self.d=dict()
            self.d['filename']=None #this is the name of the most recently opened file
            self.d['data_type']=np.float64 #this is the data type used to save an image.  All image data are handled internally as np.float64 irrespective of this setting
            self.d['internal_data_type']=np.float64
        self.d['show_windows']=True #set this to false when you want to supress the display of a window.  It saves a small amount of time. Be careful: the windows are still there taking up memory in the background.
        self.d['mousemode']='rectangle'
            
    def __getitem__(self, item):
        try:
            self.d[item]
        except KeyError:
            if item=='internal_data_type':
                self.d[item]=np.float64
        return self.d[item]
    def __setitem__(self,key,item):
        self.d[key]=item
        self.save()
    def save(self):
        '''save to a config file.'''
        if not os.path.exists(os.path.dirname(self.config_file)):
            os.makedirs(os.path.dirname(self.config_file))
        pickle.dump(self.d, open( self.config_file, "wb" ))
    def setmousemode(self,mode):
        self.d['mousemode']=mode
        

    
class SetCurrentWindowSignal(QWidget):
    sig=Signal()
    def __init__(self,parent):
        QWidget.__init__(self,parent)
        self.hide()

def initializeMainGui():
    g.init()
    g.m.setCurrentWindowSignal=SetCurrentWindowSignal(g.m)
    g.m.settings=Settings()
    g.m.windows=list()
    g.m.currentWindow=None
    g.m.tracefig=None
    g.m.clipboard=None
    g.m.scriptEditor=None
    g.m.setGeometry(QRect(15, 33, 326, 80))
    g.m.actionOpen.triggered.connect(open_gui)    
    g.m.actionSaveAs.triggered.connect(save_as_gui)
    g.m.actionSave_Points.triggered.connect(save_points_gui)
    g.m.actionSave_Movie.triggered.connect(save_movie_gui)
    g.m.actionChange_Internal_Data_type.triggered.connect(change_internal_data_type_gui)
    g.m.actionDeinterleave.triggered.connect(deinterleave.gui)
    g.m.actionZ_Project.triggered.connect(zproject.gui)
    g.m.actionPixel_Binning.triggered.connect(pixel_binning.gui)
    g.m.actionFrame_Binning.triggered.connect(frame_binning.gui)
    g.m.actionSlice_Keeper.triggered.connect(slicekeeper.gui)
    g.m.actionMultiply.triggered.connect(multiply.gui)
    g.m.actionSubtract.triggered.connect(subtract.gui)
    g.m.actionPower.triggered.connect(power.gui)
    g.m.actionGaussian_Blur.triggered.connect(gaussian_blur.gui)
    g.m.actionButterworth_Filter.triggered.connect(butterworth_filter.gui)
    g.m.actionFourier_Filter.triggered.connect(fourier_filter.gui)
    g.m.actionDifference_Filter.triggered.connect(difference_filter.gui)
    g.m.actionBoxcar_Differential.triggered.connect(boxcar_differential_filter.gui)
    g.m.actionWavelet_Filter.triggered.connect(wavelet_filter.gui)
    g.m.actionRatio.triggered.connect(ratio.gui)
    g.m.actionSubtract_Trace.triggered.connect(subtract_trace.gui)
    g.m.actionAbsolute_Value.triggered.connect(absolute_value.gui)
    g.m.actionThreshold.triggered.connect(threshold.gui)
    g.m.actionAdaptive_Threshold.triggered.connect(adaptive_threshold.gui)
    g.m.actionCanny_Edge_Detector.triggered.connect(canny_edge_detector.gui)
    g.m.actionLogically_Combine.triggered.connect(logically_combine.gui)
    g.m.actionRemove_Small_Blobs.triggered.connect(remove_small_blobs.gui)
    g.m.actionBinary_Erosion.triggered.connect(binary_erosion.gui)
    g.m.actionBinary_Dilation.triggered.connect(binary_dilation.gui)
    g.m.actionSet_value.triggered.connect(set_value.gui)
    g.m.actionImage_Calculator.triggered.connect(image_calculator.gui)    
    g.m.actionTime_Stamp.triggered.connect(time_stamp.gui)
    g.m.actionBackground.triggered.connect(background.gui)
    
    g.m.actionMeasure.triggered.connect(measure.gui)    
    g.m.actionFrame_by_frame_origin.triggered.connect(frame_by_frame_origin.gui)
    g.m.actionAverage_origin.triggered.connect(average_origin.gui)
    g.m.actionThreshold_cluster.triggered.connect(threshold_cluster.gui)
    g.m.actionRodent_Tracker.triggered.connect(launchRodentTracker)
    g.m.freehand.clicked.connect(lambda: g.m.settings.setmousemode('freehand'))
    g.m.line.clicked.connect(lambda: g.m.settings.setmousemode('line'))
    g.m.rectangle.clicked.connect(lambda: g.m.settings.setmousemode('rectangle'))
    g.m.point.clicked.connect(lambda: g.m.settings.setmousemode('point'))
    g.m.menuScripts.aboutToShow.connect(getScriptList)
    url='file:///'+os.path.join(os.getcwd(),'docs','_build','html','index.html')
    g.m.actionDocs.triggered.connect(lambda: QDesktopServices.openUrl(QUrl(url)))
    g.m.actionLoad_ROI_File.triggered.connect(load_roi_gui)
    g.m.show()
    g.m.setAcceptDrops(True)
    g.m.closeEvent=mainguiClose
    g.m.installEventFilter(mainWindowEventEater)
    
class MainWindowEventEater(QObject):
    def __init__(self,parent=None):
        QObject.__init__(self,parent)
    def eventFilter(self,obj,event):
        if (event.type()==QEvent.DragEnter):
            if event.mimeData().hasUrls():
                event.accept()   # must accept the dragEnterEvent or else the dropEvent can't occur !!!
            else:
                event.ignore()
        if (event.type() == QEvent.Drop):
            if event.mimeData().hasUrls():   # if file or link is dropped
                url = event.mimeData().urls()[0]   # get first url
                filename=url.toString()
                filename=filename.split('file:///')[1]
                print('filename={}'.format(filename)) 
                open_file(filename)  #This fails on windows symbolic links.  http://stackoverflow.com/questions/15258506/os-path-islink-on-windows-with-python
                event.accept()
            else:
                event.ignore()
        return False # lets the event continue to the edit
mainWindowEventEater=MainWindowEventEater()


    


def mainguiClose(event):
    windows=g.m.windows[:]
    for window in windows:
        window.close()
    if g.m.scriptEditor is not None:
        g.m.scriptEditor.close()
    event.accept() # let the window close
    



if __name__ == '__main__':
    app = QApplication(sys.argv)
    initializeMainGui()
    print("Time to load Flika: {} s".format(time.time()-tic))
    #open_file()
    #data_window=open_file('D:/Desktop/test_data_long.tif')
    #density_window=open_file('D:/Desktop/density_long.tif')
    #threshold_cluster(density_window,data_window,data_window,paddingT_pre=25, paddingT_post=25)
    
    
    #binary_window=open_file('D:/Desktop/test_binary_long.tif')
    #    if g.m.settings['filename'] is not None and os.path.isfile(g.m.settings['filename']):
    #open_file(g.m.settings['filename'])
    #data_window=open_file('D:/Desktop/test1.tif')
    #binary_window=open_file('D:/Desktop/test2.tif')
    #puffAnalyzer=average_origin(binary_window,data_window)
    
    
    
    insideSpyder='SPYDER_SHELL_ID' in os.environ
    if not insideSpyder: #if we are running outside of Spyder
        sys.exit(app.exec_()) #This is required to run outside of Spyder
    
    
    
    
    
    
    
    
    