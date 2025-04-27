import importlib.resources
import os
import platform

import numpy as np
from qtpy import QtCore, QtGui, QtWidgets

import flika.global_vars as g
import flika.images
from flika.logger import logger

__all__ = [
    "nonpartial",
    "setConsoleVisible",
    "load_ui",
    "random_color",
    "save_file_gui",
    "open_file_gui",
    "inside_ipython",
    "get_flika_icon",
]


def inside_ipython() -> bool:
    try:
        __IPYTHON__  # type: ignore
        return True
    except NameError:
        return False


def get_flika_icon() -> QtGui.QIcon:
    with importlib.resources.path(flika.images, "favicon.ico") as icon_path:
        flika_icon = QtGui.QIcon(str(icon_path))
    return flika_icon


def nonpartial(func, *args, **kwargs):
    """Pass args and kwargs without an automatic binding of the first
    arguemnt to self (as is done in a bound method)."""

    def result(*a, **k):
        return func(*(args + a), **dict(kwargs, **k))

    return result


def setConsoleVisible(v):
    """
    Only works on windows or linux
    On linux, runs xdotool to show/hide the parent window of the program
    On windows, shows/hides the attached console window
    Other platforms are not supported
    v: boolean, True to show and False to hide
    """
    if platform.system() == "Windows":
        import ctypes

        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), v)
    elif platform.system() == "Linux":
        for _ in range(
            2
        ):  # xdotool won't work on 1st try if the flika window has focus, so try twice
            QtWidgets.QApplication.processEvents()
            win = QtWidgets.QApplication.activeWindow()
            try:
                os.system(
                    f"xdotool windowactivate $(xdotool search --pid {os.getppid()} | head -1)"
                )
                os.system(f"xdotool windowactivate {win.winId() if v else ''}")
            except:
                pass


def random_color() -> QtGui.QColor:
    """
    Generate a random RGB color and return it as a QColor object.

    Returns:
        QtGui.QColor: A randomly generated color
    """
    rgb: np.ndarray = np.random.randint(0, 255, 3)
    return QtGui.QColor(int(rgb[0]), int(rgb[1]), int(rgb[2]))


def load_ui(path, parent=None, directory=None):
    """
    Load a .ui file for PyQt.

    Args:
        path (str): Path to .ui file
        parent: Parent element
        directory (str): Directory where the path is relative to

    Returns:
        QWidget: UI widget
    """
    if directory is not None:
        path = os.path.join(directory, path)
    if not os.path.isfile(path):
        raise IOError(f"File '{path}' does not exist")

    try:
        from qtpy.uic import loadUi

        ui = loadUi(path, parent)  # PyQt method
        return ui
    except Exception as e:
        logger.debug(f"ui loading failed: {e}")
        if hasattr(QtCore, "QMetaObject"):  # Pyside fallback
            l = QtCore.QMetaObject.connectSlotsByName
        else:  # PySide2 fallback
            l = QtCore.QObject.connectSlotsByName
        return l(QtWidgets.QWidget(parent))


def save_file_gui(prompt="Save file", directory=None, filetypes=""):
    """
    Open a save file dialog.

    Args:
        prompt (str): Dialog title
        directory (str): Initial directory
        filetypes (str): File filter string (e.g., "Images (*.jpg, *.png)")

    Returns:
        str: Selected file path or empty string if canceled
    """
    if directory is None:
        directory = g.settings["filename"]
    if directory is None:
        directory = ""
    try:
        filename = QtWidgets.QFileDialog.getSaveFileName(
            None, prompt, directory, filetypes
        )
        if isinstance(filename, tuple):
            filename = filename[0]
        filename = str(filename)
        if filename != "":
            file_dir = os.path.dirname(filename)
            g.settings["filename"] = file_dir
            g.m.statusBar().showMessage(
                f"Successfully saved file '{os.path.basename(filename)}'"
            )
    except Exception as e:
        logger.error(f"Error in save_file_gui: {e}")
        filename = ""
    return filename


def open_file_gui(prompt="Open File", directory=None, filetypes=""):
    """
    Open a file dialog.

    Args:
        prompt (str): Dialog title
        directory (str): Initial directory
        filetypes (str): File filter string (e.g., "Images (*.jpg, *.png)")

    Returns:
        str: Selected file path or None if canceled
    """
    if directory is None:
        directory = g.settings["filename"]
    if directory is None:
        directory = ""
    try:
        filename = QtWidgets.QFileDialog.getOpenFileName(
            g.m, prompt, directory, filetypes
        )
        if isinstance(filename, tuple):
            filename = filename[0]
        filename = str(filename)
        if filename == "":
            return None
        file_dir = os.path.dirname(filename)
        g.settings["filename"] = file_dir
        return filename
    except Exception as e:
        logger.error(f"Error in open_file_gui: {e}")
        return None


def send_error_report(email, report):
    """
    Log error reports to the flikarest.pythonanywhere REST API to be stored in a SQL database

    Parameters:
        email (str): Email of the user, optionally entered for response
        report (str): The complete error that occurred

    Returns:
        Request Response if the API was reached, or None if connection failed. Use response.status==200 to check success
    """
    import requests

    from .. import global_vars as g

    address = g.settings["user_information"]["UUID"]
    location = g.settings["user_information"]["location"]

    kargs = {"address": address, "email": email, "report": report, "location": location}
    try:
        r = requests.post(
            "http://flikarest.pythonanywhere.com/reports/submit", data=kargs
        )
        return r
    except requests.exceptions.ConnectionError:
        return None


def send_user_stats():
    """
    Log user information to the flikarest.pythonanywhere REST API to be stored in a SQL database.

    This function replaces the Send_User_Stats_Thread class with a simple function that can be
    run in a thread using the thread_manager module.
    """
    import requests

    from .. import global_vars as g

    address = g.settings["user_information"]["UUID"]
    location = g.settings["user_information"]["location"]
    kargs = {"address": address, "location": location}
    try:
        r = requests.post(
            "http://flikarest.pythonanywhere.com/user_stats/log_user", data=kargs
        )
        return r
    except requests.exceptions.ConnectionError:
        return None
    except Exception as e:
        logger.error(f"Error sending user stats: {e}")
        return None


def convert_to_string(arg) -> str:
    """
    Convert a Python object to its string representation for use in command strings.

    Args:
        arg: Any Python object

    Returns:
        str: String representation of the object
    """
    if isinstance(arg, str):
        return "'" + arg + "'"
    elif isinstance(arg, bool):
        return str(arg)
    elif isinstance(arg, (list, tuple, dict)):
        return str(arg)
    elif isinstance(arg, np.ndarray):
        return "np.array(" + str(arg.tolist()) + ")"
    else:
        return str(arg)
