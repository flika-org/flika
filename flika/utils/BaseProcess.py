# -*- coding: utf-8 -*-
from ..utils.misc import save_file_gui
from .. import global_vars as g
import markdown
import inspect
import sys
from qtpy import QtCore, QtGui, QtWidgets
import numpy as np
import os.path
from ..logger import logger
logger.debug("Started 'reading process/BaseProcess.py'")


__all__ = ['MissingWindowError', 'WindowSelector', 'FileSelector', 'ColorSelector', 'SliderLabel',
           'SliderLabelOdd', 'CheckBox', 'ComboBox', 'BaseDialog', 'BaseProcess', 'BaseProcess_noPriorWindow']


class MissingWindowError(Exception):
    def __init__(self, value):
        self.value = value
        g.m.statusBar().showMessage(value)

    def __str__(self):
        return repr(self.value)


class WindowSelector(QtWidgets.QWidget):
    """
    This widget is a button with a label.  Once you click the button, the widget waits for you to click a Window object.  Once you do, it sets self.window to be the window, and it sets the label to be the widget name.
    """
    valueChanged = QtCore.Signal()

    def __init__(self):
        QtWidgets.QWidget.__init__(self)
        self.button = QtWidgets.QPushButton('Select Window')
        self.button.setCheckable(True)
        self.label = QtWidgets.QLabel('None')
        self.window = None
        self.layout = QtWidgets.QHBoxLayout()
        self.layout.addWidget(self.button)
        self.layout.addWidget(self.label)
        self.setLayout(self.layout)
        self.button.clicked.connect(self.buttonclicked)

    def buttonclicked(self):
        if self.button.isChecked() is False:
            g.m.setCurrentWindowSignal.sig.disconnect(self.setWindow)
        else:
            g.m.setCurrentWindowSignal.sig.connect(self.setWindow)

    def setWindow(self, window=None):
        if window is None:
            try:
                g.m.setCurrentWindowSignal.sig.disconnect(self.setWindow)
            except TypeError:
                pass
            self.window = g.win
        else:
            self.window = window
        self.button.setChecked(False)
        self.label.setText('...'+os.path.split(self.window.name)[-1][-20:])
        self.valueChanged.emit()
        self.parent().raise_()

    def value(self):
        return self.window

    def setValue(self, window):
        ''' This function is written to satify the requirement that all items have a setValue function to recall from settings the last set value. '''
        self.setWindow(window)


class FileSelector(QtWidgets.QWidget):
    """
    This widget is a button with a label.  Once you click the button, the widget waits for you to select a file to save.  Once you do, it sets self.filename and it sets the label.
    """
    valueChanged = QtCore.Signal()

    def __init__(self, filetypes='*.*'):
        QtWidgets.QWidget.__init__(self)
        self.button = QtWidgets.QPushButton('Select Filename')
        self.label = QtWidgets.QLabel('None')
        self.window = None
        self.layout = QtWidgets.QHBoxLayout()
        self.layout.addWidget(self.button)
        self.layout.addWidget(self.label)
        self.setLayout(self.layout)
        self.button.clicked.connect(self.buttonclicked)
        self.filetypes = filetypes
        self.filename = ''

    def buttonclicked(self):
        prompt = 'testing fileSelector'
        self.filename = save_file_gui(prompt, filetypes=self.filetypes)
        self.label.setText('...'+os.path.split(self.filename)[-1][-20:])
        self.valueChanged.emit()

    def value(self):
        return self.filename

    def setValue(self, filename):
        self.filename = str(filename)
        self.label.setText('...' + os.path.split(self.filename)[-1][-20:])


def color_pixmap(color):
    pm = QtGui.QPixmap(15, 15)
    p = QtGui.QPainter(pm)
    b = QtGui.QBrush(QtGui.QColor(color))
    p.fillRect(-1, -1, 20, 20, b)
    return pm


