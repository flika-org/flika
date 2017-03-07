from __future__ import absolute_import, division, print_function

import sys, os, time
from qtpy import QtCore, QtWidgets, QtGui
from flika.utils import nonpartial, get_qapp

from flika.process import setup_menus
from flika.app.settings_editor import SettingsEditor, rectSettings, pointSettings
from flika.process.file_ import *

import flika.global_vars as g
from flika.app.plugin_manager import PluginManager, load_local_plugins
from flika.app.terminal_widget import ScriptEditor
from flika.core import tifffile
from flika.utils import load_ui
from flika.images import image_path
from flika.roi import load_rois

from flika.logger import logger

def addMenuItem(menu, label, item):
    if type(item) == QtWidgets.QMenu:
        menu.addMenu(item)
    elif type(item) == QtWidgets.QAction:
        menu.addAction(item)
    elif type(item) == type(menu):
        if len(item) == 0:
            return
        submenu = menu.addMenu(label)
        for itemName, itemMenu in item:
            addMenuItem(submenu, itemName, itemMenu)
    else:
        action = menu.addAction(label)
        action.triggered.connect(item)

def status_pixmap(attention=False):
    """
    A small icon to grab attention
    :param attention: If True, return attention-grabbing pixmap
    """
    color = QtCore.Qt.red if attention else QtCore.Qt.lightGray

    pm = QtGui.QPixmap(15, 15)
    p = QtGui.QPainter(pm)
    b = QtGui.QBrush(color)
    p.fillRect(-1, -1, 20, 20, b)
    return pm

class ClickableLabel(QtWidgets.QLabel):
    """
    A QtGui.QLabel you can click on to generate events
    """

    clicked = QtCore.Signal()

    def mousePressEvent(self, event):
        self.clicked.emit()

class XStream(QtCore.QObject):
    _stderr = None

    messageWritten = QtCore.Signal(str)

    def flush( self ):
        pass

    def fileno( self ):
        return -1

    def write( self, msg ):
        if ( not self.signalsBlocked() ):
            self.messageWritten.emit(msg)

    @staticmethod
    def stderr():
        if ( not XStream._stderr ):
            XStream._stderr = XStream()
            sys.stderr = XStream._stderr
        return XStream._stderr

class Logger(QtWidgets.QWidget):

    """
    A window to display error messages
    """

    def __init__(self, parent=None):
        super(Logger, self).__init__(parent)
        self._text = QtWidgets.QTextEdit()
        self._text.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)

        clear = QtWidgets.QPushButton("Clear")
        clear.clicked.connect(nonpartial(self._clear))

        report = QtWidgets.QPushButton("Send Bug Report")
        report.clicked.connect(nonpartial(self._send_report))

        XStream.stderr().messageWritten.connect( self.write )

        self._status = ClickableLabel()
        self._status.setToolTip("View Errors and Warnings")
        self._status.clicked.connect(self._show)
        self._status.setPixmap(status_pixmap())
        self._status.setContentsMargins(0, 0, 0, 0)

        l = QtWidgets.QVBoxLayout()
        h = QtWidgets.QHBoxLayout()
        l.setContentsMargins(2, 2, 2, 2)
        l.setSpacing(2)
        h.setContentsMargins(0, 0, 0, 0)

        l.addWidget(self._text)
        h.insertStretch(0)
        h.addWidget(report)
        h.addWidget(clear)
        l.addLayout(h)

        self.setLayout(l)

    @property
    def status_light(self):
        """
        The icon representing the status of the log
        """
        return self._status

    def write(self, message):
        """
        Interface for sys.excepthook
        """
        logger.info(message)
        print(message, end='')
        self._text.insertPlainText(message)
        self._status.setPixmap(status_pixmap(attention=True))

    def flush(self):
        """
        Interface for sys.excepthook
        """
        pass

    def _send_report(self):
        """
        Send the contents of the log as a bug report
        """
        text = self._text.document().toPlainText()
        print('Error Log:\n' + text)

    def _clear(self):
        """
        Erase the log
        """
        self._text.setText('')
        self._status.setPixmap(status_pixmap(attention=False))
        self.close()

    def _show(self):
        """
        Show the log
        """
        self.show()
        self.raise_()

    def keyPressEvent(self, event):
        """
        Hide window on escape key
        """
        if event.key() == QtCore.Qt.Key_Escape:
            self.hide()


