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
from flika.app.plugin_utils import PluginInfo, plugin_info_urls_by_name, get_plugin_info_xml_from_url
import flika.app.plugin_utils as plugin_utils


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
    ensure_plugin_path()
    return plugin_directory

def ensure_plugin_path():
    """Ensure the plugin directory is in the Python path."""
    local_flika_directory : pathlib.Path = pathlib.Path.home() / '.FLIKA'
    plugin_directory : pathlib.Path = local_flika_directory / 'plugins'
    
    # Add to sys.path if not already present
    if str(plugin_directory) not in sys.path:
        sys.path.insert(0, str(plugin_directory))
    if str(local_flika_directory) not in sys.path:
        sys.path.insert(0, str(local_flika_directory))

plugin_dir = get_plugin_directory()




def str2func(plugin_name: str, file_location: str, function: str) -> callable:
    '''
    takes plugin_name, path to object, function as arguments
    imports plugin_name.path and gets the function from that imported object
    to be run when an action is clicked
    '''
    try:
        # Try importing through the plugins package first
        plugin_dir_str = f"plugins.{plugin_name}.{file_location}"
        __import__(plugin_dir_str)
        levels = function.split('.')
        module = __import__(plugin_dir_str, fromlist=[levels[0]]).__dict__[levels[0]]
        for i in range(1, len(levels)):
            module = getattr(module, levels[i])
        return module
    except (ImportError, ModuleNotFoundError):
        # If that fails, try direct import (legacy or during installation)
        try:
            __import__(plugin_name)
            plugin_dir_str = f"{plugin_name}.{file_location}"
            levels = function.split('.')
            module = __import__(plugin_dir_str, fromlist=[levels[0]]).__dict__[levels[0]]
            for i in range(1, len(levels)):
                module = getattr(module, levels[i])
            return module
        except (ImportError, ModuleNotFoundError):
            # Module doesn't exist yet, return None
            logger.warning(f"Could not import module {plugin_name}.{file_location} - may not be installed yet")
            return None

