# -*- coding: utf-8 -*-
"""
Created on Mon Jul 21 10:32:00 2014

@author: Kyle Ellefsen
"""

dependencies = ['skimage', 'leastsqbound', 'matplotlib','PyOpenGL']

menu_layout = {'Puffs': \
				{'Average Origin': ['average_origin', 'average_origin.gui'], \
				'Frame By Frame': ['frame_by_frame_origin', 'frame_by_frame.gui'],\
				'Threshold Cluster': ['threshold_cluster', 'threshold_cluster.gui']}}