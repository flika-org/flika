#!/usr/bin/env python
"""
Commands to upload to pypi:

python setup.py sdist bdist_wheel
twine upload dist/*
"""
from setuptools import setup, find_packages
from distutils.core import Command
from setuptools.command.install import install
import platform
import os
import sys

with open('flika/version.py') as infile:
    __version__ = '0.0.0'
    exec(infile.read())  # This sets the __version__ variable.

with open('README.rst') as readme:
    LONG_DESCRIPTION = readme.read()
    LONG_DESCRIPTION = LONG_DESCRIPTION.replace('.. image:: flika/docs/_static/img/flika_screencapture.gif', '')

cmdclass = {}


class PyTest(Command):

    user_options = [('pytest-args=', 'a', "Arguments to pass to py.test")]

    def initialize_options(self):
        self.pytest_args = ""

    def finalize_options(self):
        pass

    def run(self):
        # import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.pytest_args + ' flika')
        sys.exit(errno)


cmdclass['test'] = PyTest

entry_points = """
[console_scripts]
flika = flika.flika:exec_
flika_post_install = flika.flika:post_install
"""

setup_requires = ['numpy', 'scipy']

# must have numpy and scipy installed already
install_requires = [
      'pandas>=0.14',
      'matplotlib>=1.4',
      'pyqtgraph>=0.9',
      'PyQt5>=5.8.0',
      'qtpy>=1.1',
      'setuptools>=1.0',
      'scikit-image',
      'scikit-learn',
      'ipython>=1.0',
      'ipykernel',
      'qtconsole',
      'pyopengl',
      'requests',
      'nd2reader',
      'markdown']

extras_require = {
    ':sys_platform == "win32"': ['winshell', 'pypiwin32']
}

setup(name='flika',
      version=__version__,
      cmdclass=cmdclass,
      description='An interactive image processing program for biologists written in Python.',
      long_description=LONG_DESCRIPTION,
      author='Kyle Ellefsen, Brett Settle',
      author_email='kyleellefsen@gmail.com',
      url='http://flika-org.github.io',
      setup_requires=setup_requires,
      install_requires=install_requires,
      extras_require=extras_require,
      license='MIT',
      classifiers=[
          'Intended Audience :: Science/Research',
          'Operating System :: OS Independent',
          'Programming Language :: Python',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.3',
          'Programming Language :: Python :: 3.4',
          'Programming Language :: Python :: 3.5',
          'Programming Language :: Python :: 3.6',
          'Topic :: Scientific/Engineering :: Visualization',
          ],
      packages=find_packages(),
      entry_points=entry_points,
      include_package_data=True,
      package_data={'gui': ['*.ui'],
                    'images': ['*.ico', '*.png', '*.txt', '*.tif']})









