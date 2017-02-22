from __future__ import absolute_import, division, print_function
from qtpy.uic import loadUi
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QFileDialog
import os
import random
__all__ = ['nonpartial', 'setConsoleVisible', 'load_ui', 'random_color', 'getSaveFileName', 'getOpenFileName']

def nonpartial(func, *args, **kwargs):
    """
    Like functools.partial, this returns a function which, when called, calls
    ``func(*args, **kwargs)``.

    Unlike functools.partial, extra arguments passed to the returned function
    are *not* passed to the input function.
    """
    def result(*a, **k):
        return func(*args, **kwargs)

    return result

def setConsoleVisible(v):
    from ctypes import windll
    GetConsoleWindow = windll.kernel32.GetConsoleWindow
    console_window_handle = GetConsoleWindow()
    ShowWindow = windll.user32.ShowWindow
    ShowWindow(console_window_handle, v)

def random_color(h=None):
    if h == None:
        h = random.random()
    golden_ratio_conjugate = 0.618033988749895
    h += golden_ratio_conjugate
    h %= 1
    return QColor(*hsv_to_rgb(h, 0.5, 0.95))

def hsv_to_rgb(h, s, v):
    h_i = int(h*6)
    f = h*6 - h_i
    p = v * (1 - s)
    q = v * (1 - f*s)
    t = v * (1 - (1 - f) * s)
    if h_i == 0:
        r, g, b = v, t, p
    if h_i == 1:
        r, g, b = q, v, p
    if h_i == 2:
        r, g, b = p, v, t
    if h_i == 3:
        r, g, b = p, q, v
    if h_i == 4:
        r, g, b = t, p, v
    if h_i == 5:
        r, g, b = v, p, q
    return [int(r*256), int(g*256), int(b*256)]

def load_ui(path, parent=None, directory=None):
    """
    Load a .ui file

    Parameters
    ----------
    path : str
        Name of ui file to load

    parent : QObject
        Object to use as the parent of this widget

    Returns
    -------
    w : QtWidgets.QWidget
        The new widget
    """

    if directory is not None:
        full_path = os.path.join(directory, path)
    else:
        full_path = os.path.abspath(path)

    if not os.path.exists(full_path) and 'site-packages.zip' in full_path:
        # Workaround for Mac app
        full_path = os.path.join(full_path.replace('site-packages.zip', 'flika'))

    return loadUi(full_path, parent)

def getSaveFileName(parent, title, initial='', filters=''):
    ''' File dialog for saving a new file, isolated to handle tuple/string return value
    Parameters
    ----------
    parent : QWidget object
        parent of the window to make
    title : str
        string to display at the top of the window
    initial : str
        initial path to save the file to
    filters: str
        argument for filtering file types separated by ;; (*.png) or (Images *.png);;(Other *.*)
    Returns
    -------
    str: the file path selected, or empty string if none
    '''
    filename= QFileDialog.getSaveFileName(parent, title, initial, filters)
    filename = str(filename[0] if isinstance(filename, tuple) else filename)
    
    return filename

def getOpenFileName(parent, title, initial='', filters=''):
    ''' File dialog for opening an existing file, isolated to handle tuple/string return value
    Parameters
    ----------
    parent : QWidget object
        parent of the window to make
    title : str
        string to display at the top of the window
    initial : str
        initial path to open
    filters: str
        argument for filtering file types separated by ;; (*.png) or (Images *.png);;(Other *.*)
    Returns
    -------
    str: the file path selected, or empty string if none
    '''
    filename= QFileDialog.getOpenFileName(parent, title, initial, filters)
    filename = str(filename[0] if isinstance(filename, tuple) else filename)
    return filename