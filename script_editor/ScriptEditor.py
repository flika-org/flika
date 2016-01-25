# -*- coding: utf-8 -*-
"""
Created on Fri Jul 18 12:46:47 2014

@author: Kyle Ellefsen
"""
from __future__ import (absolute_import, division,print_function, unicode_literals)
from future.builtins import (bytes, dict, int, list, object, range, str, ascii, chr, hex, input, next, oct, open, pow, round, super, filter, map, zip)
                
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import os
import global_vars as g
from os.path import expanduser
import datetime
from PyQt4 import uic
from pyqtgraph import console
import pyqtgraph as pg
import pyqtgraph.console
from script_editor.script_namespace import getnamespace
from script_editor.syntax import PythonHighlighter

def newScript():
    filename= QFileDialog.getSaveFileName(g.m, 'Open File', g.m.scriptsDir, '*.py')
    filename=str(filename)
    if filename=='':
        return False
    elif os.path.basename(filename) in os.listdir(g.m.scriptsDir): #if this file already exists, don't save over it
        g.m.statusBar().showMessage("You cannot write over an already saved script.  Manually delete the file if you'd like to reuse the filename.")
        return False
    else:
        f=open(filename,'w')
        d=datetime.datetime.now().isoformat().strip().split('T')[0].replace('-','.')
        author=os.path.basename(expanduser("~"))
        f.write('''"""\nCreated {}\n\n@author:{}\n"""\nopen_file(g.m.settings['filename'])'''.format(d,author))
        f.close()        
        
def executeScript(scriptfile):
    f = open(scriptfile, 'r')
    script=f.read()
    f.close()
    if g.m.interpreter is None:
        launch_interpreter()
    g.m.interpreter.runCmd(script)
    
def qstr2str(string):
    string=str(string)
    return string.replace(u'\u2029','\n')

class Editor(QPlainTextEdit):
    def __init__(self, scriptfile = ''):
        QWidget.__init__(self)
        self.highlight = PythonHighlighter(self.document())
        self.scriptfile = ''
        if scriptfile != '':
            self.load_file(scriptfile)

    @staticmethod
    def fromWindow(window):
        editor = Editor()
        editor.setPlainText('\n'.join(window.commands))
        return editor
        
    def load_file(self, scriptfile):
        self.scriptfile = scriptfile
        f = open(scriptfile, 'r')
        script=f.read()
        f.close()
        self.setPlainText(script)
        g.m.statusBar().showMessage('{} loaded.'.format(os.path.basename(self.scriptfile)))

    def save_as(self):
        filename= str(QFileDialog.getSaveFileName(g.m, 'Save script', g.m.scriptsDir, '*.py'))
        if filename == '':
            g.m.statusBar().showMessage('Save cancelled')
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
        g.m.statusBar().showMessage('{} saved.'.format(os.path.basename(self.scriptfile)))
        return True

