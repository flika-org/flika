# -*- coding: utf-8 -*-
from ..logger import logger
logger.debug("Started 'reading app/script_editor.py'")
from qtpy import QtGui, QtCore, QtWidgets, uic
import os

from .. import global_vars as g
from .syntax import PythonHighlighter
from ..utils.misc import save_file_gui, open_file_gui, load_ui

MESSAGE_TIME = 2000
try:
    __IPYTHON__
except NameError:
    INSIDE_IPYTHON = False
else:
    INSIDE_IPYTHON = True

def qstr2str(string):
    string=str(string)
    return string.replace(u'\u2029','\n').strip()

class Editor(QtWidgets.QPlainTextEdit):
    def __init__(self, scriptfile = ''):
        super(Editor, self).__init__()
        self.highlight = PythonHighlighter(self.document())
        self.scriptfile = ''
        if scriptfile != '':
            self.open_file(scriptfile)
        font = QtGui.QFont()
        font.setFamily("Courier")
        font.setStyleHint(QtGui.QFont.Monospace)
        font.setFixedPitch(True)
        font.setPointSize(ScriptEditor.POINT_SIZE)

        self.setFont(font)

        metrics = QtGui.QFontMetrics(font)
        self.setTabStopWidth(4 * metrics.width(' '))

    @staticmethod
    def fromWindow(window):
        if window is None:
            g.alert("In order to load a script from a window, you need to have a window selected.")
            return None
        editor = Editor()
        editor.setPlainText('\n'.join(window.commands))
        return editor
        
    def open_file(self, scriptfile):
        self.scriptfile = scriptfile
        try:
            script = open(scriptfile, 'r').read()
        except FileNotFoundError as e:
            print("Failed to read %s: %s" % (scriptfile, e))
            return
        self.setPlainText(script)
        ScriptEditor.gui.statusBar().showMessage('{} opened.'.format(os.path.basename(self.scriptfile)), MESSAGE_TIME)

    def save_as(self):
        filename = save_file_gui('Save script', ScriptEditor.most_recent_script(), '*.py')
        if filename == '':
            ScriptEditor.gui.statusBar().showMessage('Save cancelled',  MESSAGE_TIME)
            return False
        self.scriptfile = filename
        self.save()
        return True

    def save(self):
        if not self.scriptfile:
            return self.save_as()
        f = open(self.scriptfile, 'w')
        command=qstr2str(self.toPlainText())
        f.write(command)
        f.close()
        ScriptEditor.add_recent_file(self.scriptfile)
        ScriptEditor.gui.statusBar().showMessage('{} saved.'.format(os.path.basename(self.scriptfile)), MESSAGE_TIME)
        return True

