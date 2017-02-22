# -*- coding: utf-8 -*-
"""
Created on Fri Feb 06 11:24:36 2015

@author: Kyle Ellefsen
"""
if __name__ == '__main__':
    import os, sys; flika_dir = os.path.join(os.path.expanduser('~'),'Documents', 'GitHub', 'flika'); sys.path.append(flika_dir); from flika import *; start_flika()

    from plugins.detect_puffs.threshold_cluster import threshold_cluster
    from plugins.detect_puffs.puff_simulator.puff_simulator import simulate_puffs
    simulate_puffs(nFrames=1000,nPuffs=20)
    baseline = -5  # This is the mean pixel value in the absence of photons.
    subtract(baseline)
    data_window=ratio(0, 30, 'average')  # ratio(first_frame, nFrames, ratio_type). Now we are in F/F0
    data_window.setName('Data Window (F/F0)')
    norm_image = data_window.image - 1
    norm_window = Window(norm_image)
    norm_window.setName('Normalized Window')
    blurred_window = gaussian_blur(2, norm_edges=True, keepSourceWindow=True)
    blurred_window.setName('Blurred Window')
    threshold_cluster(data_window, blurred_window, blurred_window, blur_thresh=.3)

    sys.exit(g.app.exec_())  # This is required to run outside of Spyder or PyCharm