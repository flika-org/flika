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
from script_namespace import getnamespace



def getScriptList():
    g.m.menuScripts.clear()
    g.m.scriptsDir=os.path.join(expanduser("~"),'.FLIKA','scripts')
    if not os.path.exists(g.m.scriptsDir):
        os.makedirs(g.m.scriptsDir)
    scripts=os.listdir(g.m.scriptsDir)
    scripts=sorted(scripts,key=str.lower)
    def makeFun(fun,script):
        return lambda: fun(script)
    for script in scripts:
        name=os.path.splitext(script)[0]
        script=os.path.join(g.m.scriptsDir,script)
        g.m.menuScripts.addAction(QAction("&"+name, g.m, triggered=makeFun(ScriptEditor,script)))
    g.m.menuScripts.addSeparator()
    g.m.menuScripts.addAction(QAction("&New...", g.m, triggered=ScriptEditor.gui))

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
    def __init__(self, parent, scriptfile = ''):
        QWidget.__init__(self)
        self.parent = parent
        if scriptfile != '':
            self.load_file(scriptfile)
        
    def load_file(self, scriptfile):
        self.scriptfile = scriptfile
        f = open(scriptfile, 'r')
        script=f.read()
        f.close()
        self.setPlainText(script)
        self.parent.statusBar().showMessage('{} loaded.'.format(os.path.basename(self.scriptfile)))

    def save_as(self):
        filename= str(QFileDialog.getSaveFileName(g.m, 'Save script', g.m.scriptsDir, '*.py'))
        if filename == '':
            return
        self.scriptfile = filename
        self.save()

    def save(self):
        if not hasattr(self, 'scriptfile'):
            print('This script has not been saved yet, please specify a filename')
            self.save_as()
        f = open(self.scriptfile, 'w')
        command=qstr2str(self.toPlainText())
        f.write(command)
        f.close()
        self.parent.statusBar().showMessage('{} saved.'.format(os.path.basename(self.scriptfile)))

class ScriptEditor(QMainWindow):
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
        self.consoleWidget.localNamespace=getnamespace()
        self.consoleWidget.output.setPlainText(text)
        self.addEditor()
        self.saveButton.clicked.connect(self.saveCurrentScript)
        self.runButton.clicked.connect(self.runScript)
        self.runSelectedButton.clicked.connect(self.runSelected)
        self.actionNew_Script.triggered.connect(lambda f: self.addEditor())
        self.actionFrom_File.triggered.connect(self.importScript)
        self.actionFrom_Window.triggered.connect(lambda : self.currentTab().setPlainText('\n'.join(g.m.currentWindow.commands)))
        self.actionSave_Script.triggered.connect(self.saveCurrentScript)
        g.m.scriptEditor = self
        self.eventeater = ScriptEventEater(self)
        self.setAcceptDrops(True)
        self.installEventFilter(self.eventeater)
        self.scriptTabs.tabCloseRequested.connect(self.closeTab)

    def closeTab(self, index):
        self.scriptTabs.removeTab(index)

    def saveCurrentScript(self):
        cw = self.currentTab()
        if cw == None:
            return
        cw.save()
        self.scriptTabs.setTabText(cw.currentIndex(), os.path.basename(cw.scriptfile))

    def currentTab(self):
        return self.scriptTabs.currentWidget()

    def importScript(self, scriptfile=''):
        if scriptfile == '':
            scriptfile= str(QFileDialog.getOpenFileName(self, 'Load script', g.m.scriptsDir, '*.py'))
            if scriptfile == '':
                return
        cw = self.currentTab()
        cw.load_file(scriptfile)
        self.scriptTabs.setTabText(self.scriptTabs.currentIndex(), os.path.basename(cw.scriptfile))
    
    def addEditor(self, scriptfile=''):
        self.setUpdatesEnabled(False)
        e = Editor(self, scriptfile=scriptfile)
        e.keyPressEvent = lambda ev: self.editorKeyPressEvent(e, ev)
        if scriptfile == '':
            scriptfile = 'New Script'
        self.scriptTabs.insertTab(0, e, scriptfile)
        self.scriptTabs.setCurrentIndex(0)
        self.setUpdatesEnabled(True)

    def keyPressEvent(self, ev):
        if ev.key() == Qt.Key_N and ev.modifiers() == Qt.ControlModifier:
            self.addEditor()
            ev.accept()

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
        command=cursor.selectedText() #self=g.m.scriptEditor.editor; a=self.command
        self.command=command
        command=qstr2str(command)
        self.consoleWidget.runCmd(command)

    @staticmethod
    def gui():
        if g.m.scriptEditor == None:
            g.m.scriptEditor = ScriptEditor()
        g.m.scriptEditor.show()


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
                self.parent.importScript(filename)  #This fails on windows symbolic links.  http://stackoverflow.com/questions/15258506/os-path-islink-on-windows-with-python
                event.accept()
            else:
                event.ignore()
        return False # lets the event continue to the edit

    
    
    
    