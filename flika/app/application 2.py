from ..logger import logger, handle_exception
logger.debug("Started 'reading app/application.py'")

import sys, os, time
import ctypes
import platform
import traceback
logger.debug("Started 'reading app/application.py, importing qtpy'")
from qtpy import QtCore, QtWidgets, QtGui
logger.debug("Completed 'reading app/application.py, importing qtpy'")

from ..utils.misc import nonpartial
from ..utils.app import get_qapp
from ..app.settings_editor import SettingsEditor, rectSettings, pointSettings, pencilSettings
from .. import global_vars as g
from .plugin_manager import PluginManager, Load_Local_Plugins_Thread
from .script_editor import ScriptEditor
from ..utils.misc import load_ui, send_error_report, Send_User_Stats_Thread
from ..images import image_path
from ..version import __version__
from ..update_flika import checkUpdates


def status_pixmap(attention=False):
    """status_pixmap(attention=False)
    A small icon to grab attention

    Args:
        attention (bool): pixmap is red if True, gray if otherwise

    Returns:
        QtGui.QPixmap: attention icon to display
    """
    color = QtCore.Qt.red if attention else QtCore.Qt.lightGray

    pm = QtGui.QPixmap(15, 15)
    p = QtGui.QPainter(pm)
    b = QtGui.QBrush(color)
    p.fillRect(-1, -1, 20, 20, b)
    return pm


class ClickableLabel(QtWidgets.QLabel):
    """A QtGui.QLabel you can click on to generate events
    """

    clicked = QtCore.Signal()

    def mousePressEvent(self, event):
        self.clicked.emit()


class Logger(QtWidgets.QWidget):
    """A window to display error messages
    """

    def __init__(self, parent=None):
        super(Logger, self).__init__(parent)
        self._text = QtWidgets.QTextEdit()
        self._text.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        clear = QtWidgets.QPushButton("Clear")
        clear.clicked.connect(nonpartial(self._clear))
        report = QtWidgets.QPushButton("Send Bug Report")
        report.clicked.connect(nonpartial(self._send_report))
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
        """status_light(self)

        Returns:
            The icon representing the status of the log
        """
        return self._status

    def write(self, message):
        """write(self, message)
        Interface for sys.excepthook
        """
        self._text.insertPlainText(message)
        self._status.setPixmap(status_pixmap(attention=True))

    def flush(self):
        """flush(self)
        Interface for sys.excepthook
        """
        pass

    def _send_report(self):
        """_send_report(self)
        Send the contents of the log as a bug report
        """
        text = self._text.document().toPlainText()
        email = QtWidgets.QInputDialog.getText(self, "Response email", "Enter your email if you would like us to contact you about this bug.")
        if isinstance(email, tuple) and len(email) == 2:
            email = email[0]
        response = send_error_report(email=email, report=text)
        if response is None or response.status_code != 200:
            g.alert("Failed to send error report. Response {}:\n{}".format((response.status_code, response._content)))
        else:
            if email != '':
                g.alert("Bug report sent. We will contact you as soon as we can.")
            else:
                g.alert("Bug report sent. Thank you!")

    def _clear(self):
        """_clear(self)
        Erase the log
        """
        self._text.setText('')
        self._status.setPixmap(status_pixmap(attention=False))
        self.close()

    def _show(self):
        """_show(self)
        Show the log
        """
        self.show()
        self.raise_()

    def keyPressEvent(self, event):
        """keyPressEvent(self, event)
        Hide window on escape key
        """
        if event.key() == QtCore.Qt.Key_Escape:
            self.hide()



