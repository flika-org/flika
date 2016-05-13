from __future__ import print_function
INSTALL_DEPENDENCIES=True
from glob import glob
import os, sys, time, re
from sys import platform as _platform

if sys.version_info.major==2:
    from urllib2 import Request, urlopen
elif sys.version_info.major==3:
    from urllib.request import Request, urlopen
import traceback, zipfile, shutil, subprocess

def _matches_python_bit(fname):
    python_v = ("-cp%s" % pyversion in fname)
    bit_match = fname.endswith("-win%s.whl" % ("_amd64" if is_64bits else '32'))
    return python_v and bit_match

def download_file(download_url):
    req = Request(download_url,headers={'User-Agent':"Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2357.132 Safari/537.36"})
    response = urlopen(req)
    #length = int(response.getheader('Content-Length'))
    dest = os.path.basename(download_url)
    f = open(dest, 'wb')
    a = response.read()
    f.write(a)
    f.close()
    return dest

def install_pip():
    dest = download_file('https://bootstrap.pypa.io/get-pip.py')
    subprocess.call(['python', 'get-pip.py'])
    os.remove(dest)

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
    regex = re.compile('javascript:dl(\([^\)]*\))[^>]*>(%s-[^<]*)<' % plugin, re.IGNORECASE | re.DOTALL)
    fnames = {}
    for line in resp.readlines():
        line = line.decode('utf-8').replace('&#8209;', '-')
        line = line.replace("&#46;", '.')
        fname = re.findall(regex, line)
        if len(fname) > 0:
            res, fname = fname[0]
            res = eval(res)
            if _matches_python_bit(fname):
                fnames[fname] = res
    return get_newest_version(fnames)

def get_newest_version(fnames):
    if len(fnames) == 0:
        return ''
    fname = ''
    version = ['0']
    regex = re.compile('[^-]*-([a-zA-Z0-9\.]*)')
    for f in fnames:
        v = [n for n in re.findall(regex, f)[0].split('.') if n.isdigit()]
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


class NotOnGohlkeError(Exception):
    pass
class InstallFailedException(Exception):
    pass

def install_wheel(dep):
    if _platform != 'win32':
        raise Exception("No support for installing binaries on non-windows machines")
    wheel = get_wheel_url(dep)
    if wheel != '':
        if not os.path.isfile(wheel):
            print('Downloading {}'.format(base_url+wheel))
            dest = download_file(base_url+wheel)
        print('Installing {}'.format(dest))
        try:
            pip.main(['install', dest])
            os.remove(dest)
        except PermissionError:
            pass
        except IOError:
            pass
        except WindowsError:
            pass
    else:
        raise NotOnGohlkeError("No module named %s found." % dep)

def gohlke_install_plugin(plugin):
    if plugin in gohlke_aliases:
        plugin = gohlke_aliases[plugin]
    if _platform != 'win32':
        return False
    try:
        install_wheel(plugin)
        return True
    except IOError as e:
        print(e)
        print('Must have internet and administrator privileges. Also, make sure that all other Python programs are closed.')
    except NotOnGohlkeError:
        print("Not on Gohlke: %s" % plugin)
    except Exception as e:
        print("Could not install %s from Gohlke's website. %s" % (plugin, traceback.format_exc()))
    return False

def pip_install_plugin(plugin):
    if plugin in gohlke_aliases:
        plugin = gohlke_aliases[plugin]
    pip.main(['install', plugin])


def uninstall_numpy():
    print("Uninstalling old version of numpy")
    path = os.path.join(pip.locations.site_packages, 'numpy')
    if not os.path.exists(path):
        return True
    try:
        shutil.rmtree(path, True)
        if os.path.exists(path):
            i = 0
            while os.path.exists(path + (i * '_old')):
                i += 1
            shutil.move(path, path + (i * '_old'))
            print("Old numpy version not fully uninstalled")
    except Exception as e:
        print(e)
        return False
    return True

