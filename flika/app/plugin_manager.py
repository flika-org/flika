"""
Plugin manager for flika.
"""

from glob import glob
import os
import sys
import difflib
import zipfile
import shutil
import subprocess
import urllib
import pathlib
import platform
import packaging.version
import importlib.metadata
import threading
import tempfile
import dataclasses
import beartype
from qtpy import QtGui, QtWidgets, QtCore
from xml.etree import ElementTree

from flika.logger import logger
logger.debug("Started 'reading app/plugin_manager.py'")
from flika import global_vars as g
from flika.utils.misc import load_ui
from flika.images import image_path
from flika.utils.thread_manager import run_in_thread, ThreadController

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
    local_flika_directory : pathlib.Path = pathlib.Path.home() / '.FLIKA'
    plugin_directory : pathlib.Path = local_flika_directory / 'plugins'
    if not plugin_directory.exists():
        plugin_directory.mkdir(parents=True, exist_ok=True)
    if not plugin_directory.joinpath('__init__.py').exists():
        plugin_directory.joinpath('__init__.py').touch()  # Create empty __init__.py file
    if plugin_directory not in sys.path:
        sys.path.append(plugin_directory)
    if local_flika_directory not in sys.path:
        sys.path.append(local_flika_directory)
    return plugin_directory

plugin_dir = get_plugin_directory()


@beartype.beartype
def parse_plugin_info_xml(xml_str: str) -> dict:
    """
    Parse an XML string into a dictionary.
    """
    #logger.debug('Calling app.plugin_manager.parse')
    tree = ElementTree.fromstring(xml_str)
    def step(item: ElementTree.Element) -> dict:
        d = {}
        if item.text and item.text.strip():
            d['#text'] = item.text.strip()
        for k, v in item.items():
            d[f'@{k}'] = v
        for k in list(item):
            if k.tag not in d:
                d[k.tag] = step(k)
            elif isinstance(d[k.tag], list):
                d[k.tag].append(step(k))
            else:
                d[k.tag] = [d[k.tag], step(k)]
        if len(d) == 1 and '#text' in d:
            return d['#text']
        return d
    return step(tree)

def str2func(plugin_name: str, file_location: str, function: str) -> callable:
    '''
    takes plugin_name, path to object, function as arguments
    imports plugin_name.path and gets the function from that imported object
    to be run when an action is clicked
    '''
    __import__(plugin_name)
    plugin_dir_str = f"plugins.{plugin_name}.{file_location}"
    levels = function.split('.')
    module = __import__(plugin_dir_str, fromlist=[levels[0]]).__dict__[levels[0]]
    for i in range(1, len(levels)):
        module = getattr(module, levels[i])
    return module

@beartype.beartype
def build_submenu(module_name: str, parent_menu: QtWidgets.QMenu, layout_dict: dict) -> None:
    #logger.debug('Calling app.plugin_manager.build_submenu')
    if len(layout_dict) == 0:
        g.alert(f"Error building submenu for the plugin '{module_name}'. No items found in 'menu_layout' in the info.xml file.")
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

@beartype.beartype
@dataclasses.dataclass(frozen=True)
class PluginInfo:
    author: str  # The author of the plugin
    dependencies: list[str]  # The dependencies of the plugin
    description: str  # The description of the plugin
    directory: str  # The name of the module to import. This will be changed to 'module_name' eventually.
    documentation: str  # The documentation of the plugin
    full_path: pathlib.Path  # The full path to the plugin directory    
    info_url: str  # The URL of the plugin info
    last_modified: float  # The last modified date of the plugin
    latest_version: str  # The latest version of the plugin
    menu_layout: list[dict]  # The menu layout of the plugin
    name: str  # The human-readable name of the plugin
    url: str  # The URL of the plugin
    version: packaging.version.Version  # The version of the plugin