@beartype.beartype
def build_submenu(module_name: str, parent_menu: QtWidgets.QMenu, layout_data: dict | list, installing: bool = False) -> None:
    #logger.debug('Calling app.plugin_manager.build_submenu')
    
    # Convert list to appropriate dict format if needed
    if isinstance(layout_data, list):
        # Convert list of actions to dict with 'action' key
        layout_dict = {'action': layout_data}
    else:
        layout_dict = layout_data
        
    if len(layout_dict) == 0:
        g.alert(f"Error building submenu for the plugin '{module_name}'. No items found in 'menu_layout' in the info.xml file.")
    
    for key, value in layout_dict.items():
        if type(value) != list:
            value = [value]
        if key == 'menu':
            for v in value:
                menu = parent_menu.addMenu(v["@name"])
                build_submenu(module_name, menu, v, installing)
        elif key == 'action':
            for od in value:
                method = str2func(module_name, od['@location'], od['@function'])
                # Create QAction - if method is None, it will be a disabled placeholder
                action = QtWidgets.QAction(od['#text'], parent_menu)
                if method is not None:
                    action.triggered.connect(method)
                else:
                    # If we couldn't load the function, disable the action
                    action.setEnabled(False)
                parent_menu.addAction(action)





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
        
        if info_url:
            self.plugin_info = self.get_plugin_info_from_url(info_url, plugin_dir)
            self.loaded = True

    def lastModified(self) -> float:
        if self.plugin_info is None or not hasattr(self.plugin_info, 'directory'):
            return 0.0
        file_path : pathlib.Path = plugin_dir / self.plugin_info.directory
        if not file_path.exists():
            return 0.0
        return file_path.stat().st_mtime




    def bind_menu_and_methods(self):
        if self.plugin_info and self.plugin_info.menu_layout and len(self.plugin_info.menu_layout) > 0:
            self.menu = QtWidgets.QMenu(self.name)
            if self.plugin_info.directory:
                # Pass menu_layout directly - build_submenu now handles both dict and list formats
                build_submenu(self.plugin_info.directory, self.menu, self.plugin_info.menu_layout)
        else:
            self.menu = None

    def reload_and_bind_menu(self):
        """
        Reload the plugin module and rebind menu actions.
        Used after installation to make menu items active without requiring a restart.
        """
        # Remove old menu first if it exists
        if self.menu is not None:
            self.menu = None
            
        # Create new menu with fresh bindings
        if self.plugin_info and self.plugin_info.menu_layout and len(self.plugin_info.menu_layout) > 0:
            self.menu = QtWidgets.QMenu(self.name)
            if self.plugin_info.directory:
                # Special handling to force Python to reload the module
                module_name = self.plugin_info.directory
                try:
                    # First try to clean up any existing modules
                    module_to_remove = f"plugins.{module_name}"
                    if module_to_remove in sys.modules:
                        del sys.modules[module_to_remove]
                    
                    # Also clean up any submodules
                    for key in list(sys.modules.keys()):
                        if key.startswith(f"{module_to_remove}."):
                            del sys.modules[key]
                    
                    # Make sure plugin path is in sys.path
                    ensure_plugin_path()
                    
                    # Try to import the module directly to force Python to load it
                    try:
                        importlib.import_module(f"plugins.{module_name}")
                    except ImportError:
                        # Try to import directly if that fails
                        try:
                            importlib.import_module(module_name)
                        except ImportError:
                            pass
                            
                    # Now rebuild the menu
                    build_submenu(module_name, self.menu, self.plugin_info.menu_layout)
                    logger.debug(f"Successfully reloaded and bound menu for plugin {self.name}")
                    return True
                except Exception as e:
                    logger.error(f"Error reloading module for plugin {self.name}: {e}")
                    return False
        return False

    @staticmethod
    def fromLocal(plugin_path : pathlib.Path):
        plugin_info = plugin_utils.get_plugin_info_from_filesystem(plugin_path)
        if isinstance(plugin_info, FileNotFoundError):
            return plugin_info
        
        # Create a new plugin instance
        plugin = Plugin(plugin_info.name)
        plugin.plugin_info = plugin_info
        plugin.loaded = True
        # Don't set installed=True here - this should be done in load_local_plugins
        return plugin


    @staticmethod
    def get_plugin_info_from_url(
        info_url: str,
        plugin_dir: pathlib.Path,
    ) -> PluginInfo | Exception:
        """
        Update the plugin information from the online repository.
        Returns True if the update was successful, False otherwise.
        """
        plugin_info = plugin_utils.get_plugin_info_from_url(info_url)
        if isinstance(plugin_info, urllib.error.HTTPError):
            return plugin_info
        plugin_info = dataclasses.replace(plugin_info, full_path=plugin_dir / plugin_info.directory)
        return plugin_info

