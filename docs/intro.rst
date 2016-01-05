Getting Started
===================
Flika currently supports .tif files and .stk files.  To create a script, save a python file in the 'scripts' directory.  To run it, select 'Scripts', then click on the name of your script.

Processes
===================
File
----------------
.. py:module:: file_
.. autofunction:: open_file
.. autofunction:: open_file_gui
.. autofunction:: save_file
.. autofunction:: save_file_gui
.. autofunction:: save_current_frame
.. autofunction:: save_movie
.. autofunction:: close

Stacks
+++++++++++++++++++
.. py:module:: stacks
.. autofunction:: deinterleave
.. autofunction:: pixel_binning
.. autofunction:: frame_binning
.. autofunction:: trim
.. autofunction:: zproject
.. autofunction:: image_calculator

Binary
+++++++++++++++++++
.. py:module:: binary
.. autofunction:: threshold
.. autofunction:: adaptive_threshold
.. autofunction:: remove_small_blobs
.. autofunction:: canny_edge_detector
.. autofunction:: logically_combine
.. autofunction:: binary_dilation
.. autofunction:: binary_erosion

Filters
+++++++++++++++++++
.. py:module:: filters
.. autofunction:: gaussian_blur
.. autofunction:: mean_filter
.. autofunction:: median_filter
.. autofunction:: wavelet_filter
.. autofunction:: difference_filter
.. autofunction:: fourier_filter
.. autofunction:: butterworth_filter
.. autofunction:: boxcar_differential_filter

Math
+++++++++++++++++++
.. py:module:: math_
.. autofunction:: subtract
.. autofunction:: power
.. autofunction:: absolute_value
.. autofunction:: subtract_trace
.. autofunction:: ratio
.. autofunction:: multiply

Analyze
===================



.. |Ca2+| replace:: Ca\ :sup:`2+`
.. |IP3| replace:: IP\ :sub:`3`


