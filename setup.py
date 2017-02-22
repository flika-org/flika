#!/usr/bin/env python
from __future__ import print_function

from setuptools import setup, find_packages
from distutils.core import Command

import os
import re
import sys
import subprocess

with open('flika/version.py') as infile:
    exec(infile.read())

try:
    import pypandoc
    LONG_DESCRIPTION = pypandoc.convert('README.md', 'rst')
except (IOError, ImportError):
    #if 'sdist' in sys.argv or 'register' in sys.argv:
    #    raise  # don't let this pass silently
    with open('README.md') as infile:
        LONG_DESCRIPTION = infile.read()


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

entry_points = """[flika.plugins]

[console_scripts]
flika = flika.main:run
"""

setup_requires = ['numpy', 'scipy']

# must have numpy and scipy installed already
install_requires = [
      'pandas>=0.14',
      'matplotlib>=1.4',
      'pyqtgraph>=0.9',
      'qtpy>=1.1',
      'setuptools>=1.0',
      'scikit-image',
      'scikit-learn',
      'ipython>=1.0',
      'ipykernel',
      'qtconsole',
      'pyopengl',
      'nd2reader']

setup(name='flika',
      version=__version__,
      cmdclass=cmdclass,
      description='Biological movie analysis software for calcium release activity',
      long_description=LONG_DESCRIPTION,
      author='Kyle Ellefsen, Brett Settle',
      author_email='kyleellefsen@gmail.com',
      url='http://flika-org.github.io',
      setup_requires=setup_requires,
      install_requires=install_requires,
      classifiers=[
          'Intended Audience :: Science/Research',
          'Operating System :: OS Independent',
          'Programming Language :: Python',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.3',
          'Programming Language :: Python :: 3.4',
          'Programming Language :: Python :: 3.5',
          'Topic :: Scientific/Engineering :: Visualization',
          ],
      packages=find_packages(),
      entry_points=entry_points,
      include_package_data=True,
      package_data={'gui': ['*.ui'],
                    'images': ['*.ico', '*.png', '*.txt', '*.tif']})
