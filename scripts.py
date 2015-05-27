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
    g.m.menuScripts.addAction(QAction("&New...", g.m, triggered=newScript))

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

    
class ScriptEditor(QWidget):
    def __init__(self,scriptfile):
        QWidget.__init__(self)
        self.setWindowTitle(scriptfile)
        self.setGeometry(QRect(357, 178, 1100, 430))
        self.editor=Editor(scriptfile,self)
        self.interpreter=Interpreter(self)
        self.layout=QHBoxLayout()
        self.splitter =  QSplitter()
        self.splitter.addWidget(self.editor)
        self.splitter.addWidget(self.interpreter)
        self.splitter.setSizes([500,500])
        self.layout.addWidget(self.splitter)        
        self.setLayout(self.layout)
        self.show()
        g.m.scriptEditor=self
    def closeEvent(self, event):
        self.editor.save()
        g.m.scriptEditor=None
        event.accept() # let the window close
    
class Editor(QWidget):
    def __init__(self,scriptfile,parent):
        QWidget.__init__(self)
        self.parent=parent
        self.scriptfile=scriptfile
        self.textEdit=QPlainTextEdit()
        f = open(scriptfile, 'r')
        script=f.read()
        f.close()
        self.textEdit.setPlainText(script)
        self.saveButton=QPushButton('Save')
        self.saveButton.clicked.connect(self.save)
        self.runButton=QPushButton('Run')
        self.runButton.clicked.connect(self.run)
        self.runSelectedButton=QPushButton('Run Selected (F9)')
        self.runSelectedButton.clicked.connect(self.runSelected)
        self.layout=QVBoxLayout()
        self.layout_b=QHBoxLayout()
        self.layout.addWidget(self.textEdit)
        self.layout_b.addWidget(self.saveButton)
        self.layout_b.addWidget(self.runButton)
        self.layout_b.addWidget(self.runSelectedButton)
        self.layout.addLayout(self.layout_b)
        self.setLayout(self.layout)
    def save(self):
        f = open(self.scriptfile, 'w')
        command=qstr2str(self.textEdit.toPlainText())
        f.write(command)
        f.close()
        g.m.statusBar().showMessage('{} saved.'.format(os.path.basename(self.scriptfile)))
    def run(self):
        self.save()
        command=qstr2str(self.textEdit.toPlainText())
        self.parent.interpreter.runCmd(command)
    def runSelected(self):
        cursor=self.textEdit.textCursor()
        command=cursor.selectedText() #self=g.m.scriptEditor.editor; a=self.command
        self.command=command
        command=qstr2str(command)
        self.parent.interpreter.runCmd(command)
    def keyPressEvent(self,ev):
        if ev.key() == Qt.Key_F9:
            self.runSelected()
            ev.accept()
    

class Interpreter(pyqtgraph.console.ConsoleWidget):
    def __init__(self,parent):
        self.parent=parent
        namespace=getnamespace()
        ## initial text to display in the console
        text = """
        This is an interactive python console. The numpy and pyqtgraph modules have already been imported 
        as 'np' and 'pg'.
        The following are useful variables:
            g.m.windows is a dictionary containing all the windows.
            g.m.currentWindow is the currentWindow
            g.m.currentWindow.rois is a list of all the rois in that window
            - You can get traces of those rois by using the roi.getTrace() function
        
        """
        pyqtgraph.console.ConsoleWidget.__init__(self,namespace=namespace,text=text)
            

    
    
    
    