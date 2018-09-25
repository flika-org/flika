# -*- coding: utf-8 -*-
from ..logger import logger
logger.debug("Started 'reading app/plugin_manager.py'")

from glob import glob
import os, sys, difflib, zipfile, time, shutil, traceback, subprocess
from os.path import expanduser
from qtpy import QtGui, QtWidgets, QtCore
from urllib.request import urlopen
from urllib.error import HTTPError
from urllib.parse import urljoin
import threading
import tempfile
from xml.etree import ElementTree
import platform
import pkg_resources

from .. import global_vars as g
from ..utils.misc import load_ui
from ..images import image_path

plugin_list = {
    'Beam Splitter':    'https://raw.githubusercontent.com/BrettJSettle/BeamSplitter/master/',
    'Detect Puffs':     'https://raw.githubusercontent.com/kyleellefsen/detect_puffs/master/',
    'Global Analysis':  'https://raw.githubusercontent.com/BrettJSettle/GlobalAnalysisPlugin/master/',
    'Pynsight':         'http://raw.githubusercontent.com/kyleellefsen/pynsight/master/',
    'QuantiMus':        'http://raw.githubusercontent.com/Quantimus/quantimus/master/',
    'Rodent Tracker':   'https://raw.githubusercontent.com/kyleellefsen/rodentTracker/master/'
}

helpHTML = '''
<h1 style="width:100%; text-align:center">Welcome to the flika Plugin Manager</h1>
<p>Use the search bar to the left to find a specific plugin, or browse the list below it.</p>

<div>
    <h3>Develop a new plugin</h3>
    <p> If you would like to develop your own plugin for flika, follow these simple steps:</p>
    <ul list-style=none>
        <li>1. Download <a href="https://github.com/flika-org/flika_plugin_template">flika Plugin Template</a> and place it in your .FLIKA/plugins directory</li>
        <li>2. Update the info.xml file for your plugin</li>
        <li>3. Refer to the <a href="http://flika-org.github.io/writing_plugins.html">flika Documentation</a> for assistance developing your plugin.</li>
        <li>4. Update the description.html file for your plugin</li>
        <li>5. Send your plugin repo to us and we'll add it to the Plugin Manager!</li>
    </ul>
<div>
'''


def get_plugin_directory():
    logger.debug('Calling app.plugin_manager.get_plugin_directory')
    local_flika_directory = os.path.join(expanduser("~"), '.FLIKA')
    plugin_directory = os.path.join(expanduser("~"), '.FLIKA', 'plugins' )
    if not os.path.exists(plugin_directory):
        os.makedirs(plugin_directory)
    if not os.path.isfile(os.path.join(plugin_directory, '__init__.py')):
        open(os.path.join(plugin_directory, '__init__.py'), 'a').close()  # Create empty __init__.py file
    if plugin_directory not in sys.path:
        sys.path.append(plugin_directory)
    if local_flika_directory not in sys.path:
        sys.path.append(local_flika_directory)
    return plugin_directory

plugin_dir = get_plugin_directory()


def parse(x):
    #logger.debug('Calling app.plugin_manager.parse')
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
    #logger.debug("Started 'app.plugin_manager.str2func({}, {}, {})'".format(plugin_name, file_location, function))
    __import__(plugin_name)
    plugin_dir = "plugins.{}.{}".format(plugin_name, file_location)
    levels = function.split('.')
    module = __import__(plugin_dir, fromlist=[levels[0]]).__dict__[levels[0]]
    for i in range(1, len(levels)):
        module = getattr(module, levels[i])
    #logger.debug("Completed 'app.plugin_manager.str2func({}, {}, {})'".format(plugin_name, file_location, function))
    return module


def fake_str2func(plugin_name, file_location, function):
    def fake_fun():
        print(str(function))
        print('yay')
    return fake_fun

def build_submenu(module_name, parent_menu, layout_dict):
    #logger.debug('Calling app.plugin_manager.build_submenu')
    if len(layout_dict) == 0:
        g.alert("Error building submenu for the plugin '{}'. No items found in 'menu_layout' in the info.xml file.".format(module_name))
    for key, value in layout_dict.items():
        if type(value) != list:
            value = [value]
        if key == 'menu':
            for v in value:
                menu = parent_menu.addMenu(v["@name"])
                build_submenu(module_name, menu, v)
        elif key == 'action':
            for od in value:
                method = str2func(module_name, od['@location'], od['@function'])
                if method is not None:
                    action = QtWidgets.QAction(od['#text'], parent_menu, triggered = method)
                    parent_menu.addAction(action)


