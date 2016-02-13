# -*- coding: utf-8 -*-
import os, re, sys, pip
from os.path import basename, expanduser
from sys import platform as _platform
from importlib import import_module

if sys.version_info.major==2:
    from urllib2 import Request, urlopen
elif sys.version_info.major==3:
    from urllib.request import Request, urlopen
import traceback

pyversion=str(sys.version_info.major)+str(sys.version_info.minor)
is_64bits = sys.maxsize > 2**32
if is_64bits:
    fnames_suffix="-cp"+pyversion+"-none-win_amd64.whl"
else:
    fnames_suffix="-cp"+pyversion+"-none-win32.whl"
    

base_url='http://www.lfd.uci.edu/~gohlke/pythonlibs/'

def get_url(ml,mi):
    mi = mi.replace('&lt;', '<')
    mi = mi.replace('&gt;', '>')
    mi = mi.replace('&amp;', '&')
    mi = mi.replace("&#46;", '.')
    mi = mi.replace("&#62;", '>')
    mi = mi.replace("&#60;", '<')
    ot="";
    for j in range(len(mi)):
        ot += chr(ml[ord(mi[j])-48])
    return ot

def get_wheel_url(plugin):
    req = Request(base_url, headers={'User-Agent':"Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2357.132 Safari/537.36"})
    resp = urlopen(req)
    regex = re.compile('javascript:dl(\([^\)]*\))[^>]*>(%s[^<]*)<' % plugin, re.IGNORECASE | re.DOTALL)
    fnames = {}
    for line in resp.readlines():
        line = line.decode('utf-8').replace('&#8209;', '-')
        line = line.replace("&#46;", '.')
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
    print("Downloading to %s" % download_url)
    f = open(basename(download_url), 'wb')
    the_page=response.read()
    f.write(the_page)
    f.close()
    
def is_installed(dep):
    for dist in pip.get_installed_distributions(local_only=False):
        if dep.lower() == dist.project_name.lower() or dist._provider.egg_info.split('\\')[-1].startswith(dep + '-'):
            return True
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
    if is_installed(dep):
        return
    old_cwd=os.getcwd()
    flika_dir=os.path.join(expanduser("~"),'.FLIKA')
    if not os.path.exists(flika_dir):
        os.makedirs(flika_dir)
    
    os.chdir(flika_dir)

    if _platform == 'win32':
        try:
            install_wheel(dep)
            print('Successfully installed %s from Gohlke\'s website' % dep)
            os.chdir(old_cwd)
            return
        except IOError:
            print('You need to run this file with administrator privileges. Also, make sure that all other Python programs are closed.')
        except Exception as e:
            print("Could not install %s from Gohlke's website. %s" % traceback.format_exc())
    
    if not is_installed(dep):
        if pip.main(['install', dep, '--no-deps']) != 0:
            print('Could not install %s: %s' % (dep, e))

    os.chdir(old_cwd)  
        
def install_wheel(dep):
    if _platform != 'win32':
        raise Exception("No support for installing binaries on non-windows machines")
    wheel = get_wheel_url(dep)
    if wheel != '':
        if not os.path.isfile(wheel):
            print('Downloading {}'.format(wheel))
            download_file(base_url+wheel)
        print('Installing {}'.format(wheel))
        old_cwd=os.getcwd()
        flika_dir=os.path.join(expanduser("~"),'.FLIKA')
        pip.main(['install', os.path.basename(wheel)])
        
        os.remove(basename(wheel)) #if the installation was successful, remove the .whl file
        
        os.chdir(old_cwd)
    else:
        raise Exception("No module named %s found." % dep)

def check_dependencies(*args):
    for dep in args:
        install(dep)

if __name__ == "__main__":
    for arg in sys.argv[1:]:
        install(arg)