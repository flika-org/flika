
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
    # Find the pyproject.toml file - first check current directory, then parent directories
    current_path = Path.cwd()
    pyproject_path = None
    
    # Look in current and parent directories for pyproject.toml
    for path in [current_path, *current_path.parents]:
        potential_path = path / "pyproject.toml"
        if potential_path.exists():
            pyproject_path = potential_path
            break
    
    if pyproject_path is None:
        raise FileNotFoundError("Could not find pyproject.toml in current or parent directories")
    
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