@beartype.beartype
class Plugin():
    def __init__(self, name=None, info_url=None):
        self.name : str = name
        self.info_url : str | None = info_url
        self.plugin_info : PluginInfo | None = None
        self.menu = None
        self.listWidget = QtWidgets.QListWidgetItem(self.name)
        self.loaded = False
        self.installed = False



        # self.directory : pathlib.Path | None = None
        # self.url : str | None = None
        # self.author : str | None = None
        # self.documentation : str | None = None
        # self.version : str = ''
        # self.latest_version : str = ''
        # self.description = ''
        # self.dependencies = []
        
        # self.info_url = info_url
        if info_url:
            self.plugin_info = self.get_plugin_info_from_url(info_url, plugin_dir)
            self.loaded = True

        # when fromLocal is called:
        #  self.listWidget.setIcon(QtGui.QIcon(image_path('check.png')))
        # self.loaded=True

    def lastModified(self) -> float:
        file_path : pathlib.Path = plugin_dir / self.plugin_info.directory
        return file_path.stat().st_mtime


    @staticmethod
    def fromLocal(plugin_path : pathlib.Path):
        #logger.debug('Calling app.plugin_manager.Plugin.fromLocal')
        with open(plugin_path / 'info.xml', 'r', encoding='utf-8') as f:
            info_xml_str = f.read()


        with open(plugin_path / 'about.html', 'r', encoding='utf-8') as f:
            try:
                description = str(f.read())
            except FileNotFoundError:
                description = "No local description file found"

        d: dict = parse_plugin_info_xml(info_xml_str)
        if 'dependencies' in d and 'dependency' in d['dependencies']:
            deps = d['dependencies']['dependency']
            dependencies = [d['@name'] for d in deps] if isinstance(deps, list) else [deps['@name']]

        
        author : str = d['author']
        dependencies : list[str] = dependencies
        description: str = description
        directory: str = d['directory']# The name of the module to import. This will be changed to 'module_name' eventually.
        documentation: str = d['documentation'] if 'documentation' in d else None # The documentation of the plugin
        full_path: pathlib.Path = plugin_dir / d['directory']  # The full path to the plugin directory    
        info_url: str = info_url # The URL of the plugin info
        last_modified: float = d['date']  # The last modified date of the plugin
        latest_version = d['version']  # The latest version of the plugin
        menu_layout: d['menu_layout']  # The menu layout of the plugin
        name: str = d['@name']  # The human-readable name of the plugin
        url: str | None = d['url'] if 'url' in d else None  # The URL of the plugin
        version: packaging.version.Version = d['version']  # The version of the plugin

        return PluginInfo(author=author,
                          dependencies=dependencies,
                          description=description,
                          directory=directory,
                          documentation=documentation,
                          full_path=full_path,
                          info_url=info_url,
                          last_modified=last_modified,
                          latest_version=latest_version,
                          menu_layout=menu_layout,
                          name=name,
                          url=url,
                          version=version)

    def bind_menu_and_methods(self):
        if len(self.menu_layout) > 0:
            self.menu = QtWidgets.QMenu(self.name)
            build_submenu(self.directory, self.menu, self.menu_layout)
        else:
            self.menu = None

    @staticmethod
    def get_plugin_info_from_url(
        info_url: str,
        plugin_dir: pathlib.Path,
    ) -> PluginInfo | Exception:
        """
        Update the plugin information from the online repository.
        Returns True if the update was successful, False otherwise.
        """
        info_url_xml : str = urllib.parse.urljoin(info_url, 'info.xml')
        try:
            info_xml_bytes : bytes = urllib.request.urlopen(info_url_xml).read()
            info_xml_str : str = info_xml_bytes.decode('utf-8')
        except urllib.error.HTTPError as e:
            return e

        plugin_info_dict: dict = parse_plugin_info_xml(info_xml_str)
        description_url: str = urllib.parse.urljoin(info_url, 'about.html')
        try:
            description: str = urllib.request.urlopen(description_url).read().decode('utf-8')
        except urllib.error.HTTPError as e:
            return e
        menu_layout = plugin_info_dict['menu_layout']
        if 'date' in plugin_info_dict:
            version = '.'.join(plugin_info_dict['date'].split('/')[2:] + plugin_info_dict['date'].split('/')[:2])
            latest_version = version
        else:
            version = ''
            latest_version = ''
        if 'dependencies' in plugin_info_dict and 'dependency' in plugin_info_dict['dependencies']:
            deps = plugin_info_dict.pop('dependencies')['dependency']
            dependencies: list[str] = [d['@name'] for d in deps] if isinstance(deps, list) else [deps['@name']]
        else:
            dependencies: list[str] = []

        d = plugin_info_dict
        author : str = d['author']
        dependencies = dependencies
        description = description
        directory: str = d['directory']# The name of the module to import. This will be changed to 'module_name' eventually.
        documentation: str = d['documentation']  # The documentation of the plugin
        full_path: pathlib.Path = plugin_dir / d['directory']  # The full path to the plugin directory    
        info_url: str = info_url # The URL of the plugin info
        last_modified: float = d['date']  # The last modified date of the plugin
        latest_version = latest_version  # The latest version of the plugin
        menu_layout: list[dict] = menu_layout  # The menu layout of the plugin
        name: str = d['@name']  # The human-readable name of the plugin
        url: str | None = d['url'] if 'url' in d else None  # The URL of the plugin
        version: packaging.version.Version = packaging.version.parse(d['version'])  # The version of the plugin

        return PluginInfo(author=author,
                          dependencies=dependencies,
                          description=description,
                          directory=directory,
                          documentation=documentation,
                          full_path=full_path,
                          info_url=info_url,
                          last_modified=last_modified,
                          latest_version=latest_version,
                          menu_layout=menu_layout,
                          name=name,
                          url=url,
                          version=version)

