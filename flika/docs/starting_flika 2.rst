.. _startingflika:

Starting flika
===================================


If flika was :ref:`installed using pip <installation>`, start flika by opening a terminal and typing::
    
    flika

If you want to access the variables inside flika with the command line, type::

    from flika import *
    start_flika()

flika in IPython
----------------

To start flika from within an IPython command line, you need to `integrate IPython with the Qt event loop <http://ipython.readthedocs.io/en/stable/config/eventloops.html>`_. To do this, type::

    from flika import *
    %gui qt
    start_flika()


flika in PyCharm
-----------------

If you are using PyCharm, inside PyCharm go to File->Settings->Build, Execution, Deployment->Console->Python Console and append the following lines of code to the 'Starting Script'::

    from flika import *
    start_flika()

flika from git
--------------

If you downloaded flika using git rather that pip, you need to add flika to the python path before you can run it. Before starting flika, run the following code::

    import sys, os
    flika_dir = os.path.join(os.path.expanduser('~'),'Documents', 'GitHub', 'flika') # Change this to match the directory where flika is located.
    sys.path.append(flika_dir)