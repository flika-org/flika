## Flika ##

**Flika** is an interactive image processing program for biologists written in Python.
### Website ###
[flika-org.github.io](http://flika-org.github.io/)

### Documentation ###
[flika-org.github.io/documentation.html](http://flika-org.github.io/documentation.html)

### Installation Instructions ###

#### Windows (64 bit)####

##### For most users #####
[Download](https://github.com/flika-org/flika_win64/archive/master.zip) the stand-alone version of Flika.  Once it's downloaded, unzip the folder, find the flika.exe file, double click and Flika will launch.  

##### For developers #####

1. Install Python
 
	Flika requires Python 3 to run. To install Python, go [here](https://www.python.org/downloads/windows/) and download the latest Windows x86-64 MSI installer.  Once the file is downloaded, double click the icon and follow the on-screen instructions.  

2. Install Flika dependencies
	* numpy MKL
	* scipy
	* PyQt4
	* qtpy
	* pyqtgraph
	* PyOpenGL
	* scikit-image
	* xmltodict
	* nd2reader
	* openpyxl
	* matplotlib
	* tifffile

3. Install Flika


	Download the [zipped folder](https://github.com/kyleellefsen/Flika/archive/master.zip) from Github and extract the folder to a location on your computer (preferably in ```C:/Program Files/```). After the folder has been extracted, you can run Flika with the command ```python flika.py```. We recommend using the free IDE PyCharm for scripting in Flika. To run Flika in the PyCharm IPython interpreter, run the following command
	```
	import os, sys; flika_dir = my_flika_dir; sys.path.append(flika_dir); from flika import *; start_flika()
	```
	replacing ```my_flika_dir``` with the location of the flika folder.

#### Ubuntu ####
1. Install Python

	Flika requires Python 3 to run. Make sure this is the version of Python you are using.

2. Install Flika dependencies

	Open a terminal and run the following commands:
	```
	sudo apt-get install python-pip python-numpy python-scipy build-essential cython python-matplotlib python-qt4-gl libgeos-c1v5 libgeos-dev
	sudo pip install scikit-image
	```

3. Install Flika

	Download the [zipped folder](https://github.com/kyleellefsen/Flika/archive/master.zip) from Github and extract the folder to a location on your computer.  Navigate to the directory Flika was downloaded into.  Run Flika with the command

	```python flika.py```

#### Mac OSX ####

1. Install Python and Flika Dependencies

	Flika requires Python 3 to run. To install Python along with most of Flika's dependencies, download [Anaconda](https://www.continuum.io/downloads) by Continuum.

2. Install Flika

	Download the [zipped folder](https://github.com/kyleellefsen/Flika/archive/master.zip) from Github and extract the folder to a location on your computer.  Open a terminal (Press command+space, type 'Terminal'). Navigate to the directory Flika was downloaded into.  Run Flika with the command

	```python flika.py```
