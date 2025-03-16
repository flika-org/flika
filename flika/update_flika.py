import os
import sys
import tomllib
import sysconfig
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
import packaging.version
from io import StringIO, BytesIO
import contextlib
import pathlib
import tempfile
from zipfile import ZipFile
import shutil
from subprocess import check_output
from qtpy import QtWidgets, QtGui, QtCore
import json

import flika.global_vars as g
from flika.logger import logger
from flika.version import __version__ as installed_flika_version


__all__ = [
    "checkUpdates",
    "check_if_installed_via_pip",
    "get_pypi_version",
    "get_github_version",
    "path_walk",
    "capture",
    "updateFlika",
    "check_updates_no_gui",
    "update_flika_no_gui",
]


def check_if_installed_via_pip() -> bool:
    """
    Check if flika is installed via pip by comparing its location with site-packages.

    Returns:
        bool: True if installed via pip, False otherwise.
    """
    s_loc = pathlib.Path(sysconfig.get_path("purelib"))
    f_loc = pathlib.Path(__file__).resolve()
    if not f_loc.exists():
        return False

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
    """See Python docs for os.walk, exact same behavior but it yields Path()
    instances instead"""
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


def get_pypi_version() -> str | None:
    """
    Get the latest version of flika available on PyPI.

    Returns:
        str | None: The latest version string if successful, None otherwise.
    """
    url = "https://pypi.org/pypi/flika/json"
    headers = {"User-Agent": f"flika/{installed_flika_version}"}

    try:
        req = Request(url, headers=headers)
        with urlopen(req, timeout=10) as response:
            if response.status != 200:
                g.alert(
                    "PyPI Connection Failed",
                    f"Failed to fetch version information. HTTP status: {response.status}",
                )
                return None

            pypi_data = json.load(response)
            latest_version = pypi_data.get("info", {}).get("version")

            if not latest_version:
                g.alert(
                    "Version Not Found",
                    "Could not find version information in PyPI response.",
                )
                return None

            return latest_version

    except HTTPError as e:
        g.alert("PyPI Connection Failed", f"HTTP Error: {e}")
        return None
    except URLError as e:
        g.alert("PyPI Connection Failed", f"Network Error: {e}")
        return None
    except json.JSONDecodeError as e:
        g.alert("PyPI Response Error", f"Failed to parse PyPI response: {e}")
        return None
    except Exception as e:
        g.alert("Unexpected Error", f"An unexpected error occurred: {e}")
        return None


def get_github_version() -> str | None:
    branch = "master"  # Use main branch for stable releases
    branch = "dev"  # temporarily for development
    url = f"https://raw.githubusercontent.com/flika-org/flika/{branch}/pyproject.toml"
    try:
        with urlopen(url, timeout=10) as response:
            if response.status != 200:
                g.alert(
                    "Connection Failed",
                    f"Failed to fetch version information. HTTP status: {response.status}",
                )
                return None

            pyproject_data = tomllib.load(response)
    except HTTPError as e:
        g.alert(
            "Connection Failed", f"Cannot connect to flika Repository. HTTP Error: {e}"
        )
        return None
    except URLError as e:
        g.alert(
            "Connection Failed",
            f"Cannot connect to flika Repository. Network Error: {e}",
        )
        return None
    except tomllib.TOMLDecodeError as e:
        g.alert("Parsing Error", f"Failed to parse pyproject.toml: {e}")
        return None
    except Exception as e:
        g.alert("Unexpected Error", f"An unexpected error occurred: {e}")
        return None
    github_version = pyproject_data.get("project", {}).get("version")
    return github_version


def check_updates_no_gui() -> tuple[bool, str, str | None]:
    """
    Check for updates to flika without displaying any GUI elements.

    Returns:
        tuple[bool, str, str | None]: A tuple containing:
            - Boolean indicating if update is available (True) or not needed (False)
            - Message with version information
            - Latest version string if found, None if error occurred
    """
    try:
        installed_via_pip = check_if_installed_via_pip()
        if installed_via_pip:
            latest_version = get_pypi_version()
            source = "PyPI"
        else:
            latest_version = get_github_version()
            source = "GitHub"

        message = f"Installed version: {installed_flika_version}"

        if latest_version is None:
            return (
                False,
                f"{message}\nUnable to determine the latest version from {source}.",
                None,
            )

        message += f"\nLatest version: {latest_version}"

        try:
            current_version = packaging.version.parse(installed_flika_version)
            remote_version = packaging.version.parse(latest_version)

            if current_version < remote_version:
                return (
                    True,
                    f"{message}\n\nA newer version is available.",
                    latest_version,
                )
            else:
                return (
                    False,
                    f"{message}\n\nYour version is up to date.",
                    latest_version,
                )

        except packaging.version.InvalidVersion:
            return (
                False,
                f"{message}\n\nCannot compare versions due to invalid format.",
                latest_version,
            )

    except Exception as e:
        error_message = f"Installed version: {installed_flika_version}\nError checking for updates: {str(e)}"
        return False, error_message, None


