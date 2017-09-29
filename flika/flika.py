# -*- coding: utf-8 -*-
from .logger import logger
logger.debug("Started 'reading flika.py'")
import sys, os
import platform
import optparse
import warnings
logger.debug("Started 'reading flika.py, importing numpy'")
import numpy as np
logger.debug("Completed 'reading flika.py, importing numpy'")
from .version import __version__
from .app.application import FlikaApplication


# for development purposes, add this if flika is not in your site-packages
# sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))



warnings.filterwarnings("ignore", category=np.VisibleDeprecationWarning)

def parse_arguments(argv):
    ''' Parses command line arguments for valid flika args

    Arguments:
        argv: Arguments passed to program

    Returns:
        A tuple of options, position arguments
    '''
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

    parser.add_option('-x', '--execute', action='store_true', dest='script',
                      help="Open file in script editor and run", default=False)
    parser.add_option('-t', '--test', action='store_true', dest='test',
                      help="Run test suite", default=False)
    parser.add_option('-v', '--verbose', action='store_true',
                      help="Increase the vebosity level", default=False)

    err_msg = verify(parser, argv)
    if err_msg:
        sys.stderr.write('\n%s\n' % err_msg)
        parser.print_help()
        sys.exit(1)

    return parser.parse_args(argv)

def verify(parser, argv):
    """verify(parser, argv)
    Check for input errors

    Arguments:
        parser: OptionParser instance
        argv (list): Argument list

    Returns:
        An error message in the event of an input error, or None
    """
    opts, args = parser.parse_args(argv)
    err_msg = None
    if opts.script and len(args) != 1:
        err_msg = "Must provide a script\n"

    return err_msg

def ipython_qt_event_loop_setup():
    try:
        __IPYTHON__
    except NameError:
        return #  If __IPYTHON__ is not defined, we are not in ipython
    else:
        print("Starting flika inside IPython")
        from IPython import get_ipython
        ipython = get_ipython()
        ipython.magic("gui qt")

def load_files(files):
    from .process.file_ import open_file
    for f in files:
        open_file(f)

def start_flika(files=[]):
    """Run a flika session and exit, beginning the event loop

    Parameters:
        files (list): An optional list of data files to load.

    Returns:
        A flika application object with optional files loaded
 
    """
    logger.debug("Started 'flika.start_flika()'")
    print('Starting flika')
    fa = FlikaApplication()
    load_files(files)
    fa.start()
    ipython_qt_event_loop_setup()
    logger.debug("Completed 'flika.start_flika()'")
    return fa

def exec_():
    fa = start_flika(sys.argv[1:])
    return fa.app.exec_()

def post_install():
    if platform.system() == 'Windows':
        print("Creating start menu shortcut...")
        import winshell
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'images', 'favicon.ico')
        flika_exe = os.path.join(sys.exec_prefix, 'Scripts', 'flika.exe')
        link_path = os.path.join(winshell.programs(), "flika.lnk")
        with winshell.shortcut(link_path) as link:
            link.path = flika_exe
            link.description = "flika"
            link.icon_location = (icon_path, 0)
        link_path = os.path.join(winshell.desktop(), "flika.lnk")
        with winshell.shortcut(link_path) as link:
            link.path = flika_exe
            link.description = "flika"
            link.icon_location = (icon_path, 0)

if __name__ == '__main__':
    start_flika(sys.argv[1:])

logger.debug("Completed 'reading flika.py'")
"""
def exec_(args=sys.argv):
    opt, args = parse_arguments(args[1:])

    if opt.verbose:
        logger.setLevel("INFO")

    logger.info("Input arguments: %s", sys.argv)

    start_flika(files=args)


def run(args=sys.argv):
    ''' open flika without running exec_. For debugging purposes
    '''
    opt, args = parse_arguments(args[1:])

    if opt.verbose:
        logger.setLevel("INFO")

    fa = FlikaApplication()
    fa.show()

    load_files(files=args)

    if 'PYCHARM_HOSTED' not in os.environ and 'SPYDER_SHELL_ID' not in os.environ:
        return fa.app.exec_()
"""

