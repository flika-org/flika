.. flika documentation master file, created by
   sphinx-quickstart on Thu Mar 23 10:24:30 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

flika: image processing for biologists
======================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:


flika makes it easy to write analyze images and movies of biological data. It is quick to 
get started, and is easy to extend by installing a wide variety of plugins or writing your own.


.. image:: _static/img/flika_screencapture.gif

Install
-------
Please see :ref:`installation` for instructions. flika runs on Windows, OSX, and Linux.

Features
--------
- Supports numerous types of image filetypes: .tif, .nd2, .stk, and more.
- Record the steps of your analysis in a script to automate a series of Flika commands.
- Python 3
- Rich plugin architecture, with many :ref:`external plugins <extplugins>` and a growing community.
- Open source under the `MIT`_ license.

Documentation
-------------

Please see :ref:`Contents <toc>` for full documentation, including installation and tutorials.


Bugs/Requests
-------------

Please use the `GitHub issue tracker <https://github.com/flika-org/flika/issues>`_ to submit bugs or request features.


Changelog
---------

Consult the :ref:`Changelog <changelog>` page for fixes and enhancements of each version.


Citations
---------
flika was created to automatically identify and automate the analysis of local Ca :sup:`2+` signals but has grown into a general analysis tool for studying biological images. When using flika, please cite:

	Ellefsen, K., Settle, B., Parker, I. & Smith, I. 
	An algorithm for automated detection, localization 
	and measurement of local calcium signals from 
	camera-based imaging. Cell Calcium. 56:147-156, 2014

Supported through National Institutes of Health grants GM 100201 to Ian Smith, and GM 048071 and 065830 to Ian Parker

License
-------

Distributed under the terms of the `MIT`_ license, flika is free and open source software.

.. _`MIT`: https://github.com/flika-org/flika/blob/master/LICENSE