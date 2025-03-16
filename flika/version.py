"""
Module providing the flika version, extracted from pyproject.toml.
"""

import tomllib
from pathlib import Path


def _get_version() -> str:
    """
    Parse pyproject.toml to extract the flika version.
    
    Returns:
        str: The version string of flika.
    """
    # Find the pyproject.toml file relative to this file (version.py)
    module_path = Path(__file__).resolve()
    pyproject_path = None
    
    # Look in the parent directories of this file for pyproject.toml
    for path in [module_path.parent, *module_path.parent.parents]:
        potential_path = path / "pyproject.toml"
        if potential_path.exists():
            pyproject_path = potential_path
            break
    
    if pyproject_path is None:
        raise FileNotFoundError("Could not find pyproject.toml in parent directories of the module")
    
    # Parse the TOML file
    with open(pyproject_path, "rb") as f:
        pyproject_data = tomllib.load(f)
    
    # Extract the version
    flika_version = pyproject_data.get("project", {}).get("version")
    
    if flika_version is None:
        raise ValueError("Version not found in pyproject.toml")
    
    return flika_version


# Expose the version at module level
__version__ = _get_version()


