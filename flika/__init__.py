from .version import __version__
from .flika import run, exec_

import logging, sys
from logging import NullHandler
logging.getLogger('flika').addHandler(NullHandler())

def handle_exception(exc_type, exc_value, exc_traceback):
    try:
        logging.getLogger('flika').warn(str(exc_type) + "\n" + str(exc_value) + " " + str(exc_traceback.tb_frame.f_code))
    except:
        logging.getLogger('flika').warn(str(exc_type) + "\n" + str(exc_value))
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

sys.excepthook = handle_exception