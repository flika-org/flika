from glob import glob
import os, sys

from flika.utils import load_ui
from flika.images import image_path
from qtpy.QtCore import QUrl
from qtpy.QtWidgets import QListWidgetItem, QMenu, QMainWindow, QMessageBox, QAction, QAction, QApplication
from qtpy.QtGui import QIcon, QDesktopServices
import sys, difflib, zipfile, time, shutil, traceback
from urllib.request import urlopen
from pkg_resources import parse_version

import pip

from flika.plugins import plugin_list, plugin_path
import flika.global_vars as g
from xml.etree import ElementTree

def parse(x):
    
    tree = ElementTree.fromstring(x)
    def step(item):
        d = {}
        if item.text and item.text.strip():
            d['#text'] = item.text.strip()
        for k, v in item.items():
            d['@%s' % k] = v
        for k in item.getchildren():
            if k.tag not in d:
                d[k.tag] = step(k)
            elif type(d[k.tag]) == list:
                d[k.tag].append(step(k))
            else:
                d[k.tag] = [d[k.tag], step(k)]
        if len(d) == 1 and '#text' in d:
            return d['#text']
        return d
    return step(tree)

def str2func(plugin_name, file_location, function):
    '''
    takes plugin_name, path to object, function as arguments
    imports plugin_name.path and gets the function from that imported object
    to be run when an action is clicked
    '''
    plugin_dir = "flika.plugins.%s.%s" % (plugin_name, file_location)
    levels = function.split('.')
    try:
        module = __import__(plugin_dir, fromlist=[levels[0]]).__dict__[levels[0]]
    except:
        g.alert("Failed to import %s from module %s.\n%s" % (levels[0], plugin_dir, traceback.format_exc()))
        return None

    for i in range(1, len(levels)):
        try:
            module = getattr(module, levels[i])
        except:
            g.alert("Failed to import %s from module %s. Check name and try again." % (levels[i], module)) # only alerts on python 3?
    return module

def get_lambda(mod_name, path, func):
    def get_func():
        fun = lambda : str2func(mod_name, path, func)
        if fun:
            return fun()
    return get_func

def build_submenu(module_name, parent_menu, layout_dict):
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

def make_plugin_menu(plugin_name, base_dir, menu_layout):
    menu = QMenu(plugin_name)
    build_submenu(base_dir, menu, menu_layout)
    return menu

class Plugin():
    def __init__(self, name, info_url=None):
        self.name = name
        self.url = None
        self.documentation = None
        self.version = ''
        self.menu = None
        self.listWidget = QListWidgetItem(self.name)
        self.installed = False
        self.dependencies = []
        if info_url:
            self.link_info_url(info_url)
        

    @staticmethod
    def fromXML(info):
        name = info['@name']
        p = Plugin(name)
        p.base_dir = info['base_dir']
        if 'date' in info:
            info['version'] = '.'.join(info['date'].split('/')[2:] + info['date'].split('/')[:2])
            info.pop('date')
        p.version = info['version']
        p.latest_version = p.version
        p.author = info['author']
        p.description = info['description']
        p.url = info['url'] if 'url' in info else None
        p.documentation = info['documentation'] if 'documentation' in info else None
        if 'dependencies' in info and 'dependency' in info['dependencies']:
            deps = info['dependencies']['dependency']
            p.dependencies = [d['@name'] for d in deps] if isinstance(deps, list) else [deps['@name']]
        p.menu = make_plugin_menu(p.name, p.base_dir, info['menu_layout'])
        p.listWidget = QListWidgetItem(p.name)
        p.listWidget.setIcon(QIcon(image_path('check.png')))
        return p

    def link_info_url(self, url):
        self.info_url = url
        self.update_info()

    def update_info(self):
        if self.info_url == None:
            return False
        txt = urlopen(self.info_url).read()
        new_info = parse(txt)
        menu_layout = new_info.pop('menu_layout')
        if 'date' in new_info:
            new_info['version'] = '.'.join(new_info['date'].split('/')[2:] + new_info['date'].split('/')[:2])
            new_info.pop('date')
        new_info['latest_version'] = new_info.pop('version')
        if 'dependencies' in new_info and 'dependency' in new_info['dependencies']:
            deps = new_info.pop('dependencies')['dependency']
            self.dependencies = [d['@name'] for d in deps] if isinstance(deps, list) else [deps['@name']]
        self.__dict__.update(new_info)
        
        if self.version == '':
            self.listWidget.setIcon(QIcon())
        elif parse_version(self.version) < parse_version(self.latest_version):
            self.listWidget.setIcon(QIcon(image_path('exclamation.png')))
        else:
            self.listWidget.setIcon(QIcon(image_path('check.png')))