@beartype.beartype
class PluginManager(QtWidgets.QMainWindow):
    plugins: dict[str, Plugin] = {}
    thread_controllers: dict[str, ThreadController] = {}
    sigPluginLoaded = QtCore.Signal(PluginInfo)

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
        for p in plugin_info_urls_by_name.keys():
            PluginManager.load_online_plugin(p)

    @staticmethod
    def load_online_plugin(plugin_name: str) -> None:
        logger.debug('Calling app.plugin_manager.PluginManager.load_online_plugin()')
        if plugin_name not in plugin_info_urls_by_name.keys():
            return
            
        # Check if there's already a thread loading this plugin
        if plugin_name in PluginManager.thread_controllers and PluginManager.thread_controllers[plugin_name].thread.isRunning():
            return
            
        def load_plugin_info() -> PluginInfo:
            """Function to load plugin info from its URL"""
            plugin : Plugin = PluginManager.plugins[plugin_name]
            info_url : str = plugin_info_urls_by_name[plugin_name]
            plugin_info : PluginInfo | Exception = plugin.get_plugin_info_from_url(info_url, plugin_dir)
            if isinstance(plugin_info, Exception):
                raise plugin_info
            return plugin_info  # Return the plugin name to identify which plugin was loaded
            
        # Create a thread controller for this plugin
        controller = run_in_thread(load_plugin_info)
        PluginManager.thread_controllers[plugin_name] = controller
        
        # Connect signals

        controller.connect('result', lambda plugin_info: PluginManager.gui.sigPluginLoaded.emit(plugin_info))
        controller.connect('error', lambda error_msg: (_ for _ in ()).throw(Exception(f"Error loading plugin {plugin_name}: {error_msg}")))
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
            assert isinstance(plugin_info, PluginInfo)
            self.statusBar.showMessage(f'Finished loading {plugin_info.name}')
            
            # Update only the plugin_info and loaded flag
            plugin = PluginManager.plugins[plugin_info.name]
            plugin.plugin_info = plugin_info
            plugin.loaded = True
                
            # Update UI if this plugin is currently selected
            if plugin.listWidget.isSelected():
                self.pluginSelected(plugin_info.name)
            else:
                # Update the icon in the plugin list
                self.showPlugins()
        self.sigPluginLoaded.connect(update_plugin_info_async)

        self.setWindowTitle('Plugin Manager')
        self.showPlugins()

        # Set icons programmatically using image_path
        try:
            self.refreshButton.setIcon(QtGui.QIcon(image_path('refresh.png')))
            self.searchButton.setIcon(QtGui.QIcon(image_path('search.png')))
        except RuntimeError as e:
            logger.warning(f"Failed to load icons: {e}")

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
        
        info : PluginInfo | None = plugin.plugin_info
        
        if not plugin.loaded:
            msg = 'Loading information'
            self.downloadButton.setVisible(False)
            # Try to load the plugin info if it's not already being loaded
            if info is None or info.info_url is None:
                self.load_online_plugin(plugin.name)
        else:
            # If plugin is loaded, show its information and download button
            msg = ''
            if info is not None:
                if info.author:
                    msg += f'By {info.author}'
                if info.latest_version:
                    if msg:
                        msg += ', '
                    msg += f'Latest: {info.latest_version}'
            self.downloadButton.setVisible(True)
            
        # Initialize version objects for comparison
        version_obj = None
        latest_version_obj = None

        if info is not None:
            if info.version < info.latest_version:
                msg += '; <b>Update Available!</b>'

        # Only show update button if we have valid versions and an update is available
        self.updateButton.setVisible(info is not None and
                                     info.version != '' and 
                                     info.latest_version != '' and
                                     version_obj is not None and 
                                     latest_version_obj is not None and
                                     version_obj < latest_version_obj)
        
        # Set the download button text based on installation status
        self.downloadButton.setText('Install' if not plugin.installed else 'Uninstall')
        self.documentationButton.setVisible(info is not None and info.documentation is not None)
        
        # Set the icon based on installation status
        if info is None or not plugin.installed:
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
            
            # Set the icon based on installation status
            if info is None or not plug.installed:
                plug.listWidget.setIcon(QtGui.QIcon())
            elif info.version < info.latest_version:
                plug.listWidget.setIcon(QtGui.QIcon(image_path('exclamation.png')))
            else:
                plug.listWidget.setIcon(QtGui.QIcon(image_path('check.png')))
            self.pluginList.addItem(plug.listWidget)

    @staticmethod
    def removePlugin(plugin: Plugin) -> None:
        PluginManager.gui.statusBar.showMessage(f'Uninstalling {plugin.name}')
        
        # Check if the plugin directory exists and is under git control
        if plugin.plugin_info and plugin.plugin_info.directory:
            plugin_path = plugin_dir / plugin.plugin_info.directory
            if plugin_path.joinpath('.git').is_dir():
                g.alert("This plugin's directory is managed by git. To remove, manually delete the directory")
                return
            
            # Remove the plugin directory
            try:
                shutil.rmtree(plugin_path, ignore_errors=True)
                # Create a new PluginInfo with empty version to indicate uninstalled
                if plugin.plugin_info:
                    # Keep existing plugin_info but mark as uninstalled
                    plugin.installed = False
                    # Remove icon
                    plugin.listWidget.setIcon(QtGui.QIcon())
                    # Reset menu
                    plugin.menu = None
                PluginManager.gui.statusBar.showMessage(f'{plugin.name} successfully uninstalled')
            except Exception as e:
                g.alert(f'Unable to remove the folder at {plugin.name}\n{e}\nDelete the folder manually to uninstall the plugin', title='Plugin Uninstall Failed')

        # Update the UI for this plugin
        PluginManager.gui.pluginSelected(plugin.listWidget)

    @staticmethod
    def downloadPlugin(plugin: Plugin):
        PluginManager.gui.statusBar.showMessage('Installing plugin')
        if isinstance(plugin, str):
            if plugin in PluginManager.plugins:
                plugin = PluginManager.plugins[plugin]
            else:
                return
        
        # Make sure we have plugin info and URL
        if not plugin.plugin_info or not plugin.plugin_info.url:
            return
            
        failed = []
        
        # Use modern importlib.metadata instead of pkg_resources
        installed_packages = [dist.metadata['Name'] for dist in importlib.metadata.distributions()]
        
        # Install dependencies
        PluginManager.gui.statusBar.showMessage(f'Installing dependencies for {plugin.name}')
        for pl in plugin.plugin_info.dependencies:
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


        if plugin.plugin_info.directory and (plugin_dir / plugin.plugin_info.directory).exists():
            g.alert(f'A folder with name {plugin.plugin_info.directory} already exists in the plugins directory. Please remove it to install this plugin!')
            return

        PluginManager.gui.statusBar.showMessage(f'Opening {plugin.plugin_info.url}')
        plugin_url = plugin.plugin_info.url
        if not plugin_url:
            raise ValueError(f'Plugin {plugin.name} has no URL')

        # Download the plugin zip file
        try:
            plugin_zip_bytes : bytes = urllib.request.urlopen(plugin_url).read()
        except Exception as e:
            g.alert(f'Failed to connect to {plugin.plugin_info.url} to install the {plugin.name} flika Plugin. Check your internet connection and try again, or download the plugin manually.', title='Download Error')
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
            target_plugin_path : pathlib.Path = plugin_dir / plugin.plugin_info.directory
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
        
        # Create the menu
        plugin.menu = QtWidgets.QMenu(plugin.name)
        if plugin.plugin_info and plugin.plugin_info.directory and plugin.plugin_info.menu_layout:
            # Pass menu_layout directly with installing=True
            build_submenu(plugin.plugin_info.directory, plugin.menu, plugin.plugin_info.menu_layout, installing=True)
        
        # Mark as installed and update the UI
        plugin.installed = True
        plugin.listWidget.setIcon(QtGui.QIcon(image_path("check.png")))
        PluginManager.gui.statusBar.showMessage(f'Successfully installed {plugin.name} and its dependencies')
        
        # Try to reload the plugin module to make menu items active immediately
        success = plugin.reload_and_bind_menu()
        if not success:
            g.message(f"Plugin {plugin.name} has been installed. You may need to restart Flika to use all its features.")
            
        PluginManager.gui.pluginSelected(plugin.listWidget)


def load_local_plugins():
    logger.debug("Started 'app.plugin_manager.load_local_plugins'")
    plugins = {n: Plugin(n) for n in plugin_info_urls_by_name}
    installed_plugins = {}
    errors = []
    
    for pluginPath in PluginManager.local_plugin_paths():
        p = Plugin()
        plugin_info: PluginInfo | Exception = p.fromLocal(pluginPath)
        if isinstance(plugin_info, FileNotFoundError):
            raise plugin_info
        p.plugin_info = plugin_info
        try:
            p.bind_menu_and_methods()
            p.installed = True  # Mark as installed since it was found locally
            if p.name not in plugins.keys() or p.name not in installed_plugins:
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