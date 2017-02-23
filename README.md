### Installation Instructions ###

#### Windows ####

1. Install Python

	* PyQt4
	* qtpy
	* pyqtgraph
	* scikit-image
	* ipython
	* zmq
	* ipykernel
	* qtconsole
	* pyopengl	
	* nd2reader
	* openpyxl
	* matplotlib
	* tifffile
	
	There are many ways you can install these dependencies, but the following is the way we prefer. Once you have installed Python, make a folder on your Desktop called `binary_dependencies`. Go to [Christoph Gohlke's website](http://www.lfd.uci.edu/~gohlke/pythonlibs/) and download the first three dependencies (numpy, scipy, and PyQt4) into the `binary_dependencies` folder. Make sure the computer architecture and python version match yours. For instance, I have Python 3.5 running on a 64 bit computer, so I do...(line truncated)...
	```
	python -m pip install --upgrade pip
	pip install "numpy-1.12.0+mkl-cp35-cp35m-win_amd64.whl"
	pip install scipy-0.19.0rc1-cp35-cp35m-win_amd64.whl
	pip install PyQt4-4.11.4-cp35-cp35m-win_amd64.whl
	pip install qtpy pyqtgraph scikit-image ipython zmq ipykernel qtconsole pyopengl nd2reader tifffile openpyxl
	```

	Now that all of Flika's dependencies are installed you can remove the `binary_dependencies` folder and install Flika. 


3. Install Flika

	Download the [zipped folder](https://github.com/kyleellefsen/Flika/archive/master.zip) from Github and extract the folder to a location on your computer (preferably in ```C:/Program Files/```). After the folder has been extracted, you can run Flika with the command ```python flika.py```. We recommend using the free IDE PyCharm for scripting in Flika. To run Flika in the PyCharm IPython interpreter, run the following command
	```