# -*- coding: utf-8 -*-
"""
If flika is loaded using::

    from flika import *

then all of the variables inside global_vars can be accessed as ``g.*``. For instance, to access the 
image inside current window, simply run::

    I = g.win.image



"""
from .logger import logger
logger.debug("Started 'reading global_vars.py'")
import os
from multiprocessing import cpu_count
from os.path import expanduser
from qtpy import QtWidgets, QtGui, QtCore
from collections.abc import MutableMapping
import json
from uuid import getnode
from .utils.misc import get_location

__all__ = ['m', 'Settings', 'menus', 'alert', 'windows', 'traceWindows', 'currentWindow', 'win', 'currentTrace', 'clipboard']

class Settings(MutableMapping): #http://stackoverflow.com/questions/3387691/python-how-to-perfectly-override-a-dict
    """
    All of flika's settings are stored in this object, which is designed to act like a dictionary. When any value in
    this object is changed, this object is converted to json and saved in ``~/.FLIKA/settings.json``. When flika is
    restarted, this settings object is populated with values from this file. Settings can be accessed using 
    `g.settings`. 


    """
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
                        'default_roi_on_click': False}

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
        """save(self)
                 Save settings file. The file is stored in ``~/.FLIKA/settings.json`` """
        if not os.path.exists(os.path.dirname(self.settings_file)):
            os.makedirs(os.path.dirname(self.settings_file))
        with open(self.settings_file, 'w') as fp:
            json.dump(self.d, fp, indent=4)

    def load(self):
        """load(self)
        Load settings file. The file is stored in ``~/.FLIKA/settings.json`` """
        if not os.path.exists(self.settings_file):
            print('No settings file found. Creating settings file.')
            self.save()
        try:
            with open(self.settings_file, 'r') as fp:
                d = json.load(fp)
            d = {k: d[k] for k in d if d[k] is not None}
            self.d.update(d)
        except Exception as e:
            msg = "Failed to load settings file. {}\nDefault settings restored.".format(e)
            logger.info(msg)
            print(msg)
            self.save()
        self.d['mousemode'] = 'rectangle'  # don't change initial mousemode
        self._load_user_information()

    def _load_user_information(self):
        '''_load_user_information(self)
        Loads user information if present. If not, the new user information is stored in self.d
        '''
        if 'user_information' not in self.d:
            self.d['user_information'] = {}
        if 'UUID' not in self.d['user_information'] or self.d['user_information']['UUID'] is None:
            self.d['user_information']['UUID'] = getnode()
        if 'location' not in self.d['user_information'] or self.d['user_information']['location'] is None:
            self.d['user_information']['location'] = get_location()


    def setmousemode(self, mode):
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


def alert(msg, title="flika - Alert"):
    """alert(msg, title="flika - Alert')
    Creates a popup that alerts the user.

    Arguments:
        msg (str): Alert message displayed to the user
        title (str): Title of the alert message popup
    """

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
m = None  #: The main window.
menus = []
windows = [] #: list of :class:`windows<flika.window.Window>`: All of the windows that have been created and have not yet been closed.
traceWindows = [] #: list of :class:`TraceFigs<flika.tracefig.TraceFig>`: All of the TraceFigs that are open.
dialogs = []
currentWindow = None #: :class:`window <flika.window.Window>`: The window that is currently selected
win = None #: :class:`window <flika.window.Window>`: The window that is currently selected
currentTrace = None #: :class:`tracefigs<flika.tracefig.TraceFig>`: The tracefig that is currently selected
clipboard = None






logger.debug("Completed 'reading global_vars.py'")