numpy_uninstalled = False

def test_numpy():
    global numpy_uninstalled
    if is_anaconda:
        return True
    loc = os.path.join(pip.locations.site_packages, 'numpy')
    if os.path.exists(loc):
        try:
            np = __import__('numpy')
            v = np.array(map(eval, np.__version__.split('.')[:2]))
            if not numpy_uninstalled and (any(v < [1, 11]) or np.__config__.blas_mkl_info == {} or np.__config__.lapack_mkl_info == {}):
                del np
                if not uninstall_numpy():
                    raise InstallFailedException('numpy')
                numpy_uninstalled = True
                return False
            else:
                return True
        except ImportError as e:
            pass
    return False

def install(name, fromlist=[], conda=False, installers=['gohlke', 'pip']):

    for installer in installers:
        eval('%s_install_plugin' % installer)(name)
        if test(name, fromlist, conda=conda):
            return True
    return False


def test(name, fromlist=[], conda=False):
    if name == 'numpy':
        return test_numpy()
    if conda and is_anaconda:
        return True
    package_dict = [open(f, 'r').readline().strip() for f in glob(os.path.join(pip.locations.site_packages, '%s-*'%name, 'top_level.txt'))]
    if len(package_dict) == 1:
        name = package_dict[0]
    if name in package_dict or os.path.exists(os.path.join(pip.locations.site_packages, name)):
        try:
            __import__(name, fromlist=fromlist)
            return True
        except Exception as e:
            if 'try recompiling' in str(e):
                return True
    return False

def check_dependencies(*deps):
    for dep in deps:
        if not test(dep):
            install(dep)

def main():
    version = sys.version_info.major, sys.version_info.minor, sys.version_info.micro
    if version[0] == 2 and version[1] <= 7 and version[2] <= 8:
        print('\n' + "=" * 20)
        print("\nWARNING: Flika was written for Python Versions 2.7.9+. Your current version is %d.%d.%d.  It is recommended that you remove Python and install a newer version." % (version))
        print('\n' + "=" * 20)

    def test_dependency(name, installers=['gohlke', 'pip'], fromlist=[], conda=False):
        if test(name, fromlist, conda=conda):
            return True
        if not install(name, installers=installers, fromlist=fromlist, conda=conda):
            raise InstallFailedException(name)
            print('\tERROR. Failed to install %s' % name)
            sys.exit(1)
        print('\n')

    test_dependency('PyQt4', installers=['gohlke'], fromlist=['QtCore', 'QtGui', 'uic'], conda=True)
    test_dependency('numpy', installers=['gohlke'], conda=True)
    test_dependency('scipy', fromlist=['special', 'ndimage'], conda=True)
    test_dependency('matplotlib', fromlist=['pyplot', 'cbook'], conda=True)
    test_dependency('skimage', fromlist=['draw'])
    for name in ('future', 'PIL', 'pyqtgraph', 'xmltodict', 'openpyxl', 'nd2reader'):
        test_dependency(name, installers=['pip', 'gohlke'])

if __name__ == '__main__' or INSTALL_DEPENDENCIES:
    pyversion=str(sys.version_info.major)+str(sys.version_info.minor)
    is_64bits = sys.maxsize > 2**32
    is_anaconda = 'Anaconda' in sys.version


    base_url='http://www.lfd.uci.edu/~gohlke/pythonlibs/'
    submodules = {'scipy': ['ndimage', 'special'], 'skimage': ['draw'], 'matplotlib': ['cbook']}
    gohlke_aliases = {"PIL": "Pillow", 'skimage': 'scikit_image'}

    try:
        import pip
    except:
        install_pip()
        import pip

    if float(pip.__version__[:3]) < 8.1:
        print("Upgrading Pip to latest version.")
        subprocess.call(['python', '-m', 'pip', 'install', '--upgrade', 'pip'])

    main()