class FlikaApplication(QtWidgets.QMainWindow):
    """The main window of flika, stored as g.m
    """
    def __init__(self):
        logger.debug("Started 'creating app.application.FlikaApplication'")
        from ..process.file_ import open_file, open_file_from_gui, open_image_sequence_from_gui, open_points, save_file, save_movie_gui, save_points, save_rois
        from ..process import setup_menus
        logger.debug("Started 'creating app.application.FlikaApplication.app'")
        self.app = get_qapp(image_path('favicon.png'))
        logger.debug("Completed 'creating app.application.FlikaApplication.app'")
        super(FlikaApplication, self).__init__()
        self.app.setQuitOnLastWindowClosed(True)
        setup_menus()
        logger.debug("Started 'loading main.ui'")
        load_ui('main.ui', self, directory=os.path.dirname(__file__))
        logger.debug("Completed 'loading main.ui'")

        g.m = self
        # These are all added for backwards compatibility for plugins
        self.windows = g.windows
        self.traceWindows = g.traceWindows
        self.dialogs = g.dialogs
        self.currentWindow = g.win
        self.currentTrace = g.currentTrace
        self.clipboard = g.clipboard
        self.setWindowSize()
        if platform.system() == 'Windows':
            myappid = 'flika-org.flika.' + str(__version__)
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        self.menuBar().setNativeMenuBar(False)
        self._make_menu()
        self._make_tools()

        self._log = Logger()
        def handle_exception_wrapper(exc_type, exc_value, exc_traceback):
            handle_exception(exc_type, exc_value, exc_traceback)
            tb_str = traceback.format_exception(exc_type, exc_value, exc_traceback)
            tb_str = ''.join(tb_str)+'\n'
            self._log.write(tb_str)
        sys.excepthook = handle_exception_wrapper

        g.dialogs.append(self._log)
        self._log.window().setWindowTitle("Console Log")
        self._log.resize(550, 550)

        self.statusBar().addPermanentWidget(self._log.status_light)
        self.statusBar().setContentsMargins(2, 0, 20, 2)
        self.statusBar().setSizeGripEnabled(False)
        self.setCurrentWindowSignal = SetCurrentWindowSignal(self)
        self.setAcceptDrops(True)
        self.load_local_plugins_thread = Load_Local_Plugins_Thread()
        self.load_local_plugins_thread.start()
        self.load_local_plugins_thread.plugins_done_sig.connect(self.plugins_done)
        self.load_local_plugins_thread.error_loading.connect(g.alert)
        logger.debug("Completed 'creating app.application.FlikaApplication'")

    def plugins_done(self, plugins):
        for p in plugins.values():
            if p.loaded:
                p.bind_menu_and_methods()
        PluginManager.plugins = plugins

    def start(self):
        logger.debug("Started 'app.application.FlikaApplication.start()'")
        self.show()
        self.raise_()
        QtWidgets.qApp.processEvents()
        logger.debug("Started 'app.application.FlikaApplication.send_user_stats()'")
        self.send_user_stats_thread = Send_User_Stats_Thread()
        self.send_user_stats_thread.start()
        logger.debug("Completed 'app.application.FlikaApplication.send_user_stats()'")
        logger.debug("Completed 'app.application.FlikaApplication.start()'")
        #if 'PYCHARM_HOSTED' not in os.environ and 'SPYDER_SHELL_ID' not in os.environ:
        #    return self.app.exec_()

    def setWindowSize(self):
        #desktop = QtWidgets.QApplication.desktop()
        #width_px=int(desktop.logicalDpiX()*3.4)
        #height_px=int(desktop.logicalDpiY()*.9)
        #self.setGeometry(QtCore.QRect(15, 33, width_px, height_px))
        #self.setFixedSize(326, 80)
        #self.setMaximumSize(width_px*3, 120)
        self.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum);
        self.move(0, 0)

    def _make_menu(self):
        logger.debug("Started 'app.application.FlikaApplication._make_menu()'")
        from ..roi import open_rois
        from ..process.file_ import open_file, open_file_from_gui, open_image_sequence_from_gui, open_points, save_file, save_movie_gui, save_points, save_rois
        fileMenu = self.menuBar().addMenu('File')
        openMenu = fileMenu.addMenu("Open")
        openMenu.addAction("Open Image/Movie", open_file_from_gui)
        openMenu.addAction("Open Image Sequence", open_image_sequence_from_gui)
        openMenu.addAction("Open ROIs", open_rois)
        openMenu.addAction("Open Points", open_points)
        self.recentFileMenu = fileMenu.addMenu('Recent Files')
        self.recentFileMenu.aboutToShow.connect(self._make_recents)
        self.recentFileMenu.triggered.connect(lambda a: open_file(a.text()))
        saveMenu = fileMenu.addMenu("Save")
        saveMenu.addAction("Save Image", save_file)
        saveMenu.addAction("Save Movie (.mp4)", save_movie_gui)
        saveMenu.addAction("Save Points", save_points)
        saveMenu.addAction("Save All ROIs", save_rois)

        fileMenu.addAction("Settings", SettingsEditor.show)
        fileMenu.addAction("&Quit", self.close)#app.quit)


        for menu in g.menus:
            self.menuBar().addMenu(menu)

        self.pluginMenu = self.menuBar().addMenu('Plugins')
        self.pluginMenu.aboutToShow.connect(self._make_plugin_menu)

        self.scriptMenu = self.menuBar().addMenu('Scripts')
        self.scriptMenu.aboutToShow.connect(self._make_script_menu)

        helpMenu = self.menuBar().addMenu("Help")
        url = 'http://flika-org.github.io'
        helpMenu.addAction("Documentation", lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl(url)))
        helpMenu.addAction("Check For Updates", checkUpdates)
        logger.debug("Completed 'app.application.FlikaApplication._make_menu()'")

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
        self.pencil.clicked.connect(lambda: g.settings.__setitem__('mousemode', 'pencil'))
        self.rectangle.clicked.connect(lambda: g.settings.__setitem__('mousemode', 'rectangle'))
        self.point.clicked.connect(lambda: g.settings.__setitem__('mousemode', 'point'))
        self.mouse.clicked.connect(lambda: g.settings.__setitem__('mousemode', 'mouse'))

        self.point.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.point.customContextMenuRequested.connect(pointSettings)
        self.pencil.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.pencil.customContextMenuRequested.connect(pencilSettings)
        self.rectangle.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.rectangle.customContextMenuRequested.connect(rectSettings)

    def _make_script_menu(self):
        logger.debug('Making script editor')
        self.scriptMenu.clear()
        self.scriptEditorAction = self.scriptMenu.addAction('Script Editor', ScriptEditor.show)
        self.scriptMenu.addSeparator()
        def openScript(script):
            return lambda : ScriptEditor.importScript(script)
        for recent_script in g.settings['recent_scripts']:
            self.scriptMenu.addAction(recent_script, openScript(recent_script))
        logger.debug('Script editor complete')

    def _make_plugin_menu(self):
        logger.debug('Making Plugin Manager')
        self.pluginMenu.clear()
        self.pluginMenu.addAction('Plugin Manager', PluginManager.show)
        self.pluginMenu.addSeparator()
        logger.debug('Plugin Manager complete')

        installedPlugins = [plugin for plugin in PluginManager.plugins.values() if plugin.installed]
        for plugin in sorted(installedPlugins, key=lambda a: -a.lastModified()):
            if isinstance(plugin.menu, QtWidgets.QMenu):
                self.pluginMenu.addMenu(plugin.menu)

    def _make_recents(self):
        logger.debug('Making recent files')
        self.recentFileMenu.clear()
        g.settings['recent_files'] = [f for f in g.settings['recent_files'] if os.path.exists(f)]
        if len(g.settings['recent_files']) == 0:
            noAction = QtWidgets.QAction('No Recent Files', self.recentFileMenu)
            noAction.setEnabled(False)
            self.recentFileMenu.addAction(noAction)
        else:
            for name in g.settings['recent_files'][::-1]:
                if isinstance(name, str) and os.path.exists(name):
                    self.recentFileMenu.addAction(name)
        logger.debug('Recent files complete')

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()   # must accept the dragEnterEvent or else the dropEvent can't occur !!!
        else:
            event.ignore()

    def dropEvent(self, event):
        from ..process.file_ import open_file
        if event.mimeData().hasUrls():   # if file or link is dropped
            for url in event.mimeData().urls():
                filename = url.toLocalFile()
                filename = str(filename)
                #if platform.system() == 'Windows':
                #    filename = filename.split('file:///')[1]
                #else:
                #    filename = filename.split('file://')[1]
                print("filename = '{}'".format(filename))
                open_file(filename)  # This fails on windows symbolic links.  http://stackoverflow.com/questions/15258506/os-path-islink-on-windows-with-python
                event.accept()
        else:
            event.ignore()

    def clear(self):
        """clear(self)
        Close all dialogs, trace windows, and windows
        """
        while g.dialogs:
            g.dialogs.pop(0).close()
        while g.traceWindows:
            g.traceWindows.pop(0).close()
        while g.windows:
            g.windows.pop(0).close()

    def closeEvent(self, event):
        """closeEvent(self, event)
        Close all widgets and exit flika
        """
        print('Closing flika')
        event.accept()
        ScriptEditor.close()
        PluginManager.close()
        self.clear()
        g.settings.save()
        if g.m == self:
            g.m = None

class SetCurrentWindowSignal(QtWidgets.QWidget):
    sig=QtCore.Signal()

    def __init__(self,parent):
        super(SetCurrentWindowSignal, self).__init__(parent)
        self.hide()
logger.debug("Completed 'reading app/application.py'")