class Plugin():
    def __init__(self, name=None, info_url=None):
        self.name = name
        self.directory = None
        self.url = None
        self.author = None
        self.documentation = None
        self.version = ''
        self.latest_version = ''
        self.menu = None
        self.listWidget = QtWidgets.QListWidgetItem(self.name)
        self.installed = False
        self.description = ''
        self.dependencies = []
        self.loaded = False
        self.info_url = info_url
        if info_url:
            self.update_info()

    def lastModified(self):
        return os.path.getmtime(os.path.join(plugin_dir, self.directory))

    def fromLocal(self, path):
        #logger.debug('Calling app.plugin_manager.Plugin.fromLocal')
        text = open(os.path.join(path, 'info.xml'), 'r').read()
        info = parse(text)
        self.name = info['@name']
        self.directory = info['directory']
        self.version = info['version']
        self.latest_version = self.version
        self.author = info['author']
        try:
            self.description = str(open(os.path.join(path, 'about.html'), 'r').read())
        except FileNotFoundError:
            self.description = "No local description file found"
        self.url = info['url'] if 'url' in info else None
        self.documentation = info['documentation'] if 'documentation' in info else None
        if 'dependencies' in info and 'dependency' in info['dependencies']:
            deps = info['dependencies']['dependency']
            self.dependencies = [d['@name'] for d in deps] if isinstance(deps, list) else [deps['@name']]
        self.menu_layout = info.pop('menu_layout')
        self.listWidget = QtWidgets.QListWidgetItem(self.name)
        self.listWidget.setIcon(QtGui.QIcon(image_path('check.png')))
        self.loaded = True

    def bind_menu_and_methods(self):
        if len(self.menu_layout) > 0:
            self.menu = QtWidgets.QMenu(self.name)
            build_submenu(self.directory, self.menu, self.menu_layout)
        else:
            self.menu = None


    def update_info(self):
        logger.debug('Calling app.plugin_manager.update_info')
        if self.info_url is None:
            return False
        info_url = urljoin(self.info_url, 'info.xml')
        try:
            txt = urlopen(info_url).read()
        except HTTPError as e:
            g.alert("Failed to update information for {}.\n\t{}".format(self.name, e))
            return

        new_info = parse(txt)
        description_url = urljoin(self.info_url, 'about.html')
        try:
            new_info['description'] = urlopen(description_url).read().decode('utf-8')
        except HTTPError:
            new_info['description'] = "Unable to get description for {0} from <a href={1}>{1}</a>".format(self.name, description_url)
        self.menu_layout = new_info.pop('menu_layout')
        if 'date' in new_info:
            new_info['version'] = '.'.join(new_info['date'].split('/')[2:] + new_info['date'].split('/')[:2])
            new_info.pop('date')
        new_info['latest_version'] = new_info.pop('version')
        if 'dependencies' in new_info and 'dependency' in new_info['dependencies']:
            deps = new_info.pop('dependencies')['dependency']
            self.dependencies = [d['@name'] for d in deps] if isinstance(deps, list) else [deps['@name']]
        self.__dict__.update(new_info)
        self.loaded = True
        

