import os
import random
import numpy as np
import platform
from qtpy import uic, QtGui, QtWidgets
__all__ = ['nonpartial', 'setConsoleVisible', 'load_ui', 'random_color', 'save_file_gui', 'open_file_gui']

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
    if platform.system() == 'Windows':
        from ctypes import windll
        GetConsoleWindow = windll.kernel32.GetConsoleWindow
        console_window_handle = GetConsoleWindow()
        ShowWindow = windll.user32.ShowWindow
        ShowWindow(console_window_handle, v)
    else:
        print('Displaying the console on non-windows systems not yet supported')

def random_color():
    colors = [(165,42,42), (178,34,34), (220,20,60), (255,0,0), (255,99,71), (255,127,80), (205,92,92), (240,128,128), (233,150,122), 
    (250,128,114), (255,160,122), (255,69,0), (255,140,0), (255,165,0), (255,215,0), (184,134,11), (218,165,32), (238,232,170), (240,230,140),
    (128,128,0), (255,255,0), (154,205,50), (85,107,47), (107,142,35), (124,252,0), (127,255,0), (173,255,47), (34,139,34), (0,255,0),
    (50,205,50), (144,238,144), (152,251,152), (0,250,154), (0,255,127), (46,139,87), (102,205,170), (60,179,113), (32,178,170),
    (0,128,128), (0,139,139), (0,255,255), (0,255,255), (0,206,209), (64,224,208), (72,209,204), (175,238,238), (127,255,212), (176,224,230),
    (95,158,160), (70,130,180), (100,149,237), (0,191,255), (30,144,255), (173,216,230), (135,206,235), (135,206,250), 
    (138,43,226), (75,0,130), (106,90,205), (123,104,238), (147,112,219), (139,0,139), (148,0,211),
    (153,50,204), (186,85,211), (128,0,128), (216,191,216), (221,160,221), (238,130,238), (255,0,255), (218,112,214), (199,21,133), (219,112,147),
    (255,20,147), (255,105,180), (255,182,193), (255,192,203), (250,235,215), (245,245,220), (255,228,196), (255,235,205), (245,222,179), (255,248,220),
    (255,250,205), (250,250,210), (255,255,224), (139,69,19), (160,82,45), (210,105,30), (205,133,63), (244,164,96), (222,184,135), (210,180,140),
    (188,143,143), (255,228,181), (255,222,173), (255,218,185), (255,228,225), (255,240,245), (250,240,230), (253,245,230), (255,239,213), (255,245,238),
    (245,255,250), (176,196,222), (230,230,250), (240,248,255), (248,248,255), (240,255,240)]
    ind = np.random.choice(range(len(colors)))
    return QtGui.QColor(*colors[ind])

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

    return uic.loadUi(full_path, parent)

def save_file_gui(prompt="Save file", directory=None, filetypes=''):
    ''' File dialog for saving a new file, isolated to handle tuple/string return value
    Parameters
    ----------
    prompt : str
        string to display at the top of the window
    directory : str
        initial directory to save the file to
    filetypes: str
        argument for filtering file types separated by ;; (*.png) or (Images *.png);;(Other *.*)
    Returns
    -------
    str: the file path selected, or empty string if none
    '''
    from .. import global_vars as g
    if directory is None or directory == '':
        filename = g.settings['filename']
        try:
            directory = os.path.dirname(filename)
        except:
            directory = None
    if directory is None:
        filename = QtWidgets.QFileDialog.getSaveFileName(g.m, prompt, filter=filetypes)
    else:
        filename = QtWidgets.QFileDialog.getSaveFileName(g.m, prompt, directory, filter=filetypes)
    if isinstance(filename, tuple):
        filename, ext = filename
        if ext and '.' not in filename:
            filename += '.' + ext.rsplit('.')[-1]
    if filename is None or str(filename) == '':
        g.m.statusBar().showMessage('Save Cancelled')
        return None
    else:
        return str(filename)


def open_file_gui(prompt="Open File", directory=None, filetypes=''):
    ''' File dialog for opening an existing file, isolated to handle tuple/string return value
    Parameters
    ----------
    prompt : str
        string to display at the top of the window
    directory : str
        initial directory to open
    filetypes: str
        argument for filtering file types separated by ;; (*.png) or (Images *.png);;(Other *.*)
    Returns
    -------
    str: the file (path+file+extension) selected, or None
    '''
    from .. import global_vars as g

    if directory is None:
        filename = g.settings['filename']
        try:
            directory = os.path.dirname(filename)
        except:
            directory = None
    if directory is None:
        filename = QtWidgets.QFileDialog.getOpenFileName(g.m, prompt, '', filetypes)
    else:
        filename = QtWidgets.QFileDialog.getOpenFileName(g.m, prompt, filename, filetypes)
    if isinstance(filename, tuple):
        filename, ext = filename
        if ext and '.' not in filename:
            filename += '.' + ext.rsplit('.')[-1]
    if filename is None or str(filename) == '':
        g.m.statusBar().showMessage('No File Selected')
        return None
    else:
        return str(filename)

