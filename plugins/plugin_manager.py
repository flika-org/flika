'''
@author: Brett Settle
'''
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
from xmltodict import parse
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

def load_plugin_xml(xml):
    try:
        od = parse(xml)
    except Exception as e:
        return None
    return od['plugin']

def get_plugin_paths():
    paths = []
    for p in glob(os.path.join(os.getcwd(), 'plugins', '*')):
        if os.path.isdir(p) and not p.startswith('__') and os.path.exists(os.path.join(p, 'info.xml')):
            paths.append(p)
    return paths

def build_plugin_submenu(module_name, parent_menu, layout_dict):
    for key, value in layout_dict.items():
        if type(value) != list:
            value = [value]
        if key == 'menu':
            for v in value:
                menu = parent_menu.addMenu(v["@name"])
                build_plugin_submenu(module_name, menu, v)
        elif key == 'action':
            for od in value:
                action = QAction(od['#text'], parent_menu, triggered = get_lambda(module_name, od['@location'], od['@function']))
                parent_menu.addAction(action)

def add_plugin_menu(plugin_name):
    menu = g.m.menuPlugins.addMenu(plugin_name)
    build_plugin_submenu(PluginManager.plugins[plugin_name]['base_dir'], menu, PluginManager.plugins[plugin_name]['menu_layout'])

def load_plugin_menu():
    PluginManager.load_installed_plugins()
    for plugin in sorted(PluginManager.plugins.keys()):
        try:
            add_plugin_menu(plugin)
        except Exception as e:
            print("Counld not load %s. %s" % (plugin, traceback.format_exc()))


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
    def load_plugins():
        PluginManager.plugins = {}
        PluginManager.load_installed_plugins()
        try:
            PluginManager.load_online_plugins()
        except IOError as e:
            print("Could no connect to the internet. %s" % traceback.format_exc())
        PluginManager.gui.updateList()

    @staticmethod
    def load_installed_plugins():
        for p in get_plugin_paths():
            try:
                mod_dict = load_plugin_xml(open(os.path.join(p, 'info.xml'), 'r').read())
                mod_dict['install_date'] = mod_dict['date']
                PluginManager.plugins[mod_dict['@name']] = mod_dict
            except Exception as e:
                print("Could not load info for %s. %s" % (os.path.basename(p), e))

    @staticmethod
    def load_online_plugins():
        for name, url in plugin_list.items():
            txt = urlopen(url).read()
            try:
                mod_dict = load_plugin_xml(txt)
                if name in PluginManager.plugins:
                    PluginManager.plugins[name].update(mod_dict)
                else:
                    PluginManager.plugins[name] = mod_dict
            except Exception as e:
                print("Could not load data from %s. %s" % (name, traceback.format_exc()))

    @staticmethod
    def show():
        if not hasattr(PluginManager, 'gui'):
            PluginManager.gui = PluginManager()
        g.m.statusBar().showMessage('Loading plugin information...')
        PluginManager.load_plugins()
        g.m.statusBar().showMessage('%d plugins successfully loaded' % (len(PluginManager.plugins)))
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
        self.actionCheck_For_Updates.triggered.connect(PluginManager.applyUpdates)
        self.searchBox.textChanged.connect(self.search)
        self.updateButton.clicked.connect(self.updateClicked)
        self.downloadButton.hide()
        self.updateButton.hide()
        self.docsButton.hide()

        self.searchButton.clicked.connect(lambda f: self.search(str(self.searchBox.text())))
        self.setWindowTitle('Plugin Manager')

    @staticmethod
    def applyUpdates():
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
                PluginManager.gui.statusBar.showMessage('No xml file found.')
            z.extractall("plugins")

        os.remove("install.zip")
        plugin = PluginManager.plugins[plugin_name]
        os.rename(os.path.join('plugins', folder_name), os.path.join('plugins', plugin['base_dir']))
        add_plugin_menu(plugin_name)
        PluginManager.plugins[plugin_name]['install_date'] = plugin['date']
        deps = PluginManager.plugins[plugin_name]['dependencies']['dependency']
        deps = [dep['@name'] for dep in deps]
        check_dependencies(*deps)
        PluginManager.gui.statusBar.showMessage('Successfully installed %s and it\'s plugins' % plugin_name)
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
        for act in g.m.menuPlugins.actions():
            if str(act.text()) == plugin_name:
                g.m.menuPlugins.removeAction(act)
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