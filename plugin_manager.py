from dependency_check import *
from glob import glob
import global_vars as g
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4 import uic
from PyQt4.QtCore import Qt
if sys.version_info.major==2:
    from urllib2 import urlopen
elif sys.version_info.major==3:
    from urllib.request import urlopen
import difflib
import zipfile


    
def str2func(plugin_name, object_location, function):
    '''
    takes plugin_name, path to object, function as arguments
    imports plugin_name.path and gets the function from that imported object
    to be run when an action is clicked
    '''
    plugins = "plugins.%s" % (plugin_name)
    module = __import__(plugins, fromlist=[object_location]).__dict__[object_location]
    while '.' in function:
        dot = function.find('.')
        func, function = function[:dot], function[dot + 1:]
        module = getattr(module, func)
    try:
        return getattr(module, function)
    except:
        raise Exception("Failed to import %s from module %s. Check name and try again." % (function, module)) # only alerts on python 3?

def get_lambda(mod_name, path, func):
    return lambda : str2func(mod_name, path, func)()

def build_plugin_menus(parentMenu, name, value, module_name):
    if isinstance(value, list):
        act = QAction(name, parentMenu, triggered=get_lambda(module_name, *value))
        parentMenu.addAction(act)
    elif isinstance(value, dict):
        menu = parentMenu.addMenu(name)
        for k, v in value.items():
            build_plugin_menus(menu, k, v, module_name)

def add_plugin_menu(plugin_path):
    init_file=os.path.join(plugin_path,'__init__.py')
    module_name=os.path.basename(plugin_path)
    if module_name.startswith('_') or not os.path.isfile(init_file):
        return #there must be a __init__.py file or the module won't load, ignore __pycache__
    module = __import__("plugins.%s" % module_name, fromlist=['dependencies', 'menu_layout'])
    if not hasattr(module, 'dependencies') or not hasattr(module, 'menu_layout'):
        print('Module %s must have a list of dependencies and menu layout dictionary' % module_name)
        return
    for dep in module.dependencies:
        install(dep)
    for menu_name, value in module.menu_layout.items():
        build_plugin_menus(g.m.menuPlugins, menu_name, value, module_name)

def init_plugins():
    paths = glob(os.path.join(os.getcwd(), 'plugins', '*'))
    for p in paths:
        try:
            add_plugin_menu(p)
        except Exception as e:
            print('Could not import %s: %s' % (os.path.basename(p), e))



class PluginManager(QMainWindow):
    def __init__(self):
        super(QMainWindow,self).__init__()
        uic.loadUi("gui/plugin_manager.ui", self)
        self.setPlugins(eval(urlopen('https://raw.githubusercontent.com/kyleellefsen/Flika_plugins/master/plugins.txt').read()))
        self.dl_link = None
        self.docs_link = None
        self.pluginList.itemClicked.connect(self.pluginSelected)
        self.downloadButton.clicked.connect(self.downloadClicked)
        self.docsButton.clicked.connect(self.docsClicked)
        self.searchBox.textChanged.connect(self.search)
        self.searchButton.clicked.connect(self.search)
        self.pluginList.setSortingEnabled(True)

    def search(self, search_str):
        self.sortPlugins(lambda name: -difflib.SequenceMatcher(None, name.lower(), search_str.lower()).ratio() - int(search_str.lower() in name.lower()))

    def sortPlugins(self, func):
        self.clearList()
        names = sorted([p['name'] for p in self.plugins], key=func)
        for name in names:
            self.pluginList.addItem(name)

    def clearList(self):
        while self.pluginList.count() > 0:
            self.pluginList.takeItem(0)

    def setPlugins(self, plugins):
        self.plugins = []
        self.clearList()

        for plugin in plugins:
            self.plugins.append(plugin)
            self.pluginList.addItem(plugin['name'])

    def pluginSelected(self, item):
        plugin = [p for p in self.plugins if p['name'] == item.text()][0]
        self.pluginLabel.setText(plugin['name'])
        self.descriptionLabel.setText(plugin['description'])
        info = ''
        if "author" in plugin:
            info += 'By %s. ' % plugin['author']
        if "date" in plugin:
            info += 'Written on %s' % plugin['date']
        self.infoLabel.setText(info)
        self.downloadButton.setEnabled(plugin['url'] != None)
        self.docsButton.setEnabled(plugin['docs'] != None)
        self.link = plugin['url']
        self.docs_link = plugin['docs']

    def downloadClicked(self):
        plugin_name = self.pluginList.currentItem().text()
        self.statusBar.showMessage('Opening %s' % self.link)
        data = urlopen(self.link).read()
        output = open("install.zip", "wb")
        output.write(data)
        output.close()
        self.statusBar.showMessage('Extracting  %s' % plugin_name)
        with zipfile.ZipFile('install.zip', "r") as z:
            folder_name = z.namelist()[0]
            z.extractall("plugins\\")
        os.remove("install.zip")
        os.rename("plugins\\%s" % folder_name, 'plugins\\%s' % plugin_name)
        add_plugin_menu("plugins\\%s" % plugin_name)
        self.statusBar.showMessage('Successfully installed %s' % plugin_name)

    def docsClicked(self):
        QDesktopServices.openUrl(QUrl(self.docs_link))