class ColorSelector(QtWidgets.QWidget):
    """
    This widget is a button with a label.  Once you click the button, the widget waits for you to select a color.  Once you do, it sets self.color and it sets the label.
    """
    valueChanged = QtCore.Signal()

    def __init__(self):
        QtWidgets.QWidget.__init__(self)
        self.button = QtWidgets.QPushButton('Select Color')
        self.label = QtWidgets.QLabel('None')
        self.window = None
        self.layout = QtWidgets.QHBoxLayout()
        self.layout.addWidget(self.button)
        self.layout.addWidget(self.label)
        self.setLayout(self.layout)
        self.button.clicked.connect(self.buttonclicked)
        self._color = ''
        self.colorDialog = QtWidgets.QColorDialog()
        self.colorDialog.colorSelected.connect(self.colorSelected)

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, color):
        self._color = color
        self.button.setIcon(QtGui.QIcon(color_pixmap(color)))

    def buttonclicked(self):
        self.colorDialog.open()

    def value(self):
        return self._color

    def colorSelected(self, color):
        if color.isValid():
            self.color = color.name()
            self.label.setText(color.name())
            self.valueChanged.emit()


class SliderLabel(QtWidgets.QWidget):
    changeSignal = QtCore.Signal(int)

    def __init__(self, decimals: int = 0):
        """
        Args:
          decimals: the resolution of the slider. 0 means only integers,  1 
          means the tens place, etc.
        """
        # decimals specifies the resolution of the slider.
        QtWidgets.QWidget.__init__(self)
        self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.decimals = decimals
        if self.decimals <= 0:
            self.label = QtWidgets.QSpinBox()
        else:
            self.label = QtWidgets.QDoubleSpinBox()
            self.label.setDecimals(self.decimals)
        self.layout = QtWidgets.QHBoxLayout()
        self.layout.addWidget(self.slider)
        self.layout.addWidget(self.label)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)
        self.slider.valueChanged.connect(
            lambda slider_value: self.updateLabel(self.slider_2_spinbox(slider_value)))
        self.label.valueChanged.connect(self.updateSlider)
        self.valueChanged = self.label.valueChanged

    def spinbox_2_slider(self, spinbox_value: float | int) -> int:
        """Takes a spinbox value and converts it to a slider value."""
        return int(spinbox_value * 10**self.decimals)
    
    def slider_2_spinbox(self, slider_value: int) -> int | float:
        """Takes a slider value and converts it to a spinbox value."""
        spinbox_value = slider_value / 10**self.decimals
        if isinstance(self.label, QtWidgets.QSpinBox):
            spinbox_value = int(spinbox_value)
        return spinbox_value

    @QtCore.Slot(float)
    @QtCore.Slot(int)
    def updateSlider(self, value: int | float):
        slider_value = self.spinbox_2_slider(value)
        self.slider.setValue(slider_value)

    def updateLabel(self, spinbox_value: int | float):
        """Sets the spinbox value."""
        self.label.setValue(spinbox_value)

    def value(self) -> int | float:
        """Gets the spinbox value."""
        return self.label.value()

    def setRange(self, new_min: float, new_max: float):
        new_slider_min = self.spinbox_2_slider(new_min)
        new_slider_max = self.spinbox_2_slider(new_max)
        self.slider.setRange(new_slider_min, new_slider_max)
        self.label.setRange(new_min, new_max)

    def setMinimum(self, new_min: float):
        new_slider_min = self.spinbox_2_slider(new_min)
        self.slider.setMinimum(new_slider_min)
        self.label.setMinimum(new_min)

    def setMaximum(self, new_max: float):
        new_slider_max = self.spinbox_2_slider(new_max)
        self.slider.setMaximum(new_slider_max)
        self.label.setMaximum(new_max)

    def setValue(self, spinbox_value: float):
        slider_value = self.spinbox_2_slider(spinbox_value)
        self.slider.setValue(slider_value)
        self.label.setValue(spinbox_value)

    def setSingleStep(self, spinbox_step_value: int | float):
        self.label.setSingleStep(spinbox_step_value)

    def setEnabled(self, enabled: bool):
        self.label.setEnabled(enabled)
        self.slider.setEnabled(enabled)


class SliderLabelOdd(SliderLabel):
    '''This is a modified SliderLabel class that forces the user to only choose odd numbers.'''

    def __init__(self):
        SliderLabel.__init__(self, decimals=0)

    @QtCore.Slot(int)
    def updateSlider(self, value):
        value = int(value)
        if value % 2 == 0:  # if value is even
            value += 1
        self.slider.setValue(value)

    def updateLabel(self, spinbox_value: int | float):
        spinbox_value = int(spinbox_value)
        if spinbox_value % 2 == 0:  # if value is even
            spinbox_value += 1
        self.label.setValue(spinbox_value)


