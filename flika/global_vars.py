import numpy as np
from urllib.request import urlopen
import re, os, pickle
from multiprocessing import cpu_count
from os.path import expanduser
from qtpy import QtWidgets
from flika import __version__

__all__ = ['Registry', 'Settings', 'setConsoleVisible',
            'DictRegistry', 'MenuRegistry', 'MenuActionRegistry',
            'menus', 'checkUpdates', 'alert']

class Registry(object):

    """Container to hold groups of objects or settings.

    Registry instances are used to track objects
    used for various tasks like data linking, widget creation, etc.
    They have the following properties:

        - A `members` property, which lists each item in the registry
        - A `default_members` function, which can be overridden to lazily
          initialize the members list
        - A call interface, allowing the instance to be used as a decorator
          for users to add new items to the registry in their config files
    """

    def __init__(self):
        self._members = []
        self._lazy_members = []
        self._loaded = False

    @property
    def members(self):
        """ A list of the members in the registry.
        The return value is a list. The contents of the list
        are specified in each subclass"""
        self._load_lazy_members()
        if not self._loaded:
            self._members = self.default_members() + self._members
            self._loaded = True

        return self._members

    def default_members(self):
        """The member items provided by default. These are put in this
        method so that code is only imported when needed"""
        return []

    def add(self, value):
        """
        Add a new item to the registry.
        """
        self._members.append(value)

    def remove(self, item):
        self._members.remove(item)

    def lazy_add(self, value):
        """
        Add a reference to a plugin which will be loaded when needed.
        """
        self._lazy_members.append(value)

    def _load_lazy_members(self):
        return
        from plugins import load_plugin
        while self._lazy_members:
            plugin = self._lazy_members.pop()
            load_plugin(plugin)

    def __iter__(self):
        return iter(self.members)

    def __len__(self):
        return len(self.members)

    def __contains__(self, value):
        return value in self.members

    def __call__(self, arg):
        """This is provided so that registry instances can be used
        as decorators. The decorators should add the decorated
        code object to the registry, and return the original function"""
        self.add(arg)
        return arg

class MenuActionRegistry(Registry):
    """
    Stores menubar actions and menus. Can be nested

    The members property is a list of menu actions, each represented as a
    ``(label, function)`` tuple.
    """

    def add(self, label, function):
        """
        Add a new menu action item
        :param label: Short label for the item
        :type label: str

        :param function: function
        :type function: function()
        """
        self.members.append((label, function))

    def __call__(self, label):
        def adder(func):
            self.add(label, func)
            return func
        return adder

class MenuRegistry(Registry):
    """
    Stores menus.

    The members property is a list of menus, each represented as a
    ``(label, function)`` tuple.
    """

    def add(self, label, menu):
        """
        Add a new menu
        :param label: Short label for the menu
        :type label: str

        :param function: function
        :type function: function()
        """
        self.members.append((label, menu))

    def __call__(self, label):
        def adder(menu):
            self.add(label, menu)
            return menu
        return adder

class DictRegistry(Registry):
    """
    Base class for registries that are based on dictionaries instead of lists
    of objects.
    """

    def __init__(self):
        self._members = {}
        self._lazy_members = []
        self._loaded = False

    @property
    def members(self):
        self._load_lazy_members()
        if not self._loaded:
            defaults = self.default_members()
            for key in defaults:
                if key in self._members:
                    self._members[key].extend(defaults[key])
                else:
                    self._members[key] = defaults[key]
            self._loaded = True
        return self._members

    def default_members(self):
        return {}


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
                        'show_all_points': False}

    def __init__(self):
        self.config_file=os.path.join(expanduser("~"),'.FLIKA','config.p' )
        self.d = Settings.initial_settings
        try:
            d=pickle.load(open(self.config_file, "rb" ))
            d = {k:d[k] for k in d if d[k] != None}
            self.d.update(d)
        except Exception as e:
            g.m.statusBar().showMessage("Failed to load settings file. %s\nDefault settings restored." % e)
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
    print('Flika - Alert!')
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