class PluginManager(QMainWindow):
    plugins = {}

    '''
    PluginManager handles installed plugins and the online plugin database
    | show() : initializes a gui as a static variable of the class, if necessary, and displays it. Call in place of constructor
    | close() : closes the gui if it exists
    | load_plugin_info() : reads installed plugins dict, and list of plugins from database for display
    '''
    @staticmethod
    def show():
        
        if not hasattr(PluginManager, 'gui'):
            PluginManager.gui = PluginManager()
        g.m.statusBar().showMessage('Loading plugin information...')
        PluginManager.load_online_plugins()
        g.m.statusBar().showMessage('%d plugins successfully loaded' % (len(PluginManager.plugins)))
        QMainWindow.show(PluginManager.gui)
        if not os.access(plugin_path(), os.W_OK):
            g.alert("Plugin folder write permission denied. Restart Flika as administrator to enable plugin installation.")

    @staticmethod
    def load_online_plugins():
        for p, url in plugin_list.items():
            if p in PluginManager.plugins:
                PluginManager.plugins[p].link_info_url(url)
            else:
                PluginManager.plugins[p] = Plugin(p, url)
        PluginManager.gui.showPlugins()

    @staticmethod
    def close():
        if hasattr(PluginManager, 'gui'):
            QMainWindow.close(PluginManager.gui)

    def __init__(self):
        super(PluginManager,self).__init__()
        load_ui("plugin_manager.ui", self, directory = os.path.dirname(__file__))
        self.setWindowIcon(QIcon(image_path('favicon.png')))
        try:
            self.scrollAreaWidgetContents.setContentsMargins(10, 10, 10, 10)
        except:
            pass
        self.pluginList.itemClicked.connect(self.pluginSelected)
        
        self.downloadButton.clicked.connect(self.downloadClicked)
        self.pluginList.currentItemChanged.connect(lambda new, old: self.pluginSelected(new))
        self.documentationButton.clicked.connect(self.documentationClicked)
        self.updateButton.clicked.connect(self.updateClicked)
        
        self.searchBox.textChanged.connect(self.showPlugins)
        self.searchButton.clicked.connect(lambda f: self.showPlugins(search_str=str(self.searchBox.text())))
        
        self.setWindowTitle('Plugin Manager')
        self.showPlugins()

    def downloadClicked(self):
        p = str(self.pluginList.currentItem().text())
        plugin = self.plugins[p]
        if self.downloadButton.text() == 'Download':
            PluginManager.downloadPlugin(plugin)
        else:
            PluginManager.removePlugin(plugin)

    def documentationClicked(self):
        p = str(self.pluginList.currentItem().text())
        plugin = self.plugins[p]
        if hasattr(plugin, "documentation"):
            QDesktopServices.openUrl(QUrl(plugin.documentation))

    def updateClicked(self):
        p = str(self.pluginList.currentItem().text())
        plugin = self.plugins[p]
        PluginManager.removePlugin(plugin)
        PluginManager.downloadPlugin(plugin)

    def pluginSelected(self, item):
        if item == None:
            if self.pluginLabel.text():
                self.pluginSelected(PluginManager.plugins[self.pluginLabel.text()].listWidget)
            return
        s = str(item.text())
        plugin = self.plugins[s]
        self.pluginLabel.setText(s)
        info = 'By %s, Latest: %s' % (plugin.author, plugin.latest_version)
        version = parse_version(plugin.version)
        latest_version = parse_version(plugin.latest_version)
        if plugin.version and version < latest_version:
            info += "; <b>Update Available!</b>"

        self.updateButton.setVisible(plugin.version != '' and version < latest_version)
        self.downloadButton.setText("Download" if plugin.version == '' else 'Remove')
        self.documentationButton.setVisible(plugin.documentation != None)

        self.infoLabel.setText(info)
        self.descriptionLabel.setText(plugin.description)

    @staticmethod
    def local_plugin_paths():
        paths = []
        for path in glob(os.path.join(plugin_path(), "*")):
            if os.path.isdir(path) and os.path.exists(os.path.join(path, 'info.xml')):
                paths.append(path)
        return paths

    def clearList(self):
        while self.pluginList.count() > 0:
            self.pluginList.takeItem(0)

    def showPlugins(self, search_str=None):
        self.clearList()
        if search_str == None or len(search_str) == 0:
            names = sorted(self.plugins.keys())
        else:
            def sort_func(name):
                name = str(name)
                return -difflib.SequenceMatcher(None, name.lower(), search_str.lower()).ratio() - int(search_str.lower() in name.lower())
            d = {name: sort_func(name) for name in self.plugins.keys() if sort_func(name) != 0}
            names = sorted(d.keys(), key=lambda a: d[a])
            print(d)
        for name in names:
            self.pluginList.addItem(PluginManager.plugins[name].listWidget)

    @staticmethod
    def removePlugin(plugin):
        PluginManager.gui.statusBar.showMessage("Uninstalling %s" % plugin.name)
        try:
            shutil.rmtree(os.path.join('plugins', plugin.base_dir), ignore_errors=True)
            plugin.version = ''
            plugin.menu = None
            plugin.listWidget.setIcon(QIcon())
            PluginManager.gui.statusBar.showMessage('%s successfully uninstalled' % plugin.name)
        except Exception as e:
            g.alert(title="Plugin Uninstall Failed", msg="Unable to remove the folder at %s\n%s\nDelete the folder manually to uninstall the plugin" % (plugin.name, e), icon=QMessageBox.Warning)

        PluginManager.gui.pluginSelected(plugin.listWidget)
        plugin.installed = False

    @staticmethod
    def downloadPlugin(plugin):
        if plugin.url == None:
            return
        
        failed = []
        dists = [a.project_name for a in pip.get_installed_distributions()]
        PluginManager.gui.statusBar.showMessage("Installing dependencies for %s" % plugin.name)
        for pl in plugin.dependencies:
            try:
                if pl in dists:
                    continue
                a = __import__(pl)
            except ImportError:
                res = pip.main(['install', pl])
                if res != 0:
                    failed.append(pl)
        if failed:
            g.alert("Failed to install dependencies for %s:\n%s\nYou must install them on your own before installing this plugin." % (plugin.name, ', '.join(failed)))
            return

        if os.path.exists(os.path.join('plugins', plugin.base_dir)):
            g.alert("A folder with name %s already exists in the plugins directory. Please remove it to install this plugin!" % plugin.name)
            return

        PluginManager.gui.statusBar.showMessage('Opening %s' % plugin.url)
        try:
            data = urlopen(plugin.url).read()
        except:
            g.alert(title="Download Error", msg="Failed to connect to %s to install the %s Flika Plugin. Check your internet connection and try again, or download the plugin manually." % (PluginManager.gui.link, plugin_name), icon=QMessageBox.Warning)
            return

        try:
            with open("install.zip", "wb") as output:
                output.write(data)

            with zipfile.ZipFile('install.zip', "r") as z:
                folder_name = os.path.dirname(z.namelist()[0])
                z.extractall("plugins")

            os.remove("install.zip")
            plugin = PluginManager.plugins[plugin.name]
            base_dir = os.path.join('plugins', plugin.base_dir)
            os.rename(os.path.join('plugins', folder_name), base_dir)
        except (PermissionError, Exception) as e:
            if os.path.exists(folder_name):
                shutil.rmtree(folder_name)
            if isinstance(e, PermissionError):
                g.alert("Unable to download plugin to %s. Rerun Flika as administor and download the plugin again." % plugin.name, title='Permission Denied')
            else:
                g.alert("Error occurred while installing %s.\n%s" % (plugin.name, e), title='Plugin Install Failed')    
            
            return
        
        PluginManager.gui.statusBar.showMessage('Extracting  %s' % plugin.name)
        plugin.version = plugin.latest_version
        plugin.listWidget.setIcon(QIcon(image_path("check.png")))

        
        PluginManager.gui.statusBar.showMessage('Successfully installed %s and it\'s plugins' % plugin.name)
        PluginManager.gui.pluginSelected(plugin.listWidget)
        plugin.installed = True

def load_local_plugins():
    for plugin in PluginManager.local_plugin_paths():
        try:
            text = open(os.path.join(plugin, 'info.xml'), 'r').read()
            p = Plugin.fromXML(parse(text))
            p.installed = True
            PluginManager.plugins[p.name] = p
        except Exception as e:
            g.alert(title="Menu Creation Error", message="Could not load %s. %s" % (plugin, traceback.format_exc()))
