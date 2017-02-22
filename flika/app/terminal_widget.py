# -*- coding: utf-8 -*-
"""
@author: Brett Settle
"""
from qtpy import QtGui, QtCore, QtWidgets, uic
import os

if __name__ != '__main__':
    import flika.global_vars as g
    from flika.app.terminal import ipython_terminal
    from flika.app.script_namespace import getnamespace
    from flika.app.syntax import PythonHighlighter
    from flika.utils import load_ui, getSaveFileName, getOpenFileName
else:
    from syntax import PythonHighlighter
    from terminal import ipython_terminal
    class K:
        pass
    g = K()
    g.settings = {'recent_scripts': []}
    g.currentWindow = None

    import numpy, scipy
    getnamespace = lambda : {'np': numpy, 'scipy': scipy}


def qstr2str(string):
    string=str(string)
    return string.replace(u'\u2029','\n').strip()

class Editor(QtWidgets.QPlainTextEdit):
    def __init__(self, scriptfile = ''):
        super(Editor, self).__init__()
        self.highlight = PythonHighlighter(self.document())
        self.scriptfile = ''
        if scriptfile != '':
            self.load_file(scriptfile)
        self.installEventFilter(self)

    @staticmethod
    def fromWindow(window):
        editor = Editor()
        editor.setPlainText('\n'.join(window.commands))
        return editor
        
    def load_file(self, scriptfile):
        self.scriptfile = scriptfile
        try:
            script = open(scriptfile, 'r').read()
        except Exception as e:
            print("Failed to read %s: %s" % (scriptfile, e))

        self.setPlainText(script)
        ScriptEditor.gui.statusBar().showMessage('{} loaded.'.format(os.path.basename(self.scriptfile)))

    def save_as(self):
        filename=getSaveFileName(self, 'Save script', ScriptEditor.most_recent_script(), '*.py')
        if filename == '':
            ScriptEditor.gui.statusBar().showMessage('Save cancelled')
            return False
        self.scriptfile = filename
        self.save()
        return True

    def save(self):
        if self.scriptfile == '':
            return self.save_as()
        f = open(self.scriptfile, 'w')
        command=qstr2str(self.toPlainText())
        f.write(command)
        f.close()
        ScriptEditor.add_recent_file(self.scriptfile)
        ScriptEditor.gui.statusBar().showMessage('{} saved.'.format(os.path.basename(self.scriptfile)))
        return True

    def eventFilter(self, source, event):
        if (event.type()==QtGui.QKeyEvent.KeyPress and event.key() == QtCore.Qt.Key_Tab):
            event.accept()
            self.insertPlainText('    ')
            return True
        else:
            event.ignore()
        return False

class ScriptEditor(QtWidgets.QMainWindow):
    '''
    QMainWindow for editing and running user scripts. Comprised of a tabbed text editor and console.
    '''
    def __init__(self, parent=None, ):
        super(ScriptEditor, self).__init__(parent)
        load_ui('ipythonWidget.ui', self, directory=os.path.dirname(__file__))
        text = """Predefined Libraries:
    scipy and numpy (np)
Useful variables:
    g.m.windows - list of windows.
    g.currentWindow - the selected window
    g.currentWindow.rois -list of rois in that window
    - roi.getTrace() gets an roi trace as an array """
        self.setWindowIcon(QtGui.QIcon('images/favicon.png'))
        #self.splitter.setMargin(2)
        self.terminal = ipython_terminal(banner=text, **getnamespace())
        layout = QtWidgets.QGridLayout()
        self.terminalWidget.setLayout(layout)
        layout.addWidget(self.terminal)
        self.addEditor()
        self.saveButton.clicked.connect(self.saveCurrentScript)
        self.runButton.clicked.connect(self.runScript)
        self.runSelectedButton.clicked.connect(self.runSelected)
        self.actionNew_Script.triggered.connect(lambda f: self.addEditor())
        self.actionFrom_File.triggered.connect(lambda f: ScriptEditor.importScript())
        self.actionFrom_Window.triggered.connect(lambda : self.addEditor(Editor.fromWindow(g.currentWindow)))
        self.actionSave_Script.triggered.connect(self.saveCurrentScript)
        self.menuRecentScripts.aboutToShow.connect(self.load_scripts)
        self.actionChangeFontSize.triggered.connect(self.changeFontSize)
        #self.eventeater = ScriptEventEater(self)
        self.setAcceptDrops(True)
        #self.installEventFilter(self.eventeater)
        self.scriptTabs.tabCloseRequested.connect(self.closeTab)
        self.setWindowTitle('Script Editor')

    def changeFontSize(self):
        val, ok = QtWidgets.QInputDialog.getInt(self, "Change Font Size", "Font Size", \
            value=ScriptEditor.gui.centralWidget().font().pointSize(), min = 8, max = 30, step = 1)
        if ok:
            font = ScriptEditor.gui.centralWidget().font()
            font.setPointSize(val)
            ScriptEditor.gui.centralWidget().setFont(font)

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

    def load_scripts(self):
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
        if not os.path.exists(filename):
            return
        if filename in g.settings['recent_scripts']:
            g.settings['recent_scripts'].remove(filename)
        g.settings['recent_scripts'].insert(0, filename)
        if len(g.settings['recent_scripts']) > 8:
            g.settings['recent_scripts'] = g.settings['recent_scripts'][:-1]

    @staticmethod
    def importScript(scriptfile = ''):
        if not hasattr(ScriptEditor, 'gui') or not ScriptEditor.gui.isVisible():
            ScriptEditor.show()
        if scriptfile == '':
            scriptfile= getOpenFileName(ScriptEditor.gui, 'Load script', os.path.dirname(ScriptEditor.most_recent_script()), '*.py')
            if scriptfile == '':
                return
        editor = Editor(scriptfile)
        ScriptEditor.add_recent_file(scriptfile)
        ScriptEditor.gui.addEditor(editor)
    
    def addEditor(self, editor=None):
        self.setUpdatesEnabled(False)
        if editor == None:
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
        if not hasattr(ScriptEditor, 'gui'):
            ScriptEditor.gui = ScriptEditor()
        QtWidgets.QMainWindow.show(ScriptEditor.gui)

    @staticmethod
    def close():
        if hasattr(ScriptEditor, 'gui'):
            QtWidgets.QMainWindow.close(ScriptEditor.gui)

    
if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    ScriptEditor.show()
    app.exec_()
    