# -*- coding: utf-8 -*-
"""
Created on Tue Jul 01 11:28:38 2014

@author: Kyle Ellefsen
"""
from PyQt4 import uic
from PyQt4.QtCore import * # Qt is Nokias GUI rendering code written in C++.  PyQt4 is a library in python which binds to Qt
from PyQt4.QtGui import *
from PyQt4.QtCore import pyqtSignal as Signal
import sys, os
if sys.version_info.major==2:
	import cPickle as pickle # pickle serializes python objects so they can be saved persistantly.  It converts a python object into a savable data structure
else:
	import pickle
from os.path import expanduser
import numpy as np
from pyqtgraph.dockarea import *
from window import Window
from trace import TraceFig
from window3d import Window3D

def mainguiClose(event):
	global m
	windows=m.windows[:]
	for window in windows:
		window.close()
	if m.scriptEditor is not None:
		m.scriptEditor.close()
	event.accept() # let the window close

class SetCurrentWindowSignal(QWidget):
	sig=Signal()
	def __init__(self,parent):
		QWidget.__init__(self,parent)
		self.hide()

class Settings:
	def __init__(self, name):
		self.config_file=os.path.join(expanduser("~"),'.Configs','%s.p' % name)
		try:
			self.d=pickle.load(open(self.config_file, "rb" ))
		except (IOError, ValueError):
			self.d=dict()
			self.d['filename']=None #this is the name of the most recently opened file
			self.d['data_type']=np.float64 #this is the data type used to save an image.  All image data are handled internally as np.float64 irrespective of this setting
			self.d['internal_data_type']=np.float64
		self.d['mousemode']='rectangle'
		self.d['multipleTraceWindows'] = False
			
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
	def setMultipleTraceWindows(self, f):
		self.d['multipleTraceWindows'] = f

def init(filename, docks=False):
	global m
	m=uic.loadUi(filename)
	m.windowSelectedSignal=SetCurrentWindowSignal(m)
	m.settings = Settings("Flika")
	
	m.windows = []
	m.traceWindows = []
	m.currentWindow = None
	m.currentTrace = None

	m.clipboard = None
	m.scriptEditor = None
	m.setAcceptDrops(True)
	m.closeEvent = mainguiClose
	
	if docks:
		m.dockarea = DockArea()
		m.mainDock = Dock(name = 'Options', widget = m.centralwidget)
		m.dockarea.addDock(m.mainDock)
		m.setCentralWidget(m.dockarea)
		Window.onCreate = dockCreated
		TraceFig.onCreate = dockCreated
		Window3D.onCreate = dockCreated

def dockCreated(widg):
	global m
	widg.dock = Dock(name = widg.name, widget=widg, closable=True)
	m.dockarea.addDock(widg.dock, 'right', m.mainDock)
	widg.closeEvent = lambda e: widgetClosed(widg, e)

def widgetClosed(widg, e):
	widg.dock.close()
	widg.__class__.closeEvent(widg, e)
