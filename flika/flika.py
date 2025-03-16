# -*- coding: utf-8 -*-
"""
Main module for the flika application.
"""

# Standard library imports
import optparse
import os
import pathlib
import platform
import sys
import warnings
from typing import Any

# Set Jupyter to use platformdirs (fixes deprecation warning)
os.environ["JUPYTER_PLATFORM_DIRS"] = "1"

# Third-party imports
import beartype
import numpy as np

from flika.app.application import FlikaApplication

# Local application imports
from flika.logger import logger
from flika.version import __version__

# Filter out known warnings
warnings.filterwarnings("ignore", category=np.exceptions.VisibleDeprecationWarning)


@beartype.beartype
def parse_arguments(argv: list[str]) -> tuple[Any, list[str]]:
    """Parses command line arguments for valid flika args

    Arguments:
        argv: Arguments passed to program

    Returns:
        A tuple of options, position arguments
    """
    usage = """usage: %prog [FILE FILE...]

    # start a new session
    %prog

    # start a new session and load a file
    %prog image.tiff

    #start a new session with multiple files
    %prog image.tiff script.py

    #run a script
    %prog -x script.py

    #increase verbosity level
    %prog -v

    #run the test suite0

    %prog -t
    """
    parser = optparse.OptionParser(usage=usage, version=str(__version__))

    parser.add_option(
        "-x",
        "--execute",
        action="store_true",
        dest="script",
        help="Open file in script editor and run",
        default=False,
    )
    parser.add_option(
        "-t",
        "--test",
        action="store_true",
        dest="test",
        help="Run test suite",
        default=False,
    )
    parser.add_option(
        "-v",
        "--verbose",
        action="store_true",
        help="Increase the vebosity level",
        default=False,
    )

    err_msg = verify(parser, argv)
    if err_msg:
        sys.stderr.write(f"\n{err_msg}\n")
        parser.print_help()
        sys.exit(1)

    return parser.parse_args(argv)


@beartype.beartype
def verify(parser: optparse.OptionParser, argv: list[str]) -> str | None:
    """Check for input errors

    Arguments:
        parser: OptionParser instance
        argv: Argument list

    Returns:
        An error message in the event of an input error, or None
    """
    opts, args = parser.parse_args(argv)
    err_msg = None
    if opts.script and len(args) != 1:
        err_msg = "Must provide a script\n"

    return err_msg


@beartype.beartype
def ipython_qt_event_loop_setup() -> None:
    """Set up the IPython Qt event loop if running inside IPython."""
    try:
        __IPYTHON__
    except NameError:
        return  #  If __IPYTHON__ is not defined, we are not in ipython
    else:
        print("Starting flika inside IPython")
        from IPython import get_ipython

        ipython = get_ipython()
        ipython.run_line_magic("gui", "qt")


@beartype.beartype
def load_files(files: list[str]) -> None:
    from flika.process.file_ import open_file

    for f in files:
        open_file(f)


@beartype.beartype
def start_flika(files: list[str] | None = None) -> FlikaApplication:
    """Run a flika session and exit, beginning the event loop

    Parameters:
        files: An optional list of data files to load.

    Returns:
        A flika application object with optional files loaded
    """
    if files is None:
        files = []
    logger.debug("Started 'flika.start_flika()'")
    print("Starting flika")
    fa = FlikaApplication()
    load_files(files)
    fa.start()
    ipython_qt_event_loop_setup()
    logger.debug("Completed 'flika.start_flika()'")
    return fa


@beartype.beartype
def exec_() -> int:
    """Execute the flika application."""
    fa = start_flika(sys.argv[1:])
    return fa.app.exec_()


@beartype.beartype
def post_install() -> None:
    if platform.system() == "Windows":
        print("Creating start menu shortcut...")
        try:
            import importlib.resources as pkg_resources

            import winshell

            from flika import images

            # Use importlib.resources instead of os.path
            with pkg_resources.path(images, "favicon.ico") as icon_path:
                # Use Path for path manipulation
                flika_exe = pathlib.Path(sys.exec_prefix) / "Scripts" / "flika.exe"
                link_path = pathlib.Path(winshell.programs()) / "flika.lnk"
                with winshell.shortcut(str(link_path)) as link:
                    link.path = str(flika_exe)
                    link.description = "flika"
                    link.icon_location = (str(icon_path), 0)
                link_path = pathlib.Path(winshell.desktop()) / "flika.lnk"
                with winshell.shortcut(str(link_path)) as link:
                    link.path = str(flika_exe)
                    link.description = "flika"
                    link.icon_location = (str(icon_path), 0)
        except ImportError:
            print("winshell package not found. Shortcuts not created.")


if __name__ == "__main__":
    start_flika(sys.argv[1:])
