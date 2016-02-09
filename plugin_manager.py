from dependency_check import *
from glob import glob
import global_vars as g
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4 import uic
if sys.version_info.major==2:
    from urllib2 import urlopen
elif sys.version_info.major==3:
    from urllib.request import urlopen
import difflib
import zipfile
import time, shutil
import os.path
import traceback
from plugins.plugin_data import plugin_list
from collections import OrderedDict
sep=os.path.sep
    
def str2func(plugin_name, file_location, function):
    '''
    takes plugin_name, path to object, function as arguments
    imports plugin_name.path and gets the function from that imported object
    to be run when an action is clicked
    '''
    plugin_dir = "plugins.%s.%s" % (plugin_name, file_location)
    levels = function.split('.')
    try:
        module = __import__(plugin_dir, fromlist=[levels[0]]).__dict__[levels[0]]
    except:
        raise Exception("No attribute %s of module %s. %s" % (levels[0], plugin_dir, traceback.format_exc()))
    for i in range(1, len(levels)):
        try:
            module = getattr(module, levels[i])
        except:
            raise Exception("Failed to import %s from module %s. Check name and try again." % (levels[i], module)) # only alerts on python 3?
    return module
    

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
    plugin_dict = eval(open(os.path.join(plugin_path, '__init__.py'), 'r').read())
    if 'dependencies' not in plugin_dict or 'menu_layout' not in plugin_dict:
        print('Module %s must have a list of dependencies and menu layout dictionary' % plugin_dict['name'])
        return
    for dep in plugin_dict['dependencies']:
        install(dep)
    menu_dict = OrderedDict(plugin_dict['menu_layout'])
    for menu_name, value in menu_dict.items():
        build_plugin_menus(g.m.menuPlugins, menu_name, value, plugin_dict['base_dir'])

def get_plugin_paths():
    paths = []
    for p in glob(os.path.join(os.getcwd(), 'plugins', '*')):
        if os.path.isdir(p) and not p.startswith('__') and os.path.exists(os.path.join(p, '__init__.py')):
            paths.append(p)
    return paths

def init_plugins():
    for p in get_plugin_paths():
        try:
            add_plugin_menu(p)
        except Exception as e:
            print('Could not import %s: %s' % (os.path.basename(p), traceback.format_exc()))


