import numpy as np
from urllib.request import urlopen
import re, os, pickle
from multiprocessing import cpu_count
from os.path import expanduser
from qtpy import QtWidgets
from flika import __version__

__all__ = ['m', 'Settings', 'menus', 'checkUpdates', 'alert']


class Settings:
    initial_settings = {'filename': None, 
                        'internal_data_type': np.float64, 
                        'multiprocessing': True, 
                        'multipleTraceWindows': False, 
                        'mousemode': 'rectangle', 
                        'show_windows': True, 
                        'recent_scripts': [],
                        'recent_files': [],
                        'nCores':cpu_count(),
                        'debug_mode': False,
                        'point_color': '#ff0000',
                        'point_size': 5,
                        'roi_color': '#ffff00',
                        'rect_width': 5,
                        'rect_height': 5,
                        'show_all_points': False,
                        'default_rect_on_click': False}

    def __init__(self):
        self.config_file=os.path.join(expanduser("~"),'.FLIKA','config.p' )
        self.d = Settings.initial_settings
        try:
            d=pickle.load(open(self.config_file, "rb" ))
            d = {k:d[k] for k in d if d[k] != None}
            self.d.update(d)
        except Exception as e:
            from flika.logger import logger
            logger.info("Failed to load settings file. %s\nDefault settings restored." % e)
            self.save()
        self.d['mousemode'] = 'rectangle' # don't change initial mousemode

    def __getitem__(self, item):
        try:
            self.d[item]
        except KeyError:
            self.d[item]=Settings.initial_settings[item] if item in Settings.initial_settings else None
        return self.d[item]

    def __setitem__(self,key,item):
        self.d[key]=item
        self.save()

    def __contains__(self, item):
        return item in self.d

    def save(self):
        '''save to a config file.'''
        if not os.path.exists(os.path.dirname(self.config_file)):
            os.makedirs(os.path.dirname(self.config_file))
        pickle.dump(self.d, open( self.config_file, "wb" ))

    def setmousemode(self,mode):
        self['mousemode']=mode

    def setMultipleTraceWindows(self, f):
        self['multipleTraceWindows'] = f

    def setInternalDataType(self, dtype):
        self['internal_data_type'] = dtype
        print('Changed data_type to {}'.format(dtype))

    def update(self, d):
        self.d.update(d)



def alert(msg, title="Flika - Alert!", buttons=QtWidgets.QMessageBox.Ok, icon=QtWidgets.QMessageBox.Information):
    print(title)
    print(msg)
    msgbx = QtWidgets.QMessageBox(m)
    msgbx.setIcon(icon)
    msgbx.setText(msg)
    msgbx.setWindowTitle(title)
    msgbx.show()
    m.statusBar().showMessage(msg)
    desktopSize = QtWidgets.QDesktopWidget().screenGeometry()
    top = (desktopSize.height() / 2) - (msgbx.size().height() / 2)
    left = (desktopSize.width() / 2) - (msgbx.size().width() / 2)
    msgbx.move(left, top)
    dialogs.append(msgbx)
    return msgbx

def checkUpdates():
    m.statusBar().showMessage("Checking if Flika is outdated...")
    import subprocess
    update = False
    proc = subprocess.Popen(["pip", "list", "--outdated", "--format=legacy"], stdout=subprocess.PIPE)
    out = proc.communicate()[0]
    out = out.decode('ascii')
    message = ''
    for l in out.split('\r\n'):
        if l.startswith('flika ('):
            message = l
            update = True
            break
    if not update:
        a = alert("Flika %s is the latest version" % __version__, title="Up to date")
        return
    else:
        alert("Flika %s is out of date. Run 'pip install flika --upgrade --no-dependencies' in a terminal to update flika." % __version__, title="Update Available")
        return
    msgbx = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Question, "Update Recommended", message + '\nWould you like to update?', QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
    msgbx.show()
    while msgbx.isVisible(): QtWidgets.QApplication.instance().processEvents()
    if msgbx.result() == QtWidgets.QMessageBox.Yes:
        print("OK")
        return
        command = "install --upgrade flika --no-dependencies".split(' ')
        import pip
        ret = pip.main(command)
        if ret == 0:
            alert("Successfully updated. Restart Flika", title="Update Successful")
            m.close()
        else:
            alert("Failed to update Flika.")

menus = []

m = None # will be main window
windows = []
traceWindows = []
dialogs = []
currentWindow = None
currentTrace = None
clipboard = None