class FlikaApplication(QtWidgets.QMainWindow):
    def __init__(self):
        print('Launching Flika')
        self.app = get_qapp()
        super(FlikaApplication, self).__init__()
        self.app.setQuitOnLastWindowClosed(True)
        setup_menus()
        
        load_ui('main.ui', self, directory=os.path.dirname(__file__))

        g.m = self
        g.settings = g.Settings()
        
        desktop = QtWidgets.QApplication.desktop()
        width_px=int(desktop.logicalDpiX()*3.4)
        height_px=int(desktop.logicalDpiY()*.9)
        self.setGeometry(QtCore.QRect(15, 33, width_px, height_px))
        #self.setFixedSize(326, 80)
        self.setMaximumSize(width_px*3, 120)
        self.setWindowIcon(QtGui.QIcon(image_path('favicon.png')))
        self._make_menu()
        self._make_tools()


        self._log = Logger()
        self._log.window().setWindowTitle("Console Log")
        self._log.resize(550, 550)

        self.statusBar().addPermanentWidget(self._log.status_light)
        self.statusBar().setContentsMargins(2, 0, 20, 2)
        self.statusBar().setSizeGripEnabled(False)
        self.setCurrentWindowSignal = SetCurrentWindowSignal(self)
        self.setAcceptDrops(True)
        
        load_local_plugins()

    def start(self):
        self.show()
        self.raise_()
        return self.app.exec_()

    def _make_menu(self):
        fileMenu = self.menuBar().addMenu('File')
        openAction = fileMenu.addAction("Open File", open_file_from_gui)
        
        self.recentFileMenu = fileMenu.addMenu('Recent Files')
        self.recentFileMenu.aboutToShow.connect(self._make_recents)
        self.recentFileMenu.triggered.connect(lambda a: open_file(a.text()))

        fileMenu.addAction("Save As", save_window)
        importMenu = fileMenu.addMenu("Import")
        exportMenu = fileMenu.addMenu("Export")
        importMenu.addAction("Import ROIs", load_rois)
        importMenu.addAction("Import Points", load_points)
        exportMenu.addAction("Export Movie", export_movie_gui)
        exportMenu.addAction("Export Points", save_points)

        fileMenu.addAction("Settings", SettingsEditor.show)
        fileMenu.addAction("&Quit", self.close)#app.quit)

        for menu in g.menus:
            self.menuBar().addMenu(menu)

        self.pluginMenu = self.menuBar().addMenu('Plugins')
        self.pluginMenu.aboutToShow.connect(self._make_plugin_menu)

        helpMenu = self.menuBar().addMenu("Help")
        url='http://flika-org.github.io/documentation.html'
        helpMenu.addAction("Documentation", lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl(url)))
        helpMenu.addAction("Check For Updates", g.checkUpdates)

    def __getattr__(self, item):
        if item in self.__dict__:
            return self.__dict__[item]
        elif item in g.__dict__:
            return g.__dict__[item]
        raise AttributeError(item)


    def _make_tools(self):
        self.freehand.clicked.connect(lambda: g.settings.__setitem__('mousemode', 'freehand'))
        self.line.clicked.connect(lambda: g.settings.__setitem__('mousemode', 'line'))
        self.rect_line.clicked.connect(lambda: g.settings.__setitem__('mousemode', 'rect_line'))
        self.rectangle.clicked.connect(lambda: g.settings.__setitem__('mousemode', 'rectangle'))
        self.point.clicked.connect(lambda: g.settings.__setitem__('mousemode', 'point'))
        self.mouse.clicked.connect(lambda: g.settings.__setitem__('mousemode', 'mouse'))

        self.point.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.point.customContextMenuRequested.connect(pointSettings)
        self.rectangle.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.rectangle.customContextMenuRequested.connect(rectSettings)

    def _make_plugin_menu(self):
        self.pluginMenu.clear()
        self.pluginMenu.addAction('Plugin Manager', PluginManager.show)
        self.pluginMenu.addAction('Script Editor', ScriptEditor.show)
        self.pluginMenu.addSeparator()

        for plugin in PluginManager.plugins.values():
            if plugin.installed and plugin.menu:
                addMenuItem(self.pluginMenu, plugin.name, plugin.menu)

    def _make_recents(self):
        self.recentFileMenu.clear()
        g.settings['recent_files'] = [f for f in g.settings['recent_files'] if os.path.exists(f)]
        if len(g.settings['recent_files']) == 0:
            noAction = QtWidgets.QAction('No Recent Files', self.recentFileMenu)
            noAction.setEnabled(False)
            self.recentFileMenu.addAction(noAction)
        else:
            for name in g.settings['recent_files'][::-1]:
                self.recentFileMenu.addAction(name)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()   # must accept the dragEnterEvent or else the dropEvent can't occur !!!
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():   # if file or link is dropped
            for url in event.mimeData().urls():
                filename=url.toString()
                filename=str(filename)
                filename=filename.split('file:///')[1]
                print('filename={}'.format(filename))
                open_file(filename)  # This fails on windows symbolic links.  http://stackoverflow.com/questions/15258506/os-path-islink-on-windows-with-python
                event.accept()
        else:
            event.ignore()

    def clear(self):
        while g.dialogs:
            g.dialogs.pop(0).close()
        while g.traceWindows:
            g.traceWindows.pop(0).close()
        while g.windows:
            g.windows.pop(0).close()

    def closeEvent(self, event):
        print('Closing Flika')
        event.accept()
        for win in g.dialogs[:] + g.traceWindows[:] + g.windows[:]:
            win.close()

        ScriptEditor.close()
        PluginManager.close()
        g.settings.save()

class SetCurrentWindowSignal(QtWidgets.QWidget):
    sig=QtCore.Signal()

    def __init__(self,parent):
        super(SetCurrentWindowSignal, self).__init__(parent)
        self.hide()