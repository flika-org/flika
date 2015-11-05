# -*- coding: utf-8 -*-
"""
Created on Sat Jul 19 07:53:38 2014

@author: Kyle Ellefsen
"""

from __future__ import (absolute_import, division,print_function, unicode_literals)
from future.builtins import (bytes, dict, int, list, object, range, str, ascii, chr, hex, input, next, oct, open, pow, round, super, filter, map, zip)

import os.path
import global_vars as g
import numpy as np
from window import Window
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.QtCore import pyqtSignal as Signal
from PyQt4.QtCore import pyqtSlot  as Slot
import pyqtgraph as pg

import inspect

__all__ = []

        
class MissingWindowError(Exception):
    def __init__(self, value):
        self.value = value
        g.m.statusBar().showMessage(value)
    def __str__(self):
        return repr(self.value)
        
class WindowSelector(QWidget):
    """
    This widget is a button with a lab.  Once you click the button, the widget waits for you to click a Window object.  Once you do, it sets self.window to be the window, and it sets the label to be the widget name.
    """
    valueChanged=Signal()
    def __init__(self):
        QWidget.__init__(self)
        self.button=QPushButton('Select Window')
        self.button.setCheckable(True)
        self.label=QLabel('None')
        self.window=None
        self.layout=QHBoxLayout()
        self.layout.addWidget(self.button)
        self.layout.addWidget(self.label)
        self.setLayout(self.layout)
        self.button.clicked.connect(self.buttonclicked)
    def buttonclicked(self):
        if self.button.isChecked() is False:
            g.m.setCurrentWindowSignal.sig.disconnect(self.windowSet)
        else:
            g.m.setCurrentWindowSignal.sig.connect(self.windowSet)
    def windowSet(self):
        g.m.setCurrentWindowSignal.sig.disconnect(self.windowSet)
        self.window=g.m.currentWindow
        self.button.setChecked(False)
        self.label.setText('...'+os.path.split(self.window.name)[-1][-20:])
        self.valueChanged.emit()
    def value(self):
        return self.window
        
class SliderLabel(QWidget):
    changeSignal=Signal(int)
    def __init__(self,decimals=0): #decimals specifies the resolution of the slider.  0 means only integers,  1 means the tens place, etc.
        QWidget.__init__(self)
        self.slider=QSlider(Qt.Horizontal)
        self.decimals=decimals
        if self.decimals<=0:
            self.label=QSpinBox()
        else:
            self.label=QDoubleSpinBox()
            self.label.setDecimals(self.decimals)
        self.layout=QHBoxLayout()
        self.layout.addWidget(self.slider)
        self.layout.addWidget(self.label)
        self.layout.setContentsMargins(0,0,0,0)
        self.setLayout(self.layout)
        self.slider.valueChanged.connect(lambda val: self.updateLabel(val/10**self.decimals))
        self.label.valueChanged.connect(self.updateSlider)
        self.valueChanged=self.label.valueChanged
    @Slot(int, float)
    def updateSlider(self,value):
        self.slider.setValue(int(value*10**self.decimals))
    def updateLabel(self,value):
        self.label.setValue(value)
    def value(self):
        return self.label.value()
    def setRange(self,minn,maxx):
        self.slider.setRange(minn*10**self.decimals,maxx*10**self.decimals)
        self.label.setRange(minn,maxx)
    def setMinimum(self,minn):
        self.slider.setMinimum(minn*10**self.decimals)
        self.label.setMinimum(minn)
    def setMaximum(self,maxx):
        self.slider.setMaximum(maxx*10**self.decimals)
        self.label.setMaximum(maxx)
    def setValue(self,value):
        self.slider.setValue(value*10**self.decimals)
        self.label.setValue(value)
    def setSingleStep(self,value):
        self.label.setSingleStep(value)
        
class CheckBox(QCheckBox):
    ''' I overwrote the QCheckBox class so that every graphical element has the method 'setValue'
    '''
    def __init__(self,parent=None):
        QCheckBox.__init__(self,parent)
    def setValue(self,value):
        self.setChecked(value)
        
