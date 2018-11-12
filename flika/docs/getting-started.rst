Installation and Getting Started
===================================

**Python Versions**: Python 3

**Platforms**: Windows, OSX, and Linux

**PyPI package name**: `flika <https://pypi.python.org/pypi/flika>`_

**dependencies**: `numpy <https://pypi.python.org/pypi/numpy>`_,
`scipy <http://pypi.python.org/pypi/scipy>`_,
`qtpy <http://pypi.python.org/pypi/qtpy>`_,
`pandas <http://pypi.python.org/pypi/pandas>`_,
`matplotlib <http://pypi.python.org/pypi/matplotlib>`_,
`pyqtgraph <http://pypi.python.org/pypi/pyqtgraph>`_,
`scikit-image <http://pypi.python.org/pypi/scikit-image>`_,
`scikit-learn <http://pypi.python.org/pypi/scikit-learn>`_,
`ipykernel <http://pypi.python.org/pypi/ipykernel>`_,
`qtconsole <http://pypi.python.org/pypi/qtconsole>`_,
`pyopengl <http://pypi.python.org/pypi/pyopengl>`_,
`nd2reader <http://pypi.python.org/pypi/nd2reader>`_.

.. _`getstarted`:
.. _installation:

Installation
----------------------------------------

Install on Windows and Mac OSX
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
flika requires Python 3 to run. To install Python along with most of flika's dependencies, download `Anaconda <https://www.anaconda.com/download/>`_ for the latest Python 3 version. Once Python is installed open a terminal and run::

    pip install flika

Install on Linux
^^^^^^^^^^^^^^^^
Make sure that the 'pip' command is for Python 3. Then open a terminal and run::

    pip install flika


Starting flika
----------------------------------------

If flika was installed using pip, start flika by opening a terminal and typing::
	
	flika

If you want to access the variables inside flika with the command line, type::

	from flika import *
	start_flika()

For more information on starting flika, go to :ref:`startingflika`.


.. _`simpletest`:

Our first test run
----------------------------------------------------------
Let's generate a random image and apply a gaussian blur. If you are only interested in 
flika's gui features, go to Image->Stacks->Generate Random Image. Once the image is 
generated, apply a gaussian blur to the current window by going to Process->Filters->
Gaussian Blur.

If you want to do the same thing by code, either use the console you ran the 
``start_flika()`` command in or open the Script Editor (Scripts->Script Editor) and type::

    generate_random_image()
    gaussian_blur(sigma=2)



Where to go next
-------------------------------------

Here are a few suggestions where to go next:

* :ref:`examples` examples of image processing using flika
* :ref:`plugins` installing and writing plugins


