# -*- coding: utf-8 -*-
"""
Created on Mon Jul 21 10:32:00 2014

@author: Kyle Ellefsen
"""

dependencies = ['skimage', 'pyopengl', 'leastsqbound', 'matplotlib']

menu_layout = {'Puffs': \
				{'Average Origin': 'average_origin.average_origin_gui', \
				'Frame By Frame': 'frame_by_frame_origin.frame_by_frame_gui',\
				'Threshold Cluster': 'threshold_cluster.threshold_cluster_gui'}}