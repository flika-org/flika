# -*- coding: utf-8 -*-
"""
Created on Fri Dec 04 13:23:33 2015

@author: Kyle Ellefsen
"""
import numpy as np

from plugins.detect_puffs.puff_simulator.puff_simulator import simulate_puffs
from plugins.detect_puffs.threshold_cluster import threshold_cluster
data_window=simulate_puffs(nFrames=1000,nPuffs=20)
data_window=g.m.currentWindow
norm_window=data_window
norm_window.setName('Normalized Window')
binary_window=threshold(1.1, keepSourceWindow=True)
binary_window.setName('Binary Window')
threshold_cluster(binary_window,data_window,norm_window,density_threshold=5.8)

## run through manual steps

## once threshold_cluster has run, see what the percentage of puffs it detected, and the false positive rate


detected_puffs=g.m.puffAnalyzer.puffs.puffs
simulated_puffs=simulate_puffs.puffs
nearest_puffs=[]
for puff in detected_puffs:
    k=puff.kinetics
    detected_puff=np.array([k['t_peak'],k['x'],k['y']])
    difference=np.sqrt(np.sum((simulated_puffs-detected_puff)**2,1))
    closest_idx=np.argmin(difference)
    #distance=difference[closest_idx]
    closest_puff=simulated_puffs[closest_idx]
    distance=detected_puff-closest_puff
    nearest_puffs.append([closest_idx,distance[0],distance[1],distance[2]])

nearest_puffs=np.array(nearest_puffs)
distances=np.sqrt(nearest_puffs[:,2]**2+nearest_puffs[:,3]**2)