def checkUpdates() -> bool:
    """
    Check for updates to flika and prompt the user to update if a newer version is available.

    If flika was installed via pip, this function checks the PyPI repository.
    If flika was downloaded directly from Github, this checks the master branch on GitHub.

    Returns:
        bool: True if update check completed successfully, False otherwise.
    """
    try:
        # Use the non-GUI function to check for updates
        update_available, message, latest_version = check_updates_no_gui()

        if latest_version is None:
            # Error occurred during version check
            g.messageBox(
                "Update Check Failed",
                f"{message}\n\nPlease check your internet connection.",
            )
            return False

        if update_available:
            # Prompt user to update
            result = g.messageBox(
                "Update Recommended",
                f"{message}\n\nWould you like to update?",
                QtWidgets.QMessageBox.StandardButton.Yes
                | QtWidgets.QMessageBox.StandardButton.No,
                QtWidgets.QMessageBox.Icon.Question,
            )

            if result == QtWidgets.QMessageBox.StandardButton.Yes:
                update_success = updateFlika()
                if not update_success:
                    g.messageBox(
                        "Update Failed",
                        "The update process could not be completed. Please try again later.",
                    )
                    return False
                return True
        else:
            # Inform user they are up to date
            logger.debug(f"checkUpdates(): ")
            g.messageBox("Up to date", message)
            return True

        return True
    except Exception as e:
        g.alert(
            "Update Check Failed",
            f"An unexpected error occurred while checking for updates: {e}",
        )
        return False


def updateFlika() -> bool:
    """
    Update flika to the latest version and show GUI notifications of the process.

    If installed via pip, this uses pip to update.
    If installed from GitHub, downloads the latest version and updates files.

    Returns:
        bool: True if update was successful, False otherwise.
    """
    # Use the non-GUI function to perform the update
    success, message = update_flika_no_gui()

    if success:
        g.alert("Update Successful", message)
    else:
        g.alert("Update Failed", message)

    return success


def update_flika_no_gui() -> tuple[bool, str]:
    """
    Update flika to the latest version without any GUI interaction.

    Returns:
        tuple[bool, str]: A tuple containing:
            - Boolean indicating success (True) or failure (False)
            - Message describing the result or error
    """
    try:
        installed_via_pip = check_if_installed_via_pip()

        if installed_via_pip:
            try:
                out = check_output(
                    [
                        sys.executable,
                        "-m",
                        "pip",
                        "install",
                        "-U",
                        "--no-deps",
                        "flika",
                    ],
                    timeout=60,
                )
                out = out.decode("utf-8")
                return True, "Update successful. Restart flika to complete update."
            except Exception as e:
                return False, f"Failed to update flika via pip: {e}"
        else:
            flika_location = pathlib.Path(__file__).parents[1]
            if not flika_location.stem == "flika":
                return False, "Cannot determine flika installation location."

            if flika_location.joinpath(".git").exists():
                return (
                    False,
                    "This installation of flika is managed by git. Upgrade will not proceed. Use git to upgrade.",
                )

            extract_location = tempfile.mkdtemp()

            try:
                with urlopen(
                    "https://github.com/flika-org/flika/archive/master.zip", timeout=30
                ) as response:
                    if response.status != 200:
                        if os.path.exists(extract_location):
                            shutil.rmtree(extract_location)
                        return (
                            False,
                            f"Failed to download flika: HTTP status {response.status}",
                        )

                    print(f"Downloading flika from Github to {extract_location}")
                    with ZipFile(BytesIO(response.read())) as z:
                        folder_name = os.path.dirname(z.namelist()[0])
                        if os.path.exists(extract_location):
                            shutil.rmtree(extract_location)
                        z.extractall(extract_location)
            except (HTTPError, URLError) as e:
                if os.path.exists(extract_location):
                    shutil.rmtree(extract_location)
                return False, f"Failed to download flika: {e}"
            except Exception as e:
                if os.path.exists(extract_location):
                    shutil.rmtree(extract_location)
                return False, f"Failed to extract downloaded files: {e}"

            extract_location = pathlib.Path(extract_location)
            new_flika_location = extract_location.joinpath("flika-master")

            if not new_flika_location.exists():
                shutil.rmtree(extract_location.__str__())
                return False, "Downloaded files structure is not as expected"

            try:
                for src_path, subs, fs in path_walk(new_flika_location):
                    dst_path = flika_location.joinpath(
                        src_path.relative_to(new_flika_location)
                    )
                    # Ensure the destination directory exists
                    dst_path.mkdir(exist_ok=True, parents=True)
                    for src_f in fs:
                        if src_f.__str__().endswith(
                            (
                                ".py",
                                ".ui",
                                ".png",
                                ".txt",
                                ".xml",
                                ".in",
                                ".ico",
                                ".rst",
                            )
                        ):
                            print(f"Replacing {src_f}")
                            dst_f = flika_location.joinpath(
                                src_f.relative_to(new_flika_location)
                            )
                            shutil.copy(src_f.__str__(), dst_f.__str__())
            except PermissionError as e:
                shutil.rmtree(extract_location.__str__())
                return False, f"Failed to replace files: {e}. Check file permissions."
            except Exception as e:
                shutil.rmtree(extract_location.__str__())
                return False, f"Unexpected error while replacing files: {e}"

            shutil.rmtree(extract_location.__str__())
            return True, "Update successful. Restart flika to complete update."
    except Exception as e:
        return False, f"An unexpected error occurred: {e}"