class PluginManager(QtWidgets.QMainWindow):
    plugins = {}
    loadThread = None
    sigPluginLoaded = QtCore.Signal(str)
    '''
    PluginManager handles installed plugins and the online plugin database
    | show() : initializes a gui as a static variable of the class, if necessary, and displays it. Call in place of constructor
    | close() : closes the gui if it exists
    '''
    @staticmethod
    def show():
        logger.debug('Calling app.plugin_manager.PluginManager.show')
        if not hasattr(PluginManager, 'gui'):
            PluginManager.gui = PluginManager()
        PluginManager.gui.showPlugins()
        #PluginManager.load_online_plugins()
        QtWidgets.QMainWindow.show(PluginManager.gui)
        if not os.access(plugin_dir, os.W_OK):
            g.alert("Plugin folder write permission denied. Restart flika as administrator to enable plugin installation.")

        PluginManager.gui.showHelpScreen()


    @staticmethod
    def refresh_online_plugins():
        logger.debug('Calling app.plugin_manager.PluginManager.refresh_online_plugins()')
        for p in plugin_list.keys():
            PluginManager.load_online_plugin(p)

    @staticmethod
    def load_online_plugin(p):
        logger.debug('Calling app.plugin_manager.PluginManager.load_online_plugin()')
        if p not in plugin_list or PluginManager.loadThread is not None and PluginManager.loadThread.is_alive():
            return
        def loadThread():
            plug = PluginManager.plugins[p]
            plug.info_url = plugin_list[p]
            plug.update_info()
            PluginManager.gui.sigPluginLoaded.emit(p)
            #PluginManager.gui.statusBar.showMessage('Plugin information loaded successfully')

        PluginManager.loadThread = threading.Thread(None, loadThread)
        PluginManager.gui.statusBar.showMessage('Loading plugin information for {}...'.format(p))
        PluginManager.loadThread.start()

    def closeEvent(self, ev):
        if self.loadThread is not None and self.loadThread.is_alive():
            self.loadThread.join(0)

    @staticmethod
    def close():
        if hasattr(PluginManager, 'gui'):
            QtWidgets.QMainWindow.close(PluginManager.gui)

    def __init__(self):
        logger.debug('Calling app.plugin_manager.PluginManager.load_online_plugin()')

        super(PluginManager,self).__init__()
        load_ui("plugin_manager.ui", self, directory=os.path.dirname(__file__))
        try:
            self.scrollAreaWidgetContents.setContentsMargins(10, 10, 10, 10)
        except:
            pass
        #self.pluginList.itemClicked.connect(self.pluginSelected)
        self.tutorialButton.clicked.connect(lambda : QtGui.QDesktopServices.openUrl(QtCore.QUrl("https://github.com/flika-org/flika_plugin_template")))
        self.open_plugins_directory_button.clicked.connect(lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl("file:///" + os.path.expanduser('~/.FLIKA/plugins/'))))

        self.downloadButton.clicked.connect(self.downloadClicked)
        self.pluginList.currentItemChanged.connect(lambda new, old: self.pluginSelected(new))
        self.documentationButton.clicked.connect(self.documentationClicked)
        self.updateButton.clicked.connect(self.updateClicked)
        
        self.searchBox.textChanged.connect(self.showPlugins)
        self.searchButton.clicked.connect(lambda f: self.showPlugins(search_str=str(self.searchBox.text())))
        self.descriptionLabel.setOpenExternalLinks(True)
        
        self.refreshButton.pressed.connect(self.refresh_online_plugins)
        def updatePlugin(a):
            self.statusBar.showMessage("Finished loading {}".format(a))
            if PluginManager.plugins[a].listWidget.isSelected():
                PluginManager.gui.pluginSelected(a)
            #else:
                #self.showPlugins()
        self.sigPluginLoaded.connect(updatePlugin)

        self.setWindowTitle('Plugin Manager')
        self.showPlugins()

    def showHelpScreen(self):
        self.pluginLabel.setText("")
        self.descriptionLabel.setHtml(helpHTML)
        self.downloadButton.setVisible(False)
        self.documentationButton.setVisible(False)
        self.updateButton.setVisible(False)
        self.infoLabel.setText("")

    def downloadClicked(self):
        p = str(self.pluginList.currentItem().text())
        plugin = self.plugins[p]
        if self.downloadButton.text() == 'Install':
            PluginManager.downloadPlugin(plugin)
        else:
            PluginManager.removePlugin(plugin)

    def documentationClicked(self):
        p = str(self.pluginList.currentItem().text())
        plugin = self.plugins[p]
        if hasattr(plugin, "documentation"):
            QtGui.QDesktopServices.openUrl(QtCore.QUrl(plugin.documentation))

    def updateClicked(self):
        p = str(self.pluginList.currentItem().text())
        plugin = self.plugins[p]
        PluginManager.removePlugin(plugin)
        PluginManager.downloadPlugin(plugin)

    def pluginSelected(self, item):
        from pkg_resources import parse_version
        logger.debug('Calling app.plugin_manager.PluginManager.pluginSelected()')
        if item is None:
            if self.pluginLabel.text():
                self.pluginSelected(PluginManager.plugins[self.pluginLabel.text()].listWidget)
            return
        if isinstance(item, str):
            s = item
        else:
            s = str(item.text())
        plugin = self.plugins[s]
        self.pluginLabel.setText(s)
        if not plugin.loaded:
            info = "Loading information"
        else:
            info = 'By {}, Latest: {}'.format(plugin.author, plugin.latest_version)
            self.downloadButton.setVisible(True)
        version = parse_version(plugin.version)
        latest_version = parse_version(plugin.latest_version)
        if plugin.version and version < latest_version:
            info += "; <b>Update Available!</b>"

        self.updateButton.setVisible(plugin.version != '' and version < latest_version)
        self.downloadButton.setText("Install" if plugin.version == '' else 'Uninstall')
        self.documentationButton.setVisible(plugin.documentation != None)
        if plugin.version == '':
            plugin.listWidget.setIcon(QtGui.QIcon())
        elif parse_version(plugin.version) < parse_version(plugin.latest_version):
            plugin.listWidget.setIcon(QtGui.QIcon(image_path('exclamation.png')))
        else:
            plugin.listWidget.setIcon(QtGui.QIcon(image_path('check.png')))

        self.infoLabel.setText(info)
        self.descriptionLabel.setHtml(plugin.description)
        if plugin.info_url == None:
            self.load_online_plugin(plugin.name)

    @staticmethod
    def local_plugin_paths():
        paths = []
        for path in glob(os.path.join(plugin_dir, "*")):
            if os.path.isdir(path) and os.path.exists(os.path.join(path, 'info.xml')):
                paths.append(path)
        return paths

    def clearList(self):
        while self.pluginList.count() > 0:
            self.pluginList.takeItem(0)

    def showPlugins(self, search_str=None):
        from pkg_resources import parse_version
        self.clearList()
        if search_str == None or len(search_str) == 0:
            names = sorted(self.plugins.keys())
        else:
            def sort_func(name):
                name = str(name)
                return -difflib.SequenceMatcher(None, name.lower(), search_str.lower()).ratio() - int(search_str.lower() in name.lower())
            d = {name: sort_func(name) for name in self.plugins.keys() if sort_func(name) != 0}
            names = sorted(d.keys(), key=lambda a: d[a])
        for name in names:
            plug = PluginManager.plugins[name]
            if plug.version == '':
                plug.listWidget.setIcon(QtGui.QIcon())
            elif parse_version(plug.version) < parse_version(plug.latest_version):
                plug.listWidget.setIcon(QtGui.QIcon(image_path('exclamation.png')))
            else:
                plug.listWidget.setIcon(QtGui.QIcon(image_path('check.png')))
            self.pluginList.addItem(plug.listWidget)

    @staticmethod
    def removePlugin(plugin):
        PluginManager.gui.statusBar.showMessage("Uninstalling {}".format(plugin.name))
        if os.path.isdir(os.path.join(plugin_dir, plugin.directory, '.git')):
            g.alert("This plugin's directory is managed by git. To remove, manually delete the directory")
            return False
        try:
            shutil.rmtree(os.path.join(plugin_dir, plugin.directory), ignore_errors=True)
            plugin.version = ''
            plugin.menu = None
            plugin.listWidget.setIcon(QtGui.QIcon())
            PluginManager.gui.statusBar.showMessage('{} successfully uninstalled'.format(plugin.name))
        except Exception as e:
            g.alert(title="Plugin Uninstall Failed", msg="Unable to remove the folder at %s\n%s\nDelete the folder manually to uninstall the plugin" % (plugin.name, e), icon=QtWidgets.QMessageBox.Warning)

        PluginManager.gui.pluginSelected(plugin.listWidget)
        plugin.installed = False

    @staticmethod
    def downloadPlugin(plugin):
        PluginManager.gui.statusBar.showMessage("Installing plugin")
        if isinstance(plugin, str):
            if plugin in PluginManager.plugins:
                plugin = PluginManager.plugins[plugin]
            else:
                return
        if plugin.url is None:
            return
        failed = []
        dists = [a.project_name for a in pkg_resources.working_set]
        PluginManager.gui.statusBar.showMessage("Installing dependencies for %s" % plugin.name)
        for pl in plugin.dependencies:
            try:
                if pl in dists:
                    continue
                a = __import__(pl)
            except ImportError:
                res = subprocess.call([sys.executable, '-m', 'pip', 'install', '{}'.format(pl), '--no-cache-dir'])
                if res != 0:
                    failed.append(pl)
        if failed:
            if platform.system() == 'Windows':
                QtGui.QDesktopServices.openUrl(QtCore.QUrl("http://www.lfd.uci.edu/~gohlke/pythonlibs/#"+pl))
                v = str(sys.version_info.major) + str(sys.version_info.minor)
                if platform.architecture()[0]=='64bit':
                    arch = '_amd64'
                else:
                    arch = '32'
                g.alert("""Failed to install the dependency '{0}'. You must install {0} manually.
Download {0}-x-cp{1}-cp{1}m-win{2}.whl.

Once the wheel is downloaded, drag it into flika to install.

Then try installing the plugin again.""".format(pl, v, arch))
            else:
                g.alert("Failed to install dependencies for {}:\n{}\nYou must install them on your own before installing this plugin.".format(plugin.name, ', '.join(failed)))

            return

        if os.path.exists(os.path.join(plugin_dir, plugin.directory)):
            g.alert("A folder with name {} already exists in the plugins directory. Please remove it to install this plugin!".format(plugin.directory))
            return

        PluginManager.gui.statusBar.showMessage('Opening %s' % plugin.url)
        try:
            data = urlopen(plugin.url).read()
        except:
            g.alert(title="Download Error", msg="Failed to connect to %s to install the %s flika Plugin. Check your internet connection and try again, or download the plugin manually." % (PluginManager.gui.link, plugin.name), icon=QtWidgets.QMessageBox.Warning)
            return

        try:

            with tempfile.TemporaryFile() as tf:
                tf.write(data)
                tf.seek(0)
                with zipfile.ZipFile(tf) as z:
                    folder_name = os.path.dirname(z.namelist()[0])
                    z.extractall(plugin_dir)

            plugin = PluginManager.plugins[plugin.name]
            directory = os.path.join(plugin_dir, plugin.directory)
            os.rename(os.path.join(plugin_dir, folder_name), directory)
        except (PermissionError, Exception) as e:
            if os.path.exists(folder_name):
                shutil.rmtree(folder_name)
            if isinstance(e, PermissionError):
                g.alert("Unable to download plugin to {}. Rerun flika as administrator and download the plugin again.".format(plugin.name), title='Permission Denied')
            else:
                g.alert("Error occurred while installing {}.\n\t{}".format(plugin.name, e), title='Plugin Install Failed')    
            
            return
        
        PluginManager.gui.statusBar.showMessage('Extracting  %s' % plugin.name)
        plugin.version = plugin.latest_version
        plugin.listWidget.setIcon(QtGui.QIcon(image_path("check.png")))
        #plugin.menu = make_plugin_menu(plugin)
        plugin.menu = QtWidgets.QMenu(plugin.name)
        build_submenu(plugin.directory, plugin.menu, plugin.menu_layout)
        
        PluginManager.gui.statusBar.showMessage('Successfully installed {} and it\'s dependencies'.format(plugin.name))
        PluginManager.gui.pluginSelected(plugin.listWidget)
        plugin.installed = True