class ScriptEditor(QMainWindow):
    '''
    QMainWindow for editing and running user scripts. Comprised of a tabbed text editor and console.
    '''
    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)
        uic.loadUi('gui/scriptEditor.ui', self)
        text = """
        This is an interactive python console. The numpy and pyqtgraph modules have already been imported 
        as 'np' and 'pg'.
        The following are useful variables:
            g.m.windows is a dictionary containing all the windows.
            g.m.currentWindow is the currentWindow
            g.m.currentWindow.rois is a list of all the rois in that window
            - You can get traces of those rois by using the roi.getTrace() function
        
        """
        self.setWindowIcon(QIcon('images/favicon.png'))
        self.consoleWidget.localNamespace=getnamespace()
        self.consoleWidget.output.setPlainText(text)
        self.addEditor()
        self.saveButton.clicked.connect(self.saveCurrentScript)
        self.runButton.clicked.connect(self.runScript)
        self.runSelectedButton.clicked.connect(self.runSelected)
        self.actionNew_Script.triggered.connect(lambda f: self.addEditor())
        self.actionFrom_File.triggered.connect(lambda f: ScriptEditor.importScript())
        self.actionFrom_Window.triggered.connect(lambda : self.addEditor(Editor.fromWindow(g.m.currentWindow)))
        self.actionSave_Script.triggered.connect(self.saveCurrentScript)
        self.menuRecentScripts.aboutToShow.connect(self.load_scripts)
        self.eventeater = ScriptEventEater(self)
        self.setAcceptDrops(True)
        self.installEventFilter(self.eventeater)
        self.scriptTabs.tabCloseRequested.connect(self.closeTab)
        self.setWindowTitle('Script Editor')

    def load_scripts(self):
        self.menuRecentScripts.clear()
        def makeFun(script):
            return lambda: ScriptEditor.importScript(script)
        if len(g.m.settings['recent_scripts']) == 0:
            action = QAction("No Recent Scripts", g.m)
            action.setEnabled(False)
            self.menuRecentScripts.addAction(action)
        else:
            for filename in g.m.settings['recent_scripts']:
                action = QAction(filename, g.m, triggered=makeFun(filename))
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
    def importScript(scriptfile = ''):
        if not ScriptEditor.gui.isVisible():
            ScriptEditor.gui.show()
        if scriptfile == '':
            scriptfile= str(QFileDialog.getOpenFileName(ScriptEditor.gui, 'Load script', os.path.dirname(g.m.settings['recent_scripts'][-1]) if len(g.m.settings['recent_scripts']) > 0 else '', '*.py'))
            if scriptfile == '':
                return
        editor = Editor(scriptfile)
        if scriptfile in g.m.settings['recent_scripts']:
            g.m.settings['recent_scripts'].remove(scriptfile)
        g.m.settings['recent_scripts'].append(scriptfile)
        if len(g.m.settings['recent_scripts']) > 8:
            g.m.settings['recent_scripts'] = g.m.settings['recent_scripts'][-8:]
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
        if ev.modifiers() == Qt.ControlModifier:
            if ev.key() == Qt.Key_N:
                self.addEditor()
                ev.accept()
            elif ev.key() == Qt.Key_S:
                self.saveCurrentScript()

    def editorKeyPressEvent(self, editor, ev):
        if ev.key() == Qt.Key_F9:
            self.runSelected()
            ev.accept()
        else:
            Editor.keyPressEvent(editor, ev)

    def runScript(self):
        if self.currentTab() == None:
            return
        command=qstr2str(self.currentTab().toPlainText())
        self.consoleWidget.runCmd(command)

    def runSelected(self):
        if self.currentTab() == None:
            return
        cursor=self.currentTab().textCursor()
        command=cursor.selectedText()
        self.command=command
        command=qstr2str(command)
        self.consoleWidget.runCmd(command)

    @staticmethod
    def show():
        if not hasattr(ScriptEditor, 'gui'):
            ScriptEditor.gui = ScriptEditor()
        QMainWindow.show(ScriptEditor.gui)

    @staticmethod
    def close():
        if hasattr(ScriptEditor, 'gui'):
            QMainWindow.close(ScriptEditor.gui)

class ScriptEventEater(QObject):
    def __init__(self,parent=None):
        QObject.__init__(self,parent)
        self.parent = parent
    def eventFilter(self,obj,event):
        if (event.type()==QEvent.DragEnter):
            if event.mimeData().hasUrls():
                event.accept()   # must accept the dragEnterEvent or else the dropEvent can't occur !!!
            else:
                event.ignore()
        if (event.type() == QEvent.Drop):
            if event.mimeData().hasUrls():   # if file or link is dropped
                url = event.mimeData().urls()[0]   # get first url
                filename=url.toString()
                filename=filename.split('file:///')[1]
                print('filename={}'.format(filename))
                ScriptEditor.importScript(filename)  #This fails on windows symbolic links.  http://stackoverflow.com/questions/15258506/os-path-islink-on-windows-with-python
                event.accept()
            else:
                event.ignore()
        return False # lets the event continue to the edit

    
    