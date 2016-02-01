## Flika ##

**Flika** is an interactive image processing program for biologists written in Python.
### Website ###
[flika-org.github.io](http://flika-org.github.io/)

### Documentation ###
[flika-org.github.io/documentation.html](http://flika-org.github.io/documentation.html)

### Installation Instructions ###

#### Windows ####
1) Install Python
 
Flika requires Python to run.  You can install either Python 2 or Python 3 (if you are not sure, use Python 3). To install Python, go [here](https://www.python.org/downloads/windows/) and download the latest Windows x86-64 MSI installer.  Once the file is downloaded, double click the icon and follow the on-screen instructions.  

2) Install Flika


Download the [zipped folder](https://github.com/kyleellefsen/Flika/archive/master.zip) from Github and extract the folder to a location on your computer (preferably in ```C:/Program Files/```). After the folder has been extracted, you can double click the 'Flika.bat' file inside of the Flika-master folder. Or follow these steps to create an executable on the desktop:

Right click 'Flika.bat' and choose 'Create Shortcut', a shortcut icon should show up. Rename the 'Flika.bat - Shortcut' to just 'Flika', then right click it and select Properties. Click the button that says 'Change Icon' at the bottom of the window. (If a window pops up, press ok). Select 'Browse' to locate the FLIKA icon, located in the 'C:/Program Files/Flika-master/images/' folder under the name 'favicon.ico'. Once the icon is selected, you can move the shortcut to your desktop. Double click it to run Flika!

#### Ubuntu ####
Open a terminal and run the following commands:
```
sudo apt-get install python-pip python-numpy python-scipy build-essential cython python-matplotlib python-qt4-gl libgeos-c1v5 libgeos-dev
sudo pip install scikit-image
sudo pip install future
```
Download the [zipped folder](https://github.com/kyleellefsen/Flika/archive/master.zip) from Github and extract the folder to a location on your computer.  Navigate to the directory Flika was downloaded into.  Run Flika with the command
```python FLIKA.py```

#### Mac OSX ####

1) Install Python and Flika Dependencies

Install [https://www.continuum.io/downloads](Anaconda) by Continuum. This will install Python along with most of Flika's dependencies.  Any libraries not included in Anaconda will be installed the first time Flika is run.

2) Install Flika
Download the [zipped folder](https://github.com/kyleellefsen/Flika/archive/master.zip) from Github and extract the folder to a location on your computer.  Open a terminal (Press command+space, type 'Terminal'). Navigate to the directory Flika was downloaded into.  Run Flika with the command
```python FLIKA.py```