class CheckBox(QtWidgets.QCheckBox):
    '''Overwrote the QCheckBox class so that every graphical element has the method 'setValue'
    '''

    def __init__(self, parent=None):
        QtWidgets.QCheckBox.__init__(self, parent)

    def setValue(self, value):
        self.setChecked(value)


class ComboBox(QtWidgets.QComboBox):
    '''Overwrote the QComboBox class so that every graphical element has the method 'setValue'
    '''

    def __init__(self, parent=None):
        QtWidgets.QComboBox.__init__(self, parent)

    def setValue(self, value):
        if isinstance(value, str):
            idx = self.findText(value)
        else:
            idx = self.findData(value)
        if idx != -1:
            self.setCurrentIndex(idx)


class BaseDialog(QtWidgets.QDialog):
    changeSignal = QtCore.Signal()
    closeSignal = QtCore.Signal()

    def __init__(self, items, title, docstring, parent=None):
        QtWidgets.QDialog.__init__(self)
        self.parent = parent
        self.setWindowTitle(title)
        self.formlayout = QtWidgets.QFormLayout()
        self.formlayout.setLabelAlignment(QtCore.Qt.AlignRight)
        self.docstring = None
        self.items = items
        self.setupitems()
        self.connectToChangeSignal()
        self.bbox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        self.bbox.accepted.connect(self.accept)
        self.bbox.rejected.connect(self.reject)
        self._init_docstring(docstring)
        self.layout = QtWidgets.QVBoxLayout()
        if docstring is not None:
            self.layout.addWidget(self.docstring)
        self.layout.addLayout(self.formlayout)
        self.layout.addWidget(self.bbox)
        self.setLayout(self.layout)
        self.changeSignal.connect(self.updateValues)
        self.updateValues()

    def _init_docstring(self, docstring):
        if docstring is None:
            return None
        self.docstring = QtWidgets.QTextBrowser()
        self.docstring.setOpenExternalLinks(True)
        docstring = markdown.markdown(docstring)
        self.docstring.setHtml(docstring)
        # css = """ """
        # self.docstring.setStyleSheet(css)
        self.docstring.setWordWrapMode(QtGui.QTextOption.NoWrap)

    def setupitems(self):
        for item in self.items:
            self.formlayout.addRow(item['string'], item['object'])
        # Get the old vals from settings
        if self.parent is not None:
            name = self.parent.__name__
            if g.settings['baseprocesses'] is None:
                g.settings['baseprocesses'] = dict()
            if name not in g.settings['baseprocesses']:
                settings = self.parent.get_init_settings_dict()
                g.settings['baseprocesses'][name] = settings
            else:
                settings = g.settings['baseprocesses'][name]
            for item in self.items:
                if item['name'] in settings and not isinstance(item['object'], WindowSelector):
                    item['object'].setValue(settings[item['name']])

    def connectToChangeSignal(self):
        for item in self.items:
            methods = [method for method in dir(item['object']) if callable(
                getattr(item['object'], method))]
            if 'valueChanged' in methods:
                item['object'].valueChanged.connect(self.changeSignal)
            elif 'stateChanged' in methods:
                item['object'].stateChanged.connect(self.changeSignal)
            elif 'currentIndexChanged' in methods:
                item['object'].currentIndexChanged.connect(self.changeSignal)

    def updateValues(self):  # copy values from gui into the 'item' dictionary
        for item in self.items:
            methods = [method for method in dir(item['object']) if callable(
                getattr(item['object'], method))]
            if 'value' in methods:
                item['value'] = item['object'].value()
            elif 'currentText' in methods:
                item['value'] = item['object'].currentText()
            elif 'isChecked' in methods:
                item['value'] = item['object'].isChecked()

    def closeEvent(self, ev):
        self.closeSignal.emit()


def convert_to_string(item):
    if isinstance(item, str):
        return "'{}'".format(item)
    else:
        return str(item)


