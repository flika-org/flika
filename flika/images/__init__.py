"""
Images for flika
"""
import pathlib
from importlib import resources

import beartype

__all__ = ['image_path']

@beartype.beartype
def image_path(image_name: str) -> str:
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
        # Traversable objects have is_file() method to check existence
        if path.is_file():
            return str(path)
        else:
            raise RuntimeError(f"image does not exist: {image_name}")
    except NotImplementedError:  # workaround for mac app
        result = pathlib.Path(__file__).parent
        # Use string replacement on the string representation of the path
        base_dir = str(result).replace('site-packages.zip', 'flika')
        full_path = pathlib.Path(base_dir) / image_name
        if full_path.exists():
            return str(full_path)  # Return full path as string, not just name
        else:
            raise RuntimeError(f"image does not exist: {image_name}")