class ScriptEditor(QtWidgets.QMainWindow):
    '''
    QMainWindow for editing and running user scripts. Comprised of a tabbed text editor and console.
    '''
    POINT_SIZE = 8
    def __init__(self, parent=None, ):
        from .terminal import ipython_terminal
        from .script_namespace import getnamespace
        super(ScriptEditor, self).__init__(parent)
        load_ui('ipythonWidget.ui', self, directory=os.path.dirname(__file__))
        text = """Predefined Libraries:
    scipy and numpy (np)
Useful variables:
    g.m.windows - list of windows.
    g.win - the selected window
    g.win.rois -list of rois in that window
    - roi.getTrace() gets an roi trace as an array
    clear() to clear the console 
    reset() to reset all global and local variables """

        self.terminal = ipython_terminal(banner=text, **getnamespace())
        self.terminal.namespace.update({'clear': self.terminal.clear, 'reset': self.resetNamespace})
        layout = QtWidgets.QGridLayout()
        self.terminalWidget.setLayout(layout)
        layout.addWidget(self.terminal)
        self.addEditor()
        self.saveButton.clicked.connect(self.saveCurrentScript)
        self.runButton.clicked.connect(self.runScript)
        self.runSelectedButton.clicked.connect(self.runSelected)
        self.actionNew_Script.triggered.connect(lambda f: self.addEditor())
        self.actionFrom_File.triggered.connect(lambda f: ScriptEditor.importScript())
        self.actionFrom_Window.triggered.connect(lambda : self.addEditor(Editor.fromWindow(g.win)))
        self.actionSave_Script.triggered.connect(self.saveCurrentScript)
        self.menuRecentScripts.aboutToShow.connect(self.open_scripts)
        self.actionChangeFontSize.triggered.connect(self.changeFontSize)
        #self.eventeater = ScriptEventEater(self)
        self.setAcceptDrops(True)
        #self.installEventFilter(self.eventeater)
        self.scriptTabs.tabCloseRequested.connect(self.closeTab)
        self.setWindowTitle('Script Editor')

        
    def resetNamespace(self):
        self.terminal.shell.reset()
        self.terminal.shell.user_ns.update(getnamespace())
        self.terminal.namespace.update({'clear': self.terminal.clear, 'reset': self.resetNamespace})

    def changeFontSize(self):
        val, ok = QtWidgets.QInputDialog.getInt(self, "Change Font Size", "Font Size", \
            value=ScriptEditor.POINT_SIZE, min = 6, max = 50, step = 1)
        if ok:
            self.setFontSize(val)

    def setFontSize(self, val):
        ScriptEditor.POINT_SIZE = val

        font = self.scriptTabs.font()
        font.setPointSize(val)
        self.scriptTabs.setFont(font)

        f = self.terminal._control.font()
        f.setPointSize(val)
        self.terminal._control.setFont(f)

        for ch in self.scriptTabs.children():
            if isinstance(ch, QtWidgets.QStackedWidget):
                for i in range(ch.count()):
                    f = ch.widget(i).font()
                    f.setPointSize(val)
                    ch.widget(i).setFont(f)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            filename=url.toString()
            filename=filename.split('file:///')[1]
            print('filename={}'.format(filename))
            ScriptEditor.importScript(filename)

        event.accept()

    def open_scripts(self):
        self.menuRecentScripts.clear()
        def makeFun(script):
            return lambda: ScriptEditor.importScript(script)
        if len(g.settings['recent_scripts']) == 0:
            action = QtWidgets.QAction("No Recent Scripts", self)
            action.setEnabled(False)
            self.menuRecentScripts.addAction(action)
        else:
            for filename in g.settings['recent_scripts']:
                if not os.path.exists(filename):
                    g.settings['recent_scripts'].remove(filename)
                    continue
                action = QtWidgets.QAction(filename, self, triggered=makeFun(filename))
                self.menuRecentScripts.addAction(action)

    def closeTab(self, index):
        self.scriptTabs.removeTab(index)

    def saveCurrentScript(self):
        cw = self.currentTab()
        if cw == None:
            return
        if cw.save():
            self.scriptTabs.setTabText(self.scriptTabs.currentIndex(), os.path.basename(cw.scriptfile))

    def currentTab(self):
        return self.scriptTabs.currentWidget()

    @staticmethod
    def most_recent_script():
        return g.settings['recent_scripts'][-1] if len(g.settings['recent_scripts']) > 0 else ''

    @staticmethod
    def add_recent_file(filename):
        filename = os.path.abspath(filename)
        if not os.path.exists(filename):
            return
        if filename in g.settings['recent_scripts']:
            g.settings['recent_scripts'].remove(filename)
        g.settings['recent_scripts'].insert(0, filename)
        if len(g.settings['recent_scripts']) > 8:
            g.settings['recent_scripts'] = g.settings['recent_scripts'][:-1]
        g.settings.save()

    @staticmethod
    def importScript(scriptfile = ''):
        if not hasattr(ScriptEditor, 'gui') or not ScriptEditor.gui.isVisible():
            ScriptEditor.show()
        if scriptfile == '':
            prompt = "Open script"
            directory = os.path.dirname(ScriptEditor.most_recent_script())
            filetypes = '*.py'
            scriptfile = open_file_gui(prompt, directory, filetypes)
            if scriptfile is None:
                return None
        if hasattr(ScriptEditor, 'gui'):
            editor = Editor(scriptfile)
            ScriptEditor.add_recent_file(scriptfile)
            ScriptEditor.gui.addEditor(editor)
    
    def addEditor(self, editor=None):
        self.setUpdatesEnabled(False)
        if editor is None:
            editor = Editor()
        if editor.scriptfile == '':
            name = 'New Script'
        else:
            name = editor.scriptfile
        editor.keyPressEvent = lambda ev: self.editorKeyPressEvent(editor, ev)
        self.scriptTabs.insertTab(0, editor, os.path.basename(name))
        self.scriptTabs.setCurrentIndex(0)
        self.setUpdatesEnabled(True)

        return editor

    def keyPressEvent(self, ev):
        if ev.modifiers() == QtCore.Qt.ControlModifier:
            if ev.key() == QtCore.Qt.Key_N:
                self.addEditor()
                ev.accept()
            elif ev.key() == QtCore.Qt.Key_S:
                self.saveCurrentScript()

    def editorKeyPressEvent(self, editor, ev):
        if ev.key() == QtCore.Qt.Key_F9:
            self.runSelected()
            ev.accept()
        else:
            Editor.keyPressEvent(editor, ev)

    def runScript(self):
        if self.currentTab() == None:
            return
        command=qstr2str(self.currentTab().toPlainText())
        if command:
            self.terminal.execute(command)

    def runSelected(self):
        if self.currentTab() == None:
            return
        cursor=self.currentTab().textCursor()
        command=cursor.selectedText()
        self.command=command
        command=qstr2str(command)
        if command:
            self.terminal.execute(command)

    @staticmethod
    def show():
        if 'PYCHARM_HOSTED' in os.environ:
            g.alert('You cannot run the script editor from within PyCharm.')
        elif INSIDE_IPYTHON:
            g.alert('You cannot run the script editor because flika is already running inside IPython.')
        else:
            if not hasattr(ScriptEditor, 'gui'):
                ScriptEditor.gui = ScriptEditor()
            elif ScriptEditor.gui.isVisible():
                return
            QtWidgets.QMainWindow.show(ScriptEditor.gui)

            ui = ScriptEditor.gui
            geom = ui.geometry()
            geom = (geom.x(), geom.y(), geom.width(), geom.height())
            settings = {'geometry': geom, 'sizes': ui.splitter.sizes()}
            if 'script_editor_settings' in g.settings:
                settings.update(g.settings['script_editor_settings'])
            ui.setGeometry(*settings['geometry'])
            ui.splitter.setSizes(settings['sizes'])

    def closeEvent(self, ev):
        geom = self.geometry()
        geom = (geom.x(), geom.y(), geom.width(), geom.height())
        g.settings['script_editor_settings'] = {'geometry': geom, 'sizes': self.splitter.sizes()}

    @staticmethod
    def close():
        if hasattr(ScriptEditor, 'gui'):
            QtWidgets.QMainWindow.close(ScriptEditor.gui)

    
if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    ScriptEditor.show()
    app.exec_()


logger.debug("Completed 'reading app/script_editor.py'")