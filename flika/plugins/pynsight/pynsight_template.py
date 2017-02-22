# -*- coding: utf-8 -*-
"""
Created on Wed June 15 2016
@author: Kyle Ellefsen
"""
# import os, sys; flika_dir = os.path.join(os.path.expanduser('~'), 'Documents', 'GitHub', 'flika'); sys.path.append(flika_dir); from flika import *; start_flika()

from plugins.pynsight.pynsight import *
from plugins.pynsight.particle_simulator import simulate_particles
A, true_pts = simulate_particles()
data_window = Window(A)
data_window.setName('Data Window (F/F0)')
blur_window = gaussian_blur(2, norm_edges=True, keepSourceWindow=True)
blur_window.setName('Blurred Window')
binary_window = threshold(.7, keepSourceWindow=True)
binary_window.setName('Binary Window')

pynsight.gui()
pynsight.binary_window_selector.setWindow(binary_window)
pynsight.getPoints()
pynsight.blurred_window_selector.setWindow(blur_window)
pynsight.refinePoints()
pynsight.linkPoints()
pynsight.showPoints_unrefined()
pynsight.saveInsight()

# sys.exit(g.app.exec_())  # This is required to run outside of Spyder or PyCharm