class BaseProcess(object):
    """BaseProcess(object)
    Foundation for all flika processes. Subclass BaseProcess when writing your own process.

    Attributes:
        items: list of significant values unique to each BaseProcess subclass


    """

    def __init__(self):
        self.noPriorWindow = False
        self.__name__ = self.__class__.__name__.lower()
        self.items = []

    def getValue(self, name):
        '''getValue(self,name)

        Returns:
            The value of a the name stored in self.items

        '''
        return [i['value'] for i in self.items if i['name'] == name][0]

    def get_init_settings_dict(self):
        '''get_init_settings_dict(self)
        Function for storing the intial settings of any BaseProcess into self.items

        Note:
            In most cases when writing a BaseProcess subclass, this function must be overloaded

        Returns:
            A dictionary containing the initial settings and their values

                '''
        return dict()  # this function needs to be overwritten by every subclass

    def start(self, keepSourceWindow):
        frame = inspect.getouterframes(inspect.currentframe())[1][0]
        args, _, _, values = inspect.getargvalues(frame)
        funcname = self.__name__
        self.command = funcname + \
            '('+', '.join([i+'='+convert_to_string(values[i])
                           for i in args if i != 'self'])+')'
        g.m.statusBar().showMessage('Running function {}...'.format(self.__name__))
        self.keepSourceWindow = keepSourceWindow
        self.oldwindow = g.win
        if self.oldwindow is None:
            raise (MissingWindowError(
                "You cannot execute '{}' without selecting a window first.".format(self.__name__)))
        self.tif = self.oldwindow.image
        self.oldname = self.oldwindow.name

    def end(self):
        from .. import window
        if not hasattr(self, 'newtif') or self.newtif is None:
            self.oldwindow.reset()
            return
        commands = self.oldwindow.commands[:]
        if hasattr(self, 'command'):
            commands.append(self.command)
        newWindow = window.Window(self.newtif, str(
            self.newname), self.oldwindow.filename, commands, self.oldwindow.metadata)
        if self.keepSourceWindow is False:
            self.oldwindow.close()
        else:
            self.oldwindow.reset()
        if np.max(self.newtif) == 1 and np.min(self.newtif) == 0:  # if the array is boolean
            newWindow.imageview.setLevels(-.1, 1.1)
        g.m.statusBar().showMessage('Finished with {}.'.format(self.__name__))
        del self.tif
        del self.newtif
        return newWindow

    def gui(self):
        from pyqtgraph import SignalProxy
        self.ui = BaseDialog(self.items, self.__name__, self.__doc__, self)
        if hasattr(self, '__url__'):
            self.ui.bbox.addButton(QtWidgets.QDialogButtonBox.Help)
            self.ui.bbox.helpRequested.connect(
                lambda: QtWidgets.QDesktopServices.openUrl(QtCore.QUrl(self.__url__)))
        self.proxy = SignalProxy(self.ui.changeSignal,
                                 rateLimit=60, slot=self.preview)
        if g.win is not None:
            self.ui.rejected.connect(g.win.reset)
        self.ui.closeSignal.connect(self.ui.rejected.emit)
        self.ui.accepted.connect(self.call_from_gui)
        self.ui.resize(750, 450)
        self.ui.show()
        g.dialogs.append(self.ui)
        return True

    def gui_reset(self):
        self.items = []

    def call_from_gui(self):
        from .. import window
        varnames = [i for i in inspect.getfullargspec(
            self.__call__)[0] if i != 'self' and i != 'keepSourceWindow']
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
            if not isinstance(value, window.Window):
                newsettings[name] = value
        g.settings['baseprocesses'][self.__name__] = newsettings
        g.settings.save()
        try:
            if self.noPriorWindow:
                self.__call__(*args)
            else:
                self.__call__(*args, keepSourceWindow=True)
        except MemoryError as err:
            msg = 'There was a memory error in {}. Close other programs and try again.'.format(
                self.__name__)
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
        self.command = funcname + \
            '('+', '.join([i+'='+convert_to_string(values[i])
                           for i in args if i != 'self'])+')'
        g.m.statusBar().showMessage('Performing {}...'.format(self.__name__))

    def end(self):
        from .. import window
        commands = [self.command]
        newWindow = window.Window(self.newtif, str(
            self.newname), commands=commands)
        if np.max(self.newtif) == 1 and np.min(self.newtif) == 0:  # if the array is boolean
            newWindow.imageview.setLevels(-.1, 1.1)
        g.m.statusBar().showMessage('Finished with {}.'.format(self.__name__))
        del self.newtif
        return newWindow


logger.debug("Completed 'reading process/BaseProcess.py'")
