from PyQt4 import uic
from PyQt4.QtCore import * # Qt is Nokias GUI rendering code written in C++.  PyQt4 is a library in python which binds to Qt
from PyQt4.QtGui import *
from PyQt4.QtCore import pyqtSignal as Signal
import sys, os, atexit
if sys.version_info.major==2:
    import cPickle as pickle # pickle serializes python objects so they can be saved persistantly.  It converts a python object into a savable data structure
    from urllib2 import urlopen
else:
    import pickle
    from urllib.request import urlopen
from os.path import expanduser
import numpy as np
from pyqtgraph.dockarea import *

from process.BaseProcess import BaseDialog, ColorSelector
import pyqtgraph as pg
from plugins.plugin_manager import PluginManager, load_plugin_menu
from script_editor.ScriptEditor import ScriptEditor
from multiprocessing import cpu_count
import re, time, datetime, zipfile, shutil, subprocess, os
from sys import executable
from subprocess import Popen
from dependency_check import check_dependencies



data_types = ['uint8', 'uint16', 'uint32', 'uint64', 'int8', 'int16', 'int32', 'int64', 'float16', 'float32', 'float64']

mainGuiInitialized=False

class Settings:
    initial_settings = {'filename': None, 
                        'internal_data_type': np.float64, 
                        'multiprocessing': True, 
                        'multipleTraceWindows': False, 
                        'mousemode': 'rectangle', 
                        'show_windows': True, 
                        'recent_scripts': [],
                        'recent_files': [],
                        'nCores':cpu_count(),
                        'debug_mode': False,
                        'point_color': '#ff0000',
                        'point_size': 5}
    def __init__(self):
        self.config_file=os.path.join(expanduser("~"),'.FLIKA','config.p' )
        try:
            self.d=pickle.load(open(self.config_file, "rb" ))
        except Exception as e:
            print("Failed to load settings file. %s\nDefault settings restored." % e)
            self.d=Settings.initial_settings
        self.d['mousemode'] = 'rectangle' # don't change initial mousemode
    def __getitem__(self, item):
        try:
            self.d[item]
        except KeyError:
            self.d[item]=Settings.initial_settings[item] if item in Settings.initial_settings else None
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
        self['mousemode']=mode
    def setMultipleTraceWindows(self, f):
        self['multipleTraceWindows'] = f
    def setInternalDataType(self, dtype):
        self['internal_data_type'] = dtype
        print('Changed data_type to {}'.format(dtype))
    def gui(self):
        old_dtype=str(np.dtype(self['internal_data_type']))
        dataDrop = pg.ComboBox(items=data_types, default=old_dtype)
        showCheck = QCheckBox()
        showCheck.setChecked(self.d['show_windows'])
        multipleTracesCheck = QCheckBox()
        multipleTracesCheck.setChecked(self['multipleTraceWindows'])
        multiprocessing = QCheckBox()
        multiprocessing.setChecked(self['multiprocessing'])
        nCores = QComboBox()
        debug_check = QCheckBox(checked=self['debug_mode'])
        debug_check.toggled.connect(setConsoleVisible)
        for i in np.arange(cpu_count())+1:
            nCores.addItem(str(i))
        nCores.setCurrentIndex(self['nCores']-1)
        items = []
        items.append({'name': 'internal_data_type', 'string': 'Internal Data Type', 'object': dataDrop})
        items.append({'name': 'show_windows', 'string': 'Show Windows', 'object': showCheck})
        items.append({'name': 'multipleTraceWindows', 'string': 'Multiple Trace Windows', 'object': multipleTracesCheck})
        items.append({'name': 'multiprocessing', 'string': 'Multiprocessing On', 'object': multiprocessing})
        items.append({'name': 'nCores', 'string': 'Number of cores to use when multiprocessing', 'object': nCores})
        items.append({'name': 'debug_mode', 'string': 'Debug Mode', 'object': debug_check})
        def update():
            self['internal_data_type'] = np.dtype(str(dataDrop.currentText()))
            self['show_windows'] = showCheck.isChecked()
            self['multipleTraceWindows'] = multipleTracesCheck.isChecked()
            self['multiprocessing']=multiprocessing.isChecked()
            self['nCores']=int(nCores.itemText(nCores.currentIndex()))
            self['debug_mode'] = debug_check.isChecked()
            
        self.bd = BaseDialog(items, 'FLIKA Settings', '')
        self.bd.accepted.connect(update)
        self.bd.changeSignal.connect(update)
        self.bd.show()
        