class BaseDialog(QDialog):
    changeSignal=Signal()
    closeSignal=Signal()
    def __init__(self,items,title,docstring):
        QDialog.__init__(self)
        self.setWindowTitle(title)
        self.formlayout=QFormLayout()
        self.formlayout.setLabelAlignment(Qt.AlignRight)
        
        self.items=items
        self.connectToChangeSignal()
        for item in self.items:
            self.formlayout.addRow(item['string'],item['object'])
        self.bbox=QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.bbox.accepted.connect(self.accept)
        self.bbox.rejected.connect(self.reject)
        self.formlayout.addWidget(self.bbox)
        
        self.docstring=QLabel(docstring)
        self.docstring.setWordWrap(True)        
        
        self.layout=QVBoxLayout()
        self.layout.addWidget(self.docstring)
        self.layout.addLayout(self.formlayout)
        self.setLayout(self.layout)
        self.changeSignal.connect(self.updateValues)
        self.updateValues()
        
    def connectToChangeSignal(self):
        for item in self.items:
            methods=[method for method in dir(item['object']) if callable(getattr(item['object'], method))]
            if 'valueChanged' in methods:
                item['object'].valueChanged.connect(self.changeSignal)
            elif 'stateChanged' in methods:
                item['object'].stateChanged.connect(self.changeSignal)
            elif 'currentIndexChanged' in methods:
                item['object'].currentIndexChanged.connect(self.changeSignal)
    def updateValues(self): # copy values from gui into the 'item' dictionary
        for item in self.items:
            methods=[method for method in dir(item['object']) if callable(getattr(item['object'], method))]
            if 'value' in methods:
                item['value']=item['object'].value()
            elif 'currentText' in methods:
                item['value']=item['object'].currentText()
            elif 'isChecked' in methods:
                item['value']=item['object'].isChecked()
    def closeEvent(self,ev):
        self.closeSignal.emit()
        
class BaseProcess(object):
    def __init__(self):
        self.__name__=self.__class__.__name__.lower()
        self.items=[]
    def getValue(self,name):
        return [i['value'] for i in self.items if i['name']==name][0]
    def start(self,keepSourceWindow):
        frame = inspect.getouterframes(inspect.currentframe())[1][0]
        args, _, _, values = inspect.getargvalues(frame)
        funcname=self.__name__
        self.command=funcname+'('+', '.join([i+'='+str(values[i]) for i in args if i!='self'])+')'
        g.m.statusBar().showMessage('Performing {}...'.format(self.__name__))
        self.keepSourceWindow=keepSourceWindow
        self.oldwindow=g.m.currentWindow
        if self.oldwindow is None:
            raise(MissingWindowError("You cannot execute '{}' without selecting a window first.".format(self.__name__)))
        self.tif=self.oldwindow.image
        self.oldname=self.oldwindow.name
    def end(self):
        commands=self.oldwindow.commands[:]
        commands.append(self.command)
        newWindow=Window(self.newtif,str(self.newname),self.oldwindow.filename,commands,self.oldwindow.metadata)
        if self.keepSourceWindow is False:
            self.oldwindow.close()
        else:
            self.oldwindow.reset()
        if np.max(self.newtif)==1 and np.min(self.newtif)==0: #if the array is boolean
            newWindow.imageview.setLevels(-.1,1.1)
        g.m.statusBar().showMessage('Finished with {}.'.format(self.__name__))
        del self.tif
        del self.newtif
        return newWindow

    def gui(self):
        if g.m.currentWindow is None:
            g.m.statusBar().showMessage('Select an image to process.')
            return False
        self.ui=BaseDialog(self.items,self.__name__,self.__doc__)
        if hasattr(self, '__url__'):
            self.ui.bbox.addButton(QDialogButtonBox.Help)
            self.ui.bbox.helpRequested.connect(lambda : QDesktopServices.openUrl(QUrl(self.__url__)))
        self.proxy= pg.SignalProxy(self.ui.changeSignal,rateLimit=60, slot=self.preview)
        self.ui.rejected.connect(g.m.currentWindow.reset)
        self.ui.accepted.connect(self.call_from_gui)
        self.ui.show()
        g.m.dialog=self.ui
        return True

    def gui_reset(self):
        self.items=[]
    def call_from_gui(self):
        varnames=[i for i in inspect.getargspec(self.__call__)[0] if i!='self' and i!='keepSourceWindow']
        try:
            args=[self.getValue(name) for name in varnames]
        except IndexError:
            print("Names in {}: {}".format(self.__name__,varnames))
        #print(args)
        try:
            self.__call__(*args,keepSourceWindow=True)
        except MemoryError as err:
            print('There was a memory error in {}'.format(self.__name__))
            g.m.statusBar().showMessage('There was a memory error in {}'.format(self.__name__))
            print(err)
    def preview(self):
        pass











