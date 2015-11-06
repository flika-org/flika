# -*- coding: utf-8 -*-
import os
from os.path import basename, expanduser
import pip
from sys import platform as _platform
import sys
from importlib import import_module
if sys.version_info.major==2:
    from urllib2 import Request, urlopen
elif sys.version_info.major==3:
    from urllib.request import Request, urlopen
dependencies_pypi=['future','leastsqbound','pyqtgraph','openpyxl']
dependencies_gohlke=['PyQt4','numpy','scipy','skimage','OpenGL']

pyversion=str(sys.version_info.major)+str(sys.version_info.minor)
is_64bits = sys.maxsize > 2**32
if is_64bits:
    fnames_suffix="-cp"+pyversion+"-none-win_amd64.whl"
else:
    fnames_suffix="-cp"+pyversion+"-none-win32.whl"
    
dependency_fnames={
    'PyQt4':'PyQt4-4.11.4',
    'numpy':'numpy-1.9.2+mkl',
    'scipy':'scipy-0.16.0rc1',
    'skimage':'scikit_image-0.11.3',
    'OpenGL':'PyOpenGL-3.1.1a1'}
base_url='http://www.lfd.uci.edu/~gohlke/pythonlibs/3i673h27/'
    
old_cwd=os.getcwd()
flika_dir=os.path.join(expanduser("~"),'.FLIKA')
if not os.path.exists(flika_dir):
    os.makedirs(flika_dir)
os.chdir(flika_dir)
            
def download_file(download_url):
    req = Request(download_url,headers={'User-Agent':"Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2357.132 Safari/537.36"})
    response = urlopen(req)
    f = open(basename(download_url), 'wb')
    the_page=response.read()
    f.write(the_page)
    f.close()
    
def install(dep):
    try:
        pip.main(['install', dep])
    except IOError:
        print('You need to run this file with administrator privileges. Also, make sure that all other Python programs are closed.')
        if _platform == 'win32':
            print(" Search for the 'cmd' program, right click it and select 'Run as Administrator'. Then enter the following commands:\n\n")
            print("cd {}".format(os.path.realpath(__file__)))
            print('python dependency_check.py')
            print('\n\n\n')
            print('This should install all the dependencies.  You only need to do this once.')
    

        
if _platform == 'win32':
    for dep in dependencies_gohlke:
        try:
            import_module(dep)
        except ImportError:
            
            fname=dependency_fnames[dep]+fnames_suffix
            if not os.path.isfile(fname):
                print('Downloading {}'.format(dep))
                download_file(base_url+fname)
            print('Installing {}'.format(dep))
            install(fname)
            try:
                import_module(dep)
                os.remove(fname) #if the installation was successful, remove the .whl file
            except:
                pass #if it wasn't successful, keep the .whl file.
else:
    print("I haven't yet coded how to install binaries for non-Windows systems")

for dep in dependencies_pypi:
    try:
        import_module(dep)
    except ImportError as e:
        if sys.version_info.major==2:
            if e.message=='No module named {}'.format(dep):
                install(dep)
        elif sys.version_info.major==3:
            if e.msg=="No module named '{}'".format(dep):
                install(dep)
        
        
os.chdir(old_cwd)