def pointSettings(pointButton):
    '''
    default points color
    default points size
    currentWindow points color
    currentWindow points size
    clear current points

    '''
    point_color = ColorSelector()
    point_color.color=m.settings['point_color']
    point_color.label.setText(point_color.color)
    point_size = QSpinBox()
    point_size.setRange(1,50)
    point_size.setValue(m.settings['point_size'])
    
    update_current_points_check = QCheckBox()
    update_current_points_check.setChecked(True)
    
    items = []
    items.append({'name': 'point_color', 'string': 'Default Point Color', 'object': point_color})
    items.append({'name': 'point_size', 'string': 'Default Point Size', 'object': point_size})
    items.append({'name': 'update_current_points_check', 'string': 'Update already plotted points', 'object': update_current_points_check})
    def update():
        m.settings['point_color'] = point_color.value()
        m.settings['point_size'] = point_size.value()
        if m.currentWindow is not None and update_current_points_check.isChecked()==True:
            color = QColor(point_color.value())
            m.currentWindow.scatterPlot.setBrush(pg.mkBrush(*color.getRgb()))
            m.currentWindow.scatterPlot.setSize(point_size.value())
    m.dialog = BaseDialog(items, 'Points Settings', '')
    m.dialog.accepted.connect(update)
    m.dialog.changeSignal.connect(update)
    m.dialog.show()
    
        
        
def mainguiClose(event):
    global m
    for win in m.windows[:] + m.traceWindows[:] + m.dialogs[:]:
        win.close()
    ScriptEditor.close()
    PluginManager.close()
    m.settings.save()
    event.accept() # let the window close

def messageBox(title, text, buttons=QMessageBox.Ok, icon=QMessageBox.Information):
    m.messagebox = QMessageBox(icon, title, text, buttons)
    m.messagebox.setWindowIcon(m.windowIcon())
    return m.exec()

def checkUpdates():
    try:
        data = urlopen('https://raw.githubusercontent.com/flika-org/flika/master/flika.py').read()[:100]
    except Exception as e:
        messageBox("Connection Failed", "Cannot connect to Flika Repository. Connect to the internet to check for updates.")
        return
    latest_version = re.findall(r'version=([\d\.]*)', str(data))
    version = re.findall(r'version=([\d\.]*)', open('flika.py', 'r').read()[:100])
    message = "Current Version: "
    if len(version) == 0:
        version = "Unknown"
        message += "Unknown"
    else:
        version = version[0]
        message += version
    message += '\nLatest Version: '
    if len(latest_version) == 0:
        latest_version = "Unknown"
        message += 'Unknown. Check Github Page'
    else:
        latest_version = latest_version[0]
        message += latest_version
    if any([int(j) > int(i) for i, j in zip(version.split('.'), latest_version.split('.'))]):
        if messageBox("Update Recommended", message + '\n\nWould you like to update?', QMessageBox.Yes | QMessageBox.No, QMessageBox.Question) == QMessageBox.Yes:
            updateFlika()
    else:
        messageBox("Up to date", "Your version of Flika is up to date")

def updateFlika():
    folder = os.path.dirname(__file__)
    parent_dir = os.path.dirname(folder)
    new_folder = folder + '-new'
    url = 'https://github.com/flika-org/flika/archive/master.zip'
    data = urlopen(url).read()
    output = open("flika.zip", "wb")
    output.write(data)
    output.close()

    extract_location = os.path.join(parent_dir, "temp_flika")

    with zipfile.ZipFile('flika.zip', "r") as z:
        folder_name = os.path.dirname(z.namelist()[0])
        if os.path.exists(extract_location):
            shutil.rmtree(extract_location)
        z.extractall(extract_location)
    os.remove('flika.zip')
    try:
        d = os.path.dirname(__file__)
        for path, subs, fs in os.walk(d):
            extract_path = path.replace(os.path.basename(d), os.path.join('temp_flika', 'flika-master'))
            for f in fs:
                if f.endswith(('.py', '.ui', '.png', '.txt', '.xml')):
                    old, new = os.path.join(path, f), os.path.join(extract_path, f)
                    if os.path.exists(old) and os.path.exists(new):
                        m.statusBar().showMessage('replacing %s' % f)
                        shutil.copy(new, old)
        Popen('python flika.py', shell=True)
        shutil.rmtree(extract_location)
        exit(0)
    except Exception as e:
        print("Failed to remove and replace old Flika. %s" % e)
    

def setConsoleVisible(v):
    from ctypes import windll
    GetConsoleWindow = windll.kernel32.GetConsoleWindow
    console_window_handle = GetConsoleWindow()
    ShowWindow = windll.user32.ShowWindow
    ShowWindow(console_window_handle, v)

class SetCurrentWindowSignal(QWidget):
    sig=Signal()
    def __init__(self,parent):
        QWidget.__init__(self,parent)
        self.hide()


def init(filename):
    global m, mainGuiInitialized
    mainGuiInitialized=True
    m=uic.loadUi(filename)
    load_plugin_menu()
    m.setCurrentWindowSignal=SetCurrentWindowSignal(m)
    m.settings = Settings()
    m.windows = []
    m.traceWindows = []
    m.dialogs = []
    m.currentWindow = None
    m.currentTrace = None

    m.clipboard = None
    m.setAcceptDrops(True)
    m.closeEvent = mainguiClose

