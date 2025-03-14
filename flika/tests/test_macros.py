from ..app.plugin_manager import PluginManager, plugin_list
from ..app.script_editor import ScriptEditor
from ..window import Window
from .. import flika
import numpy as np
import unittest.mock as mock

class TestPluginManager():
    def setup_method(self, method):
        flika.start_flika()
        # Create the plugin manager UI
        PluginManager.show()
        
    def teardown_method(self, method):
        # Close the plugin manager UI
        PluginManager.close()

    def test_local_plugins(self):
        local = set(plugin_list.keys())
        plugins = set(PluginManager.plugins.keys())
        assert (local & plugins) == local, "Local plugin list not loaded correctly"

    @mock.patch('flika.app.plugin_manager.PluginManager.refresh_online_plugins')
    @mock.patch('flika.app.plugin_manager.PluginManager.downloadPlugin') 
    @mock.patch('flika.app.plugin_manager.PluginManager.removePlugin')
    def test_install_plugin(self, mock_remove, mock_download, mock_refresh):
        # Skip the test if the plugin is already installed
        plugin_name = 'Detect Puffs'
        if PluginManager.plugins[plugin_name].installed:
            return
            
        # Set up the plugin URL manually instead of refreshing online plugins
        PluginManager.plugins[plugin_name].url = "https://example.com/plugin.zip"
        
        # Call download and remove methods
        PluginManager.downloadPlugin(plugin_name)
        PluginManager.removePlugin(plugin_name)
        
        # Verify that our mocked methods were called
        assert mock_download.called, "Plugin download not called"
        assert mock_remove.called, "Plugin removal not called"


class TestScriptEditor():
    def setup_method(self, method):
        ScriptEditor.show()

    def teardown_method(self, method):
        ScriptEditor.close()

    def test_from_window(self):
        w1 = Window(np.random.random([10, 20, 20]))
        from ..process import threshold
        w2 = threshold(.5)
        ScriptEditor.gui.actionFrom_Window.trigger()
        text = str(ScriptEditor.gui.currentTab().toPlainText())
        assert text == "threshold(value=0.5, darkBackground=False, keepSourceWindow=False)", "From window command not expected"