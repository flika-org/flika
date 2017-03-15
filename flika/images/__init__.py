# -*- coding: utf-8 -*-
"""
Flika
@author: Kyle Ellefsen
@author: Brett Settle
@license: MIT
"""
import os
import pkg_resources

__all__ = ['image_path']

def image_path(image_name):
    """
    Return the absolute path to an image

    Parameters
    ----------
    image_name : str
       Name of image

    Returns
    -------
    path : str
      Full path to image
    """


    try:
        if pkg_resources.resource_exists('flika.images', image_name):
            return pkg_resources.resource_filename('flika.images', image_name)
        else:
            raise RuntimeError("image does not exist: %s" % image_name)
    except NotImplementedError:  # workaround for mac app
        result = os.path.dirname(__file__)
        return os.path.join(result.replace('site-packages.zip', 'flika'),
                            image_name)