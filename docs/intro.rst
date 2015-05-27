Introduction to Flika
************************
Flika was created in the `Parker Lab <http://parkerlab.bio.uci.edu/index.htm>`_ in order to detect and measure |Ca2+| puffs caused by |IP3| channel openings.  It is growing into a general analysis tool for biological movies.

Getting Started
===================
Flika currently supports .tif files and .stk files.  To create a script, save a python file in the 'scripts' directory.  To run it, select 'Scripts', then click on the name of your script.

Functions
===================
File
----------------
.. py:module:: file
.. autofunction:: open_file
.. autofunction:: save_file
Edit
----------------
Image
----------------
Stacks
+++++++++++++++++++
.. py:module:: stacks
.. autofunction:: deinterleave
.. autofunction:: slicekeeper
Process
----------------
Binary
+++++++++++++++++++
.. py:module:: binary
.. autofunction:: threshold
.. autofunction:: remove_small_blobs
Filters
+++++++++++++++++++
.. py:module:: filters
.. autofunction:: gaussian_blur
.. autofunction:: butterworth_filter
.. autofunction:: boxcar_differential_filter
Math
+++++++++++++++++++
.. py:module:: math_
.. autofunction:: subtract
.. autofunction:: ratio
.. autofunction:: multiply
Analyze
----------------

.. |Ca2+| replace:: Ca\ :sup:`2+`
.. |IP3| replace:: IP\ :sub:`3`


