import sys, os
import optparse

from ..process import *
from .. import global_vars as g
from ..window import Window
import numpy as np
import time
import pytest
from ..roi import makeROI, open_rois
import pyqtgraph as pg
from qtpy import QtGui

def test_example1():
	w = generate_random_image(120, 140)
	trimmed = trim(0, 0, keepSourceWindow=True)
	assert trimmed.imageview.ui.roiPlot.isVisible() == False
	assert trimmed.image.shape[-2:] == w.image.shape[-2:]
	roi = makeROI('rectangle', [[10, 10], [15, 5]], w)
	cropped = roi.crop()



