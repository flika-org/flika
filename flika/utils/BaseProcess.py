"""
Base process module for flika operations.
"""

import inspect

import numpy as np
from qtpy import QtCore, QtWidgets

import flika.global_vars as g
import flika.window
from flika.utils.custom_widgets import *  # pylint: disable=wildcard-import

__all__ = ["BaseProcess", "BaseProcess_noPriorWindow"]


# Type aliases for process items
# A ProcessItem represents a single parameter for a process
# with its name, display string, UI widget, and current value
ProcessItem = dict[
    str, str | QtWidgets.QWidget | object
]  # Keys include 'name', 'string', 'object', 'value'
# ProcessItems is a collection of ProcessItem dictionaries
ProcessItems = list[ProcessItem]


def _convert_item_to_string(item):
    if isinstance(item, str):
        return f"'{item}'"
    else:
        return str(item)


class BaseProcess(object):
    """BaseProcess(object)
    Foundation for all flika processes. Subclass BaseProcess when writing your own process.

    Attributes:
        items: List of dictionaries that store process parameters and their metadata.
            Each dictionary in this list represents a single parameter and contains:
            - 'name': Identifier used to retrieve the parameter value
            - 'string': Human-readable label shown in the UI
            - 'object': Qt widget used for input in the GUI
            - 'value': Current value of the parameter

            The items list serves multiple purposes:
            1. Auto-generates UI forms through BaseDialog
            2. Stores and retrieves parameter values during process execution
            3. Enables parameter persistence between sessions
            4. Provides a standardized parameter management system across all processes

            Process subclasses should populate this list in their gui() method
            and access values via getValue().
    """

    def __init__(self):
        self.noPriorWindow: bool = False
        self.__name__: str = self.__class__.__name__.lower()
        self.items: ProcessItems = []
        self.newtif: np.ndarray | None = None
        self.newname: str = ""
        self.tif: np.ndarray | None = None
        self.oldwindow: flika.window.Window | None = None
        self.oldname: str = ""
        self.keepSourceWindow: bool = False
        self.command: str = ""

    def getValue(self, name: str) -> object:
        """getValue(self,name)

        Returns:
            The value of a the name stored in self.items

        """
        return [i["value"] for i in self.items if i["name"] == name][0]

    def get_init_settings_dict(self) -> dict[str, object]:
        """get_init_settings_dict(self)
        Function for storing the intial settings of any BaseProcess into self.items

        Note:
            In most cases when writing a BaseProcess subclass, this function must be overloaded

        Returns:
            A dictionary containing the initial settings and their values

        """
        return dict()  # this function needs to be overwritten by every subclass

    def start(self, keepSourceWindow):
        frame = inspect.getouterframes(inspect.currentframe())[1][0]
        args, _, _, values = inspect.getargvalues(frame)
        funcname = self.__name__
        self.command = (
            funcname
            + "("
            + ", ".join(
                [
                    i + "=" + _convert_item_to_string(values[i])
                    for i in args
                    if i != "self"
                ]
            )
            + ")"
        )
        g.m.statusBar().showMessage("Running function {}...".format(self.__name__))
        self.keepSourceWindow = keepSourceWindow
        self.oldwindow = g.win
        if self.oldwindow is None:
            raise (
                MissingWindowError(
                    "You cannot execute '{}' without selecting a window first.".format(
                        self.__name__
                    )
                )
            )
        self.tif = self.oldwindow.image
        self.oldname = self.oldwindow.name

    def end(self) -> flika.window.Window | None:
        from flika import window

        if not hasattr(self, "newtif") or self.newtif is None:
            self.oldwindow.reset()
            return
        commands = self.oldwindow.commands[:]
        if hasattr(self, "command"):
            commands.append(self.command)
        newWindow = window.Window(
            self.newtif,
            str(self.newname),
            self.oldwindow.filename,
            commands,
            self.oldwindow.metadata,
        )
        if self.keepSourceWindow is False:
            self.oldwindow.close()
        else:
            self.oldwindow.reset()
        if (
            np.max(self.newtif) == 1 and np.min(self.newtif) == 0
        ):  # if the array is boolean
            newWindow.imageview.setLevels(-0.1, 1.1)
        g.m.statusBar().showMessage("Finished with {}.".format(self.__name__))
        del self.tif
        del self.newtif
        return newWindow

    def gui(self):
        from pyqtgraph import SignalProxy

        self.ui = BaseDialog(self.items, self.__name__, self.__doc__, self)
        if hasattr(self, "__url__"):
            self.ui.bbox.addButton(QtWidgets.QDialogButtonBox.Help)
            self.ui.bbox.helpRequested.connect(
                lambda: QtWidgets.QDesktopServices.openUrl(QtCore.QUrl(self.__url__))
            )
        self.proxy = SignalProxy(self.ui.changeSignal, rateLimit=60, slot=self.preview)
        if g.win is not None:
            self.ui.rejected.connect(g.win.reset)
        self.ui.closeSignal.connect(self.ui.rejected.emit)
        self.ui.accepted.connect(self.call_from_gui)
        self.ui.resize(750, 450)
        self.ui.show()
        g.dialogs.append(self.ui)
        return True

    def gui_reset(self):
        self.items: ProcessItems = []

    def call_from_gui(self):
        varnames = [
            i
            for i in inspect.getfullargspec(self.__call__)[0]
            if i != "self" and i != "keepSourceWindow"
        ]
        try:
            args = [self.getValue(name) for name in varnames]
        except IndexError as err:
            msg = "IndexError in {}: {}".format(self.__name__, varnames)
            msg += str(err)
            g.alert(msg)
        newsettings = dict()
        for name in varnames:
            value = self.getValue(name)
            # cannot save window objects using pickle
            if not isinstance(value, flika.window.Window):
                newsettings[name] = value
        g.settings["baseprocesses"][self.__name__] = newsettings
        g.settings.save()
        try:
            if self.noPriorWindow:
                self.__call__(*args)
            else:
                self.__call__(*args, keepSourceWindow=True)
        except MemoryError as err:
            msg = "There was a memory error in {}. Close other programs and try again.".format(
                self.__name__
            )
            msg += str(err)
            g.alert(msg)

    def preview(self):
        pass


class BaseProcess_noPriorWindow(BaseProcess):
    """A BaseProcess subclass that has no prior window.
    Some flika objects inherit this class."""

    def __init__(self):
        super().__init__()
        self.noPriorWindow = True

    def start(self):
        frame = inspect.getouterframes(inspect.currentframe())[1][0]
        args, _, _, values = inspect.getargvalues(frame)
        funcname = self.__name__
        self.command = (
            funcname
            + "("
            + ", ".join(
                [
                    i + "=" + _convert_item_to_string(values[i])
                    for i in args
                    if i != "self"
                ]
            )
            + ")"
        )
        g.m.statusBar().showMessage("Performing {}...".format(self.__name__))

    def end(self):
        from flika import window

        commands = [self.command]
        newWindow = window.Window(self.newtif, str(self.newname), commands=commands)
        if (
            np.max(self.newtif) == 1 and np.min(self.newtif) == 0
        ):  # if the array is boolean
            newWindow.imageview.setLevels(-0.1, 1.1)
        g.m.statusBar().showMessage("Finished with {}.".format(self.__name__))
        del self.newtif
        return newWindow
