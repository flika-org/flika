# -*- coding: utf-8 -*-
"""
Created on Thu Jun 26 14:17:38 2014
updated 2015.01.27
@author: Kyle Ellefsen
"""
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import global_vars as g
import pyqtgraph as pg
import sys, os
from FLIKA import initializeMainGui
from process.voltage_ import *

try:
	os.chdir(os.path.split(os.path.realpath(__file__))[0])
except NameError:
	pass


def addVoltageButton():

	voltageButton = QPushButton("Extract Voltage")
	voltageButton.clicked.connect(extractVoltage)
	g.m.centralwidget.layout().insertWidget(-1, voltageButton)

def extractVoltage():
    img = g.m.currentWindow.imageview.image
    v = np.average(img, (2, 1))
    Vout, corrimg, weight_movie, offsetimg = extractV(img, v)
    Window(corrimg, 'Corrected Image')
    Window(weight_movie, "Weight Movie")
    Window(offsetimg, 'Offset Image')
    print(Vout)
    pg.plot(Vout)
    print(ApplyWeights(img[:], corrimg, weight_movie, offsetimg))

if __name__ == '__main__':
	app = QApplication(sys.argv)
	initializeMainGui()
	addVoltageButton()
	
	insideSpyder='SPYDER_SHELL_ID' in os.environ
	if not insideSpyder: #if we are running outside of Spyder
		sys.exit(app.exec_()) #This is required to run outside of Spyder
	
	
	
	
	
	
	
	
	