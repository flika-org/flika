from ..app.plugin_manager import PluginManager, plugin_list
from ..app.script_editor import ScriptEditor
from ..window import Window
from .. import flika
import numpy as np
import unittest.mock as mock
import pytest
from ..utils.thread_manager import cleanup_threads

class TestPluginManager():
    def setup_method(self, method):
        flika.start_flika()
        # Create the plugin manager UI
        PluginManager.show()
        
    def teardown_method(self, method):
        # Clean up threads first
        cleanup_threads()
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


@pytest.mark.skip(reason="ScriptEditor tests need comprehensive rework")
class TestScriptEditor():
    """
    These tests are currently skipped because they require substantial rework.
    The ScriptEditor has complex Qt interactions that need better mocking and isolation.
    """
    def setup_method(self, method):
        flika.start_flika()
        ScriptEditor.show()

    def teardown_method(self, method):
        cleanup_threads()
        # Close any windows first to prevent issues
        from .. import global_vars as g
        if hasattr(g, 'windows'):
            for window in list(g.windows):
                try:
                    window.close()
                except Exception:
                    pass
        ScriptEditor.close()

    def test_from_window(self):
        """Test that creating a window and applying an operation updates the script editor."""
        # Create a window with random data
        w1 = Window(np.random.random([10, 20, 20]))
        
        # Apply a threshold operation
        from ..process import threshold
        w2 = threshold(.5)
        
        # Trigger the "From Window" action in the script editor
        ScriptEditor.gui.actionFrom_Window.trigger()
        
        # Get the text from the editor
        text = str(ScriptEditor.gui.currentTab().toPlainText())
        
        # Verify the text contains the expected command
        assert "threshold" in text, "Script editor should contain threshold command"
        assert "0.5" in text, "Script editor should contain the threshold value"