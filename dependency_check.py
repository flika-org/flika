# -*- coding: utf-8 -*-
import os, re, sys, pip
from os.path import basename, expanduser
from sys import platform as _platform
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
base_url='http://www.lfd.uci.edu/~gohlke/pythonlibs/'



def get_url(ml,mi):
    mi = mi.replace('&lt;', '<')
    mi = mi.replace('&gt;', '>')
    mi = mi.replace('&amp;', '&')
    ot="";
    for j in range(len(mi)):
        ot += chr(ml[ord(mi[j])-48])
    return ot

def get_wheel_url(plugin):
    if is_64bits:
        fnames_suffix="-cp"+pyversion+"-none-win_amd64.whl"
    else:
        fnames_suffix="-cp"+pyversion+"-none-win32.whl"
    url = "http://www.lfd.uci.edu/~gohlke/pythonlibs"
    req = Request(url,headers={'User-Agent':"Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2357.132 Safari/537.36"})
    resp = urlopen(req)
    regex = re.compile('javascript:dl(\([^\)]*\))[^>]*>(%s[^<]*)<' % plugin, re.IGNORECASE | re.DOTALL)
    fnames = {}
    for line in resp.readlines():
        line = line.decode('utf-8').replace('&#8209;', '-')
        fname = re.findall(regex, line)
        if len(fname) > 0:
            res, fname = fname[0]
            res = eval(res)
            if fname.endswith(fnames_suffix):
                fnames[fname] = res

    return get_newest_version(fnames)

def get_newest_version(fnames):
    if len(fnames) == 0:
        return ''
    fname = ''
    version = ['0']
    regex = re.compile('[^-]*-([a-zA-Z0-9\.]*)')
    for f in fnames:
        v = re.findall(regex, f)[0].split('.')
        i = 0
        if fname == '' or int(v[0]) > int(version[0]):
            fname = f
            version = v
            continue
        while i < min(len(v), len(version)) - 1 and v[i] == version[i]:
            if int(v[i+1]) > int(version[i+1]):
                version = v
                fname = f
            i += 1
    return get_url(*fnames[fname])

def download_file(download_url):
    req = Request(download_url,headers={'User-Agent':"Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2357.132 Safari/537.36"})
    response = urlopen(req)
    f = open(basename(download_url), 'wb')
    the_page=response.read()
    f.write(the_page)
    f.close()
    
def is_installed(dep):
    try:
        import_module(dep)
        return True
    except ImportError as e:
        if sys.version_info.major==2:
            if e.message=='No module named {}'.format(dep):
                return False
        elif sys.version_info.major==3:
            if e.msg=="No module named '{}'".format(dep):
                return False

def install(dep):
    old_cwd=os.getcwd()
    flika_dir=os.path.join(expanduser("~"),'.FLIKA')
    if not os.path.exists(flika_dir):
        os.makedirs(flika_dir)
    os.chdir(flika_dir)
    if is_installed(dep):
        os.chdir(old_cwd)  
        return
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
    except Exception:
        print('Trying to install from Gohlke on win32 only')
        try:
            install_wheel(dep)
        except:
            print('Could not install %s' % dep)

    os.chdir(old_cwd)  
        
def install_wheel(dep):
    if _platform != 'win32':
        print("No support for installing binaries on non-windows machines")
        return
    wheel = get_wheel_url(dep)
    if wheel != '':
        if not os.path.isfile(wheel):
            print('Downloading {}'.format(wheel))
            download_file(base_url+wheel)
        print('Installing {}'.format(wheel))
        install(basename(wheel))
        try:
            import_module(dep)
            os.remove(fname) #if the installation was successful, remove the .whl file
        except:
            pass #if it wasn't successful, keep the .whl file.

def check_dependencies(*args):
    for dep in args:
        install(dep)