@beartype.beartype
class PluginManager(QtWidgets.QMainWindow):
    plugins: dict[str, Plugin] = {}
    thread_controllers: dict[str, ThreadController] = {}
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
    def load_online_plugin(plugin_name: str) -> None:
        logger.debug('Calling app.plugin_manager.PluginManager.load_online_plugin()')
        if plugin_name not in plugin_list:
            return
            
        # Check if there's already a thread loading this plugin
        if plugin_name in PluginManager.thread_controllers and PluginManager.thread_controllers[plugin_name].thread.isRunning():
            return
            
        def load_plugin_info() -> PluginInfo:
            """Function to load plugin info from its URL"""
            plugin : Plugin = PluginManager.plugins[plugin_name]
            info_url : str = plugin_list[plugin_name]
            plugin_info : PluginInfo | Exception = plugin.get_plugin_info_from_url(info_url, plugin_dir)
            if isinstance(plugin_info, Exception):
                raise plugin_info
            return plugin_info  # Return the plugin name to identify which plugin was loaded
            
        # Create a thread controller for this plugin
        controller = run_in_thread(load_plugin_info)
        PluginManager.thread_controllers[plugin_name] = controller
        
        # Connect signals
        def handle_error(error_msg):
            raise Exception(f"Error loading plugin {plugin_name}: {error_msg}")

        controller.connect('result', lambda plugin_info: PluginManager.gui.sigPluginLoaded.emit(plugin_info))
        controller.connect('error', lambda error_msg: handle_error)
        # controller.connect('error', lambda error_msg: logger.error(f"Error loading plugin {plugin_name}: {error_msg}"))
        
        if hasattr(PluginManager, 'gui'):
            PluginManager.gui.statusBar.showMessage(f'Loading plugin information for {plugin_name}...')
        logger.debug(f'Loading plugin information for {plugin_name}')

    def closeEvent(self, ev):
        if hasattr(PluginManager, 'thread_controllers'):
            # Make a copy of the keys to avoid modification during iteration
            controller_names = list(PluginManager.thread_controllers.keys())
            
            # First, try to abort all controllers
            for controller_name in controller_names:
                try:
                    controller = PluginManager.thread_controllers.get(controller_name)
                    if controller is None:
                        continue
                        
                    if hasattr(controller, 'thread') and controller.thread is not None:
                        try:
                            # Use safe try/except to check if thread is running
                            # This will catch RuntimeError if the C++ object is deleted
                            logger.debug(f"Attempting to abort thread controller for plugin: {controller_name}")
                            controller.abort()  # Our enhanced abort method handles deleted threads safely
                        except (RuntimeError, AttributeError) as e:
                            logger.debug(f"Thread object for {controller_name} not accessible: {str(e)}")
                            # Clean up to prevent future errors
                            controller.thread = None
                    else:
                        logger.debug(f"No valid thread found for {controller_name}")
                        
                except (RuntimeError, AttributeError, Exception) as e:
                    # If the thread has been deleted or is in an invalid state, log and continue
                    logger.warning(f"Error handling thread controller for plugin {controller_name}: {str(e)}")
            
            # Now clean up the dictionary
            for controller_name in controller_names:
                try:
                    if controller_name in PluginManager.thread_controllers:
                        controller = PluginManager.thread_controllers[controller_name]
                        # If thread is None or not valid, remove from dictionary
                        if not hasattr(controller, 'thread') or controller.thread is None:
                            PluginManager.thread_controllers.pop(controller_name, None)
                            logger.debug(f"Removed invalid thread controller for {controller_name}")
                except Exception as e:
                    logger.warning(f"Error cleaning up thread controller {controller_name}: {str(e)}")
                    # Just remove it to be safe
                    PluginManager.thread_controllers.pop(controller_name, None)

    @staticmethod
    def close():
        if hasattr(PluginManager, 'gui'):
            QtWidgets.QMainWindow.close(PluginManager.gui)

    def __init__(self):
        logger.debug('Calling app.plugin_manager.PluginManager.load_online_plugin()')

        super(PluginManager,self).__init__()
        load_ui('plugin_manager.ui', self, directory=pathlib.Path(__file__).parent)
        try:
            self.scrollAreaWidgetContents.setContentsMargins(10, 10, 10, 10)
        except:
            pass
        #self.pluginList.itemClicked.connect(self.pluginSelected)
        self.tutorialButton.clicked.connect(lambda : QtGui.QDesktopServices.openUrl(QtCore.QUrl('https://github.com/flika-org/flika_plugin_template')))
        self.open_plugins_directory_button.clicked.connect(lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl('file:///' + str(pathlib.Path.home() / '.FLIKA' / 'plugins'))))
        self.downloadButton.clicked.connect(self.downloadClicked)
        self.pluginList.currentItemChanged.connect(lambda new, old: self.pluginSelected(new))
        self.documentationButton.clicked.connect(self.documentationClicked)
        self.updateButton.clicked.connect(self.updateClicked)
        self.searchBox.textChanged.connect(self.showPlugins)
        self.searchButton.clicked.connect(lambda f: self.showPlugins(search_str=str(self.searchBox.text())))
        self.descriptionLabel.setOpenExternalLinks(True)
        self.refreshButton.pressed.connect(self.refresh_online_plugins)

        def update_plugin_info_async(plugin_info: PluginInfo):
            self.statusBar.showMessage(f'Finished loading {plugin_info.name}')
            PluginManager.plugins[plugin_info.name].plugin_info = plugin_info
            if PluginManager.plugins[plugin_info.name].listWidget.isSelected():
                PluginManager.gui.pluginSelected(plugin_info.name)
            #else:
                #self.showPlugins()
        self.sigPluginLoaded.connect(update_plugin_info_async)

        self.setWindowTitle('Plugin Manager')
        self.showPlugins()

    def showHelpScreen(self):
        self.pluginLabel.setText('')
        self.descriptionLabel.setHtml(helpHTML)
        self.downloadButton.setVisible(False)
        self.documentationButton.setVisible(False)
        self.updateButton.setVisible(False)
        self.infoLabel.setText('')

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
        if hasattr(plugin, 'documentation'):
            QtGui.QDesktopServices.openUrl(QtCore.QUrl(plugin.documentation))

    def updateClicked(self):
        p = str(self.pluginList.currentItem().text())
        plugin = self.plugins[p]
        PluginManager.removePlugin(plugin)
        PluginManager.downloadPlugin(plugin)

    def pluginSelected(self, item):
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
            msg = 'Loading information'
        else:
            msg = f'By {plugin.author}, Latest: {plugin.latest_version}'
            self.downloadButton.setVisible(True)
            
        # Initialize version objects for comparison
        version_obj = None
        latest_version_obj = None

        info : PluginInfo | None = plugin.plugin_info

        if info is not None:
            if info.version != '':
                version_obj = packaging.version.parse(info.version)
                if info.latest_version != '':
                    latest_version_obj = packaging.version.parse(info.latest_version)
                    if version_obj < latest_version_obj:
                        msg += '; <b>Update Available!</b>'

        # Only show update button if we have valid versions and an update is available
        self.updateButton.setVisible(info is not None and
                                     info.version != '' and 
                                     info.latest_version != '' and
                                     version_obj is not None and 
                                     latest_version_obj is not None and
                                     version_obj < latest_version_obj)
        self.downloadButton.setText('Install' if info is not None and info.version == '' else 'Uninstall')
        self.documentationButton.setVisible(info is not None and info.documentation is not None)
        if info is None or info.version == '':
            plugin.listWidget.setIcon(QtGui.QIcon())
        elif info.version < info.latest_version:
            plugin.listWidget.setIcon(QtGui.QIcon(image_path('exclamation.png')))
        else:
            plugin.listWidget.setIcon(QtGui.QIcon(image_path('check.png')))

        self.infoLabel.setText(msg)
        if info is not None:
            self.descriptionLabel.setHtml(info.description)
        else:
            self.descriptionLabel.setHtml('')

        # Finally, load the plugin info from the online repo if it's not already loaded
        if info is None or info.info_url is None:
            self.load_online_plugin(plugin.name)

    @staticmethod
    def local_plugin_paths() -> list[pathlib.Path]:
        paths : list[pathlib.Path] = []
        for path in glob(str(plugin_dir / '*')):
            if pathlib.Path(path).is_dir() and pathlib.Path(path).joinpath('info.xml').exists():
                paths.append(pathlib.Path(path))
        return paths

    def clearList(self):
        while self.pluginList.count() > 0:
            self.pluginList.takeItem(0)

    def showPlugins(self, search_str: str | None = None) -> None:
        self.clearList()
        if search_str is None or len(search_str) == 0:
            names = sorted(self.plugins.keys())
        else:
            def sort_func(name):
                name = str(name)
                return -difflib.SequenceMatcher(None, name.lower(), search_str.lower()).ratio() - int(search_str.lower() in name.lower())
            d = {name: sort_func(name) for name in self.plugins if sort_func(name) != 0}
            names = sorted(d.keys(), key=lambda a: d[a])
        for name in names:
            plug = PluginManager.plugins[name]
            info : PluginInfo | None = plug.plugin_info
            if info is None:
                plug.listWidget.setIcon(QtGui.QIcon())
            else:
                if info.version == '':
                    plug.listWidget.setIcon(QtGui.QIcon())
                elif info.version < info.latest_version:
                    plug.listWidget.setIcon(QtGui.QIcon(image_path('exclamation.png')))
                else:
                    plug.listWidget.setIcon(QtGui.QIcon(image_path('check.png')))
            self.pluginList.addItem(plug.listWidget)

    @staticmethod
    def removePlugin(plugin: Plugin) -> None:
        PluginManager.gui.statusBar.showMessage(f'Uninstalling {plugin.name}')
        if (plugin_dir / plugin.directory / '.git').is_dir():
            g.alert("This plugin's directory is managed by git. To remove, manually delete the directory")
            return False
        try:
            shutil.rmtree(plugin_dir / plugin.directory, ignore_errors=True)
            plugin.version = ''
            plugin.menu = None
            plugin.listWidget.setIcon(QtGui.QIcon())
            PluginManager.gui.statusBar.showMessage(f'{plugin.name} successfully uninstalled')
        except Exception as e:
            g.alert(f'Unable to remove the folder at {plugin.name}\n{e}\nDelete the folder manually to uninstall the plugin', title='Plugin Uninstall Failed')

        PluginManager.gui.pluginSelected(plugin.listWidget)
        plugin.installed = False

    @staticmethod
    def downloadPlugin(plugin: Plugin):
        PluginManager.gui.statusBar.showMessage('Installing plugin')
        if isinstance(plugin, str):
            if plugin in PluginManager.plugins:
                plugin = PluginManager.plugins[plugin]
            else:
                return
        if plugin.url is None:
            return
        failed = []
        
        # Use modern importlib.metadata instead of pkg_resources
        installed_packages = [dist.metadata['Name'] for dist in importlib.metadata.distributions()]
        
        PluginManager.gui.statusBar.showMessage(f'Installing dependencies for {plugin.name}')
        for pl in plugin.dependencies:
            try:
                if pl in installed_packages:
                    continue
                a = __import__(pl)
            except ImportError:
                res = subprocess.call([sys.executable, '-m', 'pip', 'install', f'{pl}', '--no-cache-dir'])
                if res != 0:
                    failed.append(pl)
        if failed:
            if platform.system() == 'Windows':
                QtGui.QDesktopServices.openUrl(QtCore.QUrl('http://www.lfd.uci.edu/~gohlke/pythonlibs/#'+pl))
                v = str(sys.version_info.major) + str(sys.version_info.minor)
                if platform.architecture()[0]=='64bit':
                    arch = '_amd64'
                else:
                    arch = '32'
                g.alert(f"""Failed to install the dependency '{pl}'. You must install {pl} manually.
Download {pl}-x-cp{v}-cp{v}m-win{arch}.whl.

Once the wheel is downloaded, drag it into flika to install.

Then try installing the plugin again.""")
            else:
                g.alert(f"Failed to install dependencies for {plugin.name}:\n{', '.join(failed)}\nYou must install them on your own before installing this plugin.")

            return


        if plugin.directory and (plugin_dir / plugin.directory).exists():
            g.alert(f'A folder with name {plugin.directory} already exists in the plugins directory. Please remove it to install this plugin!')
            return

        PluginManager.gui.statusBar.showMessage(f'Opening {plugin.url}')
        plugin_url : str | None = plugin.url
        if plugin_url is None:
            raise ValueError(f'Plugin {plugin.name} has no URL')

        # Download the plugin zip file
        try:
            plugin_zip_bytes : bytes = urllib.request.urlopen(plugin_url).read()
        except Exception as e:
            g.alert(f'Failed to connect to {plugin.url} to install the {plugin.name} flika Plugin. Check your internet connection and try again, or download the plugin manually.', title='Download Error')
            return

        # Extract the plugin zip file into a temporary file
        try:
            with tempfile.TemporaryFile() as tf:
                tf.write(plugin_zip_bytes)
                tf.seek(0)
                with zipfile.ZipFile(tf) as zip_file:
                    unzipped_plugin_path : pathlib.Path = plugin_dir / os.path.dirname(zip_file.namelist()[0])
                    zip_file.extractall(plugin_dir)

            # Move the unzipped plugin directory to the plugins directory
            plugin : Plugin = PluginManager.plugins[plugin.name]
            target_plugin_path : pathlib.Path = plugin_dir / plugin.directory
            os.rename(unzipped_plugin_path, target_plugin_path)
        except (PermissionError, Exception) as e:
            if pathlib.Path(unzipped_plugin_path).exists():
                shutil.rmtree(unzipped_plugin_path)
            if isinstance(e, PermissionError):
                g.alert(f"Unable to download plugin to {plugin.name}. Rerun flika as administrator and download the plugin again.", title='Permission Denied')
            else:
                g.alert(f"Error occurred while installing {plugin.name}.\n\t{e}", title='Plugin Install Failed')    
            return

        PluginManager.gui.statusBar.showMessage(f'Extracting {plugin.name}')
        plugin.version = plugin.latest_version
        plugin.listWidget.setIcon(QtGui.QIcon(image_path("check.png")))
        #plugin.menu = make_plugin_menu(plugin)
        plugin.menu = QtWidgets.QMenu(plugin.name)
        build_submenu(plugin.directory, plugin.menu, plugin.menu_layout)
        
        PluginManager.gui.statusBar.showMessage(f'Successfully installed {plugin.name} and its dependencies')
        PluginManager.gui.pluginSelected(plugin.listWidget)
        plugin.installed = True


def load_local_plugins():
    logger.debug("Started 'app.plugin_manager.load_local_plugins'")
    plugins = {n: Plugin(n) for n in plugin_list}
    installed_plugins = {}
    errors = []
    
    for pluginPath in PluginManager.local_plugin_paths():
        p = Plugin()
        p.fromLocal(pluginPath)
        try:
            p.bind_menu_and_methods()
            if p.name not in plugins.keys() or p.name not in installed_plugins:
                p.installed = True
                plugins[p.name] = p
                installed_plugins[p.name] = p
            else:
                error_msg = f'Could not load the plugin {p.name}. There is already a plugin with this same name. Change the plugin name in the info.xml file'
                errors.append(error_msg)
                g.alert(error_msg)
        except Exception:
            msg = f"Could not load plugin {pluginPath}"
            errors.append(msg)
            g.alert(msg)
            logger.error(msg)
            ex_type, ex, tb = sys.exc_info()
            sys.excepthook(ex_type, ex, tb)
    
    logger.debug("Completed 'app.plugin_manager.load_local_plugins'")
    return plugins, errors

# from flika.app.plugin_manager import *


logger.debug("Completed 'reading app/plugin_manager.py'")
logger.debug("Completed 'reading app/plugin_manager.py'")