class PluginManager(QMainWindow):
    plugins = {}

    '''
    PluginManager handles installed plugins and the online plugin database
    | show() : initializes a gui as a static variable of the class, if necessary, and displays it. Call in place of constructor
    | close() : closes the gui if it exists
    | load_plugin_info() : reads installed plugins dict, and list of plugins from database for display
    | 
    '''

    @staticmethod
    def update_available(plugin):
        if 'install_date' not in PluginManager.plugins[plugin]:
            return False
        installed_date = [int(i) for i in PluginManager.plugins[plugin]['install_date'].split('/')]
        latest_date = [int(i) for i in PluginManager.plugins[plugin]['date'].split('/')]
        if latest_date[2] > installed_date[2] or latest_date[0] > installed_date[0] or latest_date[1] > installed_date[1]:
            return True
        return False

    @staticmethod
    def load_plugin_info():
        PluginManager.plugins = {}
        PluginManager.load_installed_plugin_info()
        if not PluginManager.load_online_plugin_info():
            PluginManager.gui.updateList()

    @staticmethod
    def load_installed_plugin_info():
        for p in get_plugin_paths():
            base_dir = os.path.basename(p)
            try:
                mod_dict = eval(open(os.path.join(p, '__init__.py'), 'r').read())
                mod_dict['install_date'] = mod_dict['date']
                PluginManager.plugins[mod_dict['name']] = mod_dict
            except Exception as e:
                print("Could not load info for %s. %s" % (base_dir, e))

    @staticmethod
    def load_online_plugin_info():
        for name, url in plugin_list.items():
            try:
                mod_dict = eval(urlopen(url).read())
                if name in PluginManager.plugins:
                    PluginManager.plugins[name].update(mod_dict)
                else:
                    PluginManager.plugins[name] = mod_dict
            except IOError as e:
                g.m.statusBar().showMessage("No Internet connection. Please connect to the internet to access the plugin database")
                print(traceback.format_exc())
                return False
            except:
                print("Could not load data from %s. %s" % (name, traceback.format_exc()))
        PluginManager.gui.updateList()
        return True

    @staticmethod
    def show():
        if not hasattr(PluginManager, 'gui'):
            PluginManager.gui = PluginManager()
        g.m.statusBar().showMessage('Loading plugin information...')
        if PluginManager.load_plugin_info():
            g.m.statusBar().showMessage('Plugin Information Loaded')
        QMainWindow.show(PluginManager.gui)


    @staticmethod
    def close():
        if hasattr(PluginManager, 'gui'):
            QMainWindow.close(PluginManager.gui)

    def __init__(self):
        super(QMainWindow,self).__init__()
        uic.loadUi("gui/plugin_manager.ui", self)
        self.setWindowIcon(QIcon('images/favicon.png'))
        self.dl_link = None
        self.docs_link = None
        self.pluginList.itemClicked.connect(self.pluginSelected)
        self.downloadButton.clicked.connect(self.downloadClicked)
        self.pluginList.currentItemChanged.connect(lambda new, old: self.pluginSelected(new))
        self.docsButton.clicked.connect(self.docsClicked)
        self.actionCheck_For_Updates.triggered.connect(PluginManager.checkUpdates)
        self.searchBox.textChanged.connect(self.search)
        self.updateButton.clicked.connect(self.updateClicked)
        self.downloadButton.hide()
        self.updateButton.hide()
        self.docsButton.hide()

        self.searchButton.clicked.connect(lambda f: self.search(str(self.searchBox.text())))
        self.setWindowTitle('Plugin Manager')

    @staticmethod
    def checkUpdates():
        for plugin in PluginManager.plugins:
            if PluginManager.update_available(plugin):
                PluginManager.updatePlugin(plugin)

    def search(self, search_str):
        search_str = str(search_str)
        self.clearList()
        if len(search_str) == 0:
            names = sorted(self.plugins.keys())
        else:
            def sort_func(name):
                name = str(name)
                return -difflib.SequenceMatcher(None, name.lower(), search_str.lower()).ratio() - int(search_str.lower() in name.lower())
            names = sorted(self.plugins.keys(), key=sort_func)
        for name in names:
            item=PluginManager.makeListWidgetItem(name)
            self.pluginList.addItem(item)

    @staticmethod
    def makeListWidgetItem(name):
        item=QListWidgetItem(name)
        if 'install_date' in PluginManager.plugins[name]:
            if PluginManager.update_available(name):
                item.setIcon(QIcon('images/exclamation.png'))
            else:
                item.setIcon(QIcon('images/check.png'))
        return item

    def clearList(self):
        while self.pluginList.count() > 0:
            self.pluginList.takeItem(0)

    def updateList(self):
        self.clearList()
        for plugin in self.plugins:
            item=PluginManager.makeListWidgetItem(plugin)
            self.pluginList.addItem(item)

        if self.pluginList.currentItem() == None:
            self.pluginList.setCurrentItem(self.pluginList.item(0))

    def pluginSelected(self, item):
        if item == None:
            return
        plugin_name = str(item.text())
        plugin = self.plugins[plugin_name]
        self.pluginLabel.setText(plugin_name)
        self.descriptionLabel.setText("No description for plugin." if 'description' not in plugin else plugin['description'])
        info = ''
        if "author" in plugin:
            info += 'By %s. ' % plugin['author']
        if "date" in plugin:
            info += 'Written on %s' % plugin['date']
            if PluginManager.update_available(plugin_name):
                info += ". Update Available!"
                self.updateButton.show()
            else:
                self.updateButton.hide()
        self.downloadButton.setText('Uninstall' if 'install_date' in PluginManager.plugins[plugin_name] else 'Download')
        self.downloadButton.setVisible(True)
        self.infoLabel.setText(info)
        self.docsButton.setVisible('docs' in plugin)
        self.link = plugin['url']
        if 'docs' in plugin:
            self.docs_link = plugin['docs']

    @staticmethod
    def downloadPlugin(plugin_name):
        PluginManager.gui.statusBar.showMessage('Opening %s' % PluginManager.gui.link)
        data = urlopen(PluginManager.gui.link).read()
        output = open("install.zip", "wb")
        output.write(data)
        output.close()
        PluginManager.gui.statusBar.showMessage('Extracting  %s' % plugin_name)

        with zipfile.ZipFile('install.zip', "r") as z:
            try:
                folder_name = os.path.dirname(z.namelist()[0])
            except:
                PluginManager.gui.statusBar.showMessage('No __init__ file found.')
            z.extractall("plugins")

        os.remove("install.zip")
        plugin = eval(open(os.path.join('plugins', folder_name, '__init__.py'), 'r').read())
        os.rename(os.path.join('plugins', folder_name), os.path.join('plugins', plugin['base_dir']))
        add_plugin_menu(os.path.join('plugins', plugin['base_dir']))
        PluginManager.plugins[plugin_name]['install_date'] = plugin['date']
        PluginManager.gui.statusBar.showMessage('Successfully installed %s' % plugin_name)
        PluginManager.gui.pluginSelected(PluginManager.gui.pluginList.selectedItems()[0])
        
    def updateClicked(self):
        plugin_name = str(self.pluginList.currentItem().text())
        PluginManager.updatePlugin(plugin_name)
        PluginManager.gui.updateList()

    @staticmethod
    def updatePlugin(plugin_name):
        PluginManager.uninstallPlugin(plugin_name)
        PluginManager.downloadPlugin(plugin_name)
        PluginManager.gui.pluginSelected(PluginManager.gui.pluginList.selectedItems()[0])
        PluginManager.gui.statusBar.showMessage('%s updated' % plugin_name)

    @staticmethod
    def uninstallPlugin(plugin_name):
        base_dir = PluginManager.plugins[plugin_name]['base_dir']
        menu_names = OrderedDict(PluginManager.plugins[plugin_name]['menu_layout']).keys()
        for menu in g.m.menuPlugins.actions():
            if isinstance(menu, QMenu) and str(menu.menuAction().text()) in menu_names:
                g.m.menuPlugins.removeAction(menu.menuAction())
            elif str(menu.text()) in menu_names:
                g.m.menuPlugins.removeAction(menu)
        shutil.rmtree(os.path.join('plugins', base_dir))
        PluginManager.plugins[plugin_name].pop('install_date')
        PluginManager.gui.pluginSelected(PluginManager.gui.pluginList.selectedItems()[0])
        PluginManager.gui.statusBar.showMessage('%s successfully uninstalled' % plugin_name)

    def downloadClicked(self):
        plugin_name = str(self.pluginList.currentItem().text())
        if str(self.downloadButton.text()) == 'Download':
            PluginManager.downloadPlugin(plugin_name)
        elif str(self.downloadButton.text()) == 'Uninstall':
            PluginManager.uninstallPlugin(plugin_name)
        PluginManager.gui.updateList()

    def docsClicked(self):
        QDesktopServices.openUrl(QUrl(self.docs_link))
