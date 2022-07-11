# -*- coding: utf-8 -*-
import os, sys
from urllib.request import urlopen
from urllib.error import HTTPError
import re
import sys
from io import StringIO, BytesIO
import contextlib
import pathlib
import tempfile
from zipfile import ZipFile
import shutil
from subprocess import check_output
from qtpy import QtWidgets, QtGui, QtCore
from . import global_vars as g
from .version import __version__ as installed_flika_version



__all__ = ['checkUpdates']


def check_if_installed_via_pip():
    from distutils.sysconfig import get_python_lib
    s_loc = pathlib.Path(get_python_lib())
    f_loc = pathlib.Path(__file__)
    assert f_loc.exists()
    assert s_loc.exists()
    return s_loc in f_loc.parents


@contextlib.contextmanager
def capture():
    oldout, olderr = sys.stdout, sys.stderr
    try:
        out = [StringIO(), StringIO()]
        sys.stdout, sys.stderr = out
        yield out
    finally:
        sys.stdout, sys.stderr = oldout, olderr
        out[0] = out[0].getvalue()
        out[1] = out[1].getvalue()


def path_walk(top, topdown=False, followlinks=False):
    """
         See Python docs for os.walk, exact same behavior but it yields Path() instances instead
    """
    names = list(top.iterdir())

    dirs = (node for node in names if node.is_dir() is True)
    nondirs = (node for node in names if node.is_dir() is False)

    if topdown:
        yield top, dirs, nondirs

    for name in dirs:
        if followlinks or name.is_symlink() is False:
            for x in path_walk(name, topdown, followlinks):
                yield x

    if topdown is not True:
        yield top, dirs, nondirs


def get_pypi_version():
    out = check_output([sys.executable, '-m', 'pip', 'search', 'flika'])
    out = out.decode('utf-8')
    pypi_version = re.search(r'\((.*?)\)', out).group(1)
    return pypi_version


def get_github_version():
    url = "https://raw.githubusercontent.com/flika-org/flika/master/flika/version.py"
    try:
        data = urlopen(url).read().decode('utf-8')
    except Exception as e:
        g.alert("Connection Failed",
                "Cannot connect to flika Repository. Connect to the internet to check for updates. %s" % e)
        return
    github_version = re.match(r'__version__\s*=\s*\'([\d\.\']*)\'', data).group(1)
    return github_version


def checkUpdates():
    """
    If flika was installed via pip, this function uses pip to lookup the current version.

    If flika was downloaded directly from Github, this will check the current version in the master branch of the Github
    repository.

    """
    from pkg_resources import parse_version
    installed_via_pip = check_if_installed_via_pip()
    if installed_via_pip:
        latest_version = get_pypi_version()
    else:
        latest_version = get_github_version()
    message = "Installed version: " + installed_flika_version
    if latest_version is None:
        latest_version = 'Unknown'
    message += '\nLatest Version: ' + latest_version

    if parse_version(installed_flika_version) < parse_version(latest_version):
        if g.messageBox("Update Recommended", message + '\n\nWould you like to update?',
                      QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                      QtWidgets.QMessageBox.Question) == QtWidgets.QMessageBox.Yes:
            updateFlika()
    else:
        g.messageBox("Up to date", "Your version of Flika is up to date\n" + message)


def updateFlika():
    installed_via_pip = check_if_installed_via_pip()
    if installed_via_pip:
        out = check_output([sys.executable, '-m', 'pip', 'install', '-U', '--no-deps', 'flika'])
        out = out.decode('utf-8')
        print(out)
        g.alert('Update successful. Restart flika to complete update.')
    else:
        flika_location = pathlib.Path(__file__).parents[1]
        assert flika_location.stem == 'flika'
        if flika_location.joinpath('.git').exists():
            g.alert("This installation of flika is managed by git. Upgrade will not proceed. Use git to upgrade.")
            return False
        extract_location = tempfile.mkdtemp()
        url = urlopen('https://github.com/flika-org/flika/archive/master.zip')
        print("Downloading flika from Github to {}".format(extract_location))
        try:
            with ZipFile(BytesIO(url.read())) as z:
                folder_name = os.path.dirname(z.namelist()[0])
                if os.path.exists(extract_location):
                    shutil.rmtree(extract_location)
                z.extractall(extract_location)
        except Exception as e:
            g.messageBox("Update Error", "Failed to remove and replace old version of flika. %s" % e,
                         icon=QtWidgets.QMessageBox.Warning)
            return False
        extract_location = pathlib.Path(extract_location)
        new_flika_location = extract_location.joinpath('flika-master')
        assert new_flika_location.exists()
        try:
            for src_path, subs, fs in path_walk(new_flika_location):
                dst_path = flika_location.joinpath(src_path.relative_to(new_flika_location))
                for src_f in fs:
                    if src_f.__str__().endswith(('.py', '.ui', '.png', '.txt', '.xml', '.in', '.ico', '.rst')):
                        g.m.statusBar().showMessage('replacing %s' % src_f)
                        dst_f = flika_location.joinpath(src_f.relative_to(new_flika_location))
                        shutil.copy(src_f.__str__(), dst_f.__str__())
        except PermissionError as e:
            g.messageBox("Update Error", "Failed to remove and replace old version of flika. %s" % e,
                         icon=QtWidgets.QMessageBox.Warning)
            shutil.rmtree(extract_location.__str__())
            return False
        shutil.rmtree(extract_location.__str__())
        g.alert('Update successful. Restart flika to complete update.')