from .version import __version__
from .main import run, exec_

import logging, sys
from logging import NullHandler
logging.getLogger('flika').addHandler(NullHandler())

def handle_exception(exc_type, exc_value, exc_traceback):
    logging.getLogger('flika').warn(str(exc_type) + "; " + str(exc_value) + " " + str(exc_traceback.tb_frame.f_code))
    '''
    if exc_type == ImportError and exc_value.msg.startswith("No module named"):
        from tkinter import messagebox
        import tkinter
        root = tkinter.Tk()
        root.withdraw()
        result = messagebox.askquestion("Missing Dependency", "%s is not installed. Would you like to try to install it with pip?" % exc_value.name, icon='warning')
        if result == 'yes':
            import pip
            ret = pip.main(['install', exc_value.name])
            if ret == 0:
                messagebox.showinfo("Missing Dependency", "Successfully installed %s with pip. Restart flika to try again." % (exc_value.name))
            else:
                messagebox.showerror("Missing Dependency", "Failed to import %s. Could not install with pip. Try installing manually before running flika again." % (exc_value.name, message))
        return
        '''
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

sys.excepthook = handle_exception