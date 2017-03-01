#!/usr/bin/env python

from __future__ import absolute_import, division, print_function

import sys, os
import optparse

# for development purposes, add this if flika is not in your site-packages
#os.chdir(os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flika import __version__
from flika.logger import logger

import warnings
import numpy as np

warnings.filterwarnings("ignore", category=np.VisibleDeprecationWarning)

def parse_arguments(argv):
    ''' Parses command line arguments for valid Flika args

    :param argv: Arguments passed to program

    *Returns*
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
    """ Check for input errors

    :param parser: OptionParser instance
    :param argv: Argument list
    :type argv: List of strings

    *Returns*
    An error message, or None
    """
    opts, args = parser.parse_args(argv)
    err_msg = None
    if opts.script and len(args) != 1:
        err_msg = "Must provide a script\n"

    return err_msg

def load_files(files):
    from flika.process.file_ import open_file
    for f in files:
        open_file(f)

def start_flika(files=[]):
    print('Launching Flika')
    """Run a flika session and exit

    Parameters
    ----------
    files : list
        An optional list of data files to load.
 
    """
    import flika
    from flika.app import FlikaApplication

    fa = FlikaApplication()

    load_files(files)

    return fa.start()

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

    import flika
    from flika.app import FlikaApplication

    fa = FlikaApplication()
    fa.show()

    load_files(files=args)

    if 'PYCHARM_HOSTED' not in os.environ and 'SPYDER_SHELL_ID' not in os.environ:
        return fa.app.exec_()

if __name__ == '__main__':
    run()