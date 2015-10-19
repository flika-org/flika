# -*- coding: utf-8 -*-
"""
Created on Fri Feb 06 11:24:36 2015

@author: Kyle Ellefsen
"""

open_file()
pixel_binning(2)
subtract(100) #subtract baseline
data_window=ratio(0,30,'average'); #ratio(first_frame, nFrames, ratio_type), now we are in F/F0
data_window.setWindowTitle('Data Window (F/F0)')
high_pass=butterworth_filter(1,.00615,1,keepSourceWindow=True) # High pass filter 
high_pass.setWindowTitle('High Pass Data Window (filtered F/F0)')
low_pass=image_calculator(data_window,high_pass,'Subtract',keepSourceWindow=True) # we will use the low pass image as an approximation for the variance of the photon noise.  
low_pass.image[low_pass.image<1]=1 # We can't take the sqrt of a negative number
low_pass=power(.5) #convert from variance to standard deviation
high_pass.select() 
norm_window=ratio(0,30,'standard deviation', keepSourceWindow=True) 
image_calculator(norm_window,low_pass,'Divide') #now the noise should be constant throughout the imaging field and over the duration of the movie
norm_window=set_value(0,  1000, 1099) #our butterworth_filter gives us an artifact towards the end of the movie
norm_window=set_value(0,  0, 50) #our butterworth_filter gives us an artifact towards the end of the movie
norm_window.setWindowTitle('Normalized Window')
#
gaussian_blur(1, keepSourceWindow=True)
binary_window=threshold(.7)
binary_window.setWindowTitle('Binary Window')
#threshold_cluster(binary_window,data_window,norm_window,rotatedfit=False, density_threshold=4,time_factor=3)


data_window=open_file(r'D:\Desktop\data_window.tif')
high_pass=open_file(r'D:\Desktop\high_pass.tif')
norm_window=open_file(r'D:\Desktop\norm_window.tif')
binary_window=open_file(r'D:\Desktop\binary_window.tif')




threshold_cluster(binary_window,high_pass,norm_window,rotatedfit=False, roi_width=9, maxPuffDiameter=15, maxSigmaForGaussianFit=15, maxPuffLen=5, density_threshold=3.5,time_factor=1)





#puffs at 519, 533
