# -*- coding: utf-8 -*-
import os
from importlib import resources

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
        path = resources.files('flika.images').joinpath(image_name)
        if path.exists():
            return str(path)
        else:
            raise RuntimeError(f"image does not exist: {image_name}")
    except NotImplementedError:  # workaround for mac app
        result = os.path.dirname(__file__)
        return os.path.join(result.replace('site-packages.zip', 'flika'),
                            image_name)
