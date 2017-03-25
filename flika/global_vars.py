# -*- coding: utf-8 -*-
"""
Flika
@author: Kyle Ellefsen
@author: Brett Settle
@license: MIT
"""

import numpy as np
from urllib.request import urlopen
from urllib.error import HTTPError
import re, os
from multiprocessing import cpu_count
from os.path import expanduser
from qtpy import QtWidgets, QtGui, QtCore
from collections.abc import MutableMapping
import json, zipfile
from pkg_resources import parse_version
import shutil

__all__ = ['m', 'Settings', 'menus', 'checkUpdates', 'alert']

class Settings(MutableMapping): #http://stackoverflow.com/questions/3387691/python-how-to-perfectly-override-a-dict
    initial_settings = {'filename': None, 
                        'internal_data_type': 'float64',
                        'multiprocessing': True, 
                        'multipleTraceWindows': False, 
                        'mousemode': 'rectangle', 
                        'show_windows': True, 
                        'recent_scripts': [],
                        'recent_files': [],
                        'nCores':cpu_count(),
                        'debug_mode': False,
                        'point_color': '#ff0000',
                        'point_size': 5,
                        'roi_color': '#ffff00',
                        'rect_width': 5,
                        'rect_height': 5,
                        'show_all_points': False,
                        'default_rect_on_click': False}

    def __init__(self):
        self.settings_file = os.path.join(expanduser("~"), '.FLIKA', 'settings.json' )
        self.d = Settings.initial_settings
        self.load()

    def __getitem__(self, item):
        try:
            self.d[item]
        except KeyError:
            self.d[item] = Settings.initial_settings[item] if item in Settings.initial_settings else None
        return self.d[item]

    def __setitem__(self, key, item):
        self.d[key] = item
        self.save()

    def __delitem__(self, key):
        del self.d[key]

    def __iter__(self):
        return iter(self.d)

    def __len__(self):
        return len(self.d)

    def __contains__(self, item):
        return item in self.d

    def save(self):
        """ Save settings file. """
        if not os.path.exists(os.path.dirname(self.settings_file)):
            os.makedirs(os.path.dirname(self.settings_file))
        with open(self.settings_file, 'w') as fp:
            json.dump(self.d, fp, indent=4)

    def load(self):
        """ Load settings file. """
        try:
            with open(self.settings_file, 'r') as fp:
                d = json.load(fp)
            d = {k: d[k] for k in d if d[k] is not None}
            self.d.update(d)
        except Exception as e:
            from .logger import logger
            msg = "Failed to load settings file. {}\nDefault settings restored.".format(e)
            logger.info(msg)
            print(msg)
            self.save()
        self.d['mousemode'] = 'rectangle'  # don't change initial mousemode

    def setmousemode(self,mode):
        self['mousemode']=mode

    def setMultipleTraceWindows(self, f):
        self['multipleTraceWindows'] = f

    def setInternalDataType(self, dtype):
        self['internal_data_type'] = dtype
        print('Changed data_type to {}'.format(dtype))


def messageBox(title, text, buttons=QtWidgets.QMessageBox.Ok, icon=QtWidgets.QMessageBox.Information):
    m.messagebox = QtWidgets.QMessageBox(icon, title, text, buttons)
    m.messagebox.setWindowIcon(m.windowIcon())
    m.messagebox.show()
    while m.messagebox.isVisible(): QtWidgets.QApplication.instance().processEvents()
    return m.messagebox.result()


def checkUpdates():
    try:
        url = "https://raw.githubusercontent.com/flika-org/flika/master/flika/version.py"
    except Exception as e:
        alert("Connection Failed", "Cannot connect to Flika Repository. Connect to the internet to check for updates. %s" % e)
        return
    
    data = urlopen(url).read().decode('utf-8')
    print(data)
    latest_version = re.match(r'__version__\s*=\s*([\d\.\']*)', data)
    print(latest_version)
    from .version import __version__
    version = __version__
    message = "Installed version: " + version
    if latest_version is None:
        latest_version = 'Unknown'
    else:
        latest_version = eval(latest_version.group(1))
    message += '\nLatest Version: ' + latest_version

    if parse_version(version) < parse_version(latest_version):
        if messageBox("Update Recommended", message + '\n\nWould you like to update?', QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.Question) == QtWidgets.QMessageBox.Yes:
            updateFlika()
    else:
        messageBox("Up to date", "Your version of Flika is up to date\n" + message)


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
    print("file: {}".format(__file__))
    try:
        for path, subs, fs in os.walk(folder):
            extract_path = path.replace(os.path.basename(folder), os.path.join('temp_flika', 'flika-master'))
            for f in fs:
                if f.endswith(('.py', '.ui', '.png', '.txt', '.xml')):
                    old, new = os.path.join(path, f), os.path.join(extract_path, f)
                    if os.path.exists(old) and os.path.exists(new):
                        m.statusBar().showMessage('replacing %s' % f)
                        shutil.copy(new, old)
        shutil.rmtree(extract_location)
    except Exception as e:
        messageBox("Update Error", "Failed to remove and replace old Flika. %s" % e, icon=QtWidgets.QMessageBox.Warning)

    #if not 'SPYDER_SHELL_ID' in os.environ:
    #    Popen('python flika.py', shell=True)

    alert('Update successful. Restart Flika to complete update.')
    

def setConsoleVisible(v):
    from ctypes import windll
    GetConsoleWindow = windll.kernel32.GetConsoleWindow
    console_window_handle = GetConsoleWindow()
    ShowWindow = windll.user32.ShowWindow
    ShowWindow(console_window_handle, v)


class SetCurrentWindowSignal(QtWidgets.QWidget):
    sig = QtCore.Signal()

    def __init__(self,parent):
        QtWidgets.QWidget.__init__(self,parent)
        self.hide()


def alert(msg, title="Flika - Alert"):
    print('\nAlert: ' + msg)
    msgbx = QtWidgets.QMessageBox(m)
    msgbx.setIcon(QtWidgets.QMessageBox.Information)
    msgbx.setText(msg)
    msgbx.setWindowTitle(title)
    msgbx.show()
    m.statusBar().showMessage(msg)
    desktopSize = QtWidgets.QDesktopWidget().screenGeometry()
    top = (desktopSize.height() / 2) - (msgbx.size().height() / 2)
    left = (desktopSize.width() / 2) - (msgbx.size().width() / 2)
    msgbx.move(left, top)
    dialogs.append(msgbx)


settings = Settings()
m = None  # will be main window
menus = []
windows = []
traceWindows = []
dialogs = []
currentWindow = None
currentTrace = None
clipboard = None