class Load_Local_Plugins_Thread(QtCore.QThread):
    plugins_done_sig = QtCore.Signal(dict)
    error_loading = QtCore.Signal(str)
    def __init__(self):
        QtCore.QThread.__init__(self)

    def __del__(self):
        self.wait()

    def run(self):
        #logger.debug("Started 'app.plugin_manager.load_local_plugins'")
        plugins = {n: Plugin(n) for n in plugin_list}
        installed_plugins = {}
        for pluginPath in PluginManager.local_plugin_paths():
            p = Plugin()
            p.fromLocal(pluginPath)
            try:
                p.bind_menu_and_methods()
                if p.name not in plugins.keys() or p.name not in installed_plugins.keys():
                    p.installed = True
                    plugins[p.name] = p
                    installed_plugins[p.name] = p
                else:
                    g.alert('Could not load the plugin {}. There is already a plugin with this same name. Change the plugin name in the info.xml file'.format(p.name))
            except Exception as e:
                msg = "Could not load plugin {}".format(pluginPath)
                self.error_loading.emit(msg)
                #g.alert(msg)
                logger.error(msg)
                ex_type, ex, tb = sys.exc_info()
                sys.excepthook(ex_type, ex, tb)
        self.plugins_done_sig.emit(plugins)
        #logger.debug("Completed 'app.plugin_manager.load_local_plugins'")

# from flika.app.plugin_manager import *


logger.debug("Completed 'reading app/plugin_manager.py'")