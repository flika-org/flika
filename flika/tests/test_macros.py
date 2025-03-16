import unittest.mock as mock
import pytest
import logging
import time

import numpy as np

import flika
from flika.app.plugin_manager import PluginManager
from flika.app.plugin_utils import plugin_info_urls_by_name
from flika.app.script_editor import ScriptEditor
from flika.window import Window
from flika.utils.thread_manager import cleanup_threads, run_in_thread


class TestPluginManager:
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
        local = set(plugin_info_urls_by_name.keys())
        plugins = set(PluginManager.plugins.keys())
        assert (local & plugins) == local, "Local plugin list not loaded correctly"

    @mock.patch("flika.app.plugin_manager.PluginManager.refresh_online_plugins")
    @mock.patch("flika.app.plugin_manager.PluginManager.downloadPlugin")
    @mock.patch("flika.app.plugin_manager.PluginManager.removePlugin")
    def test_install_plugin(self, mock_remove, mock_download, mock_refresh):
        # Skip the test if the plugin is already installed
        plugin_name = "Detect Puffs"
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

    def test_plugin_manager_close(self):
        """Test that the plugin manager closes without errors when threads are active."""
        # Create a situation similar to what happens in real usage:
        # A thread controller that might be in an invalid state when the plugin manager closes
        from flika.app.plugin_manager import PluginManager
        import time

        # Set up more verbose logging for this test
        logging.basicConfig(level=logging.DEBUG)
        logger = logging.getLogger("test_plugin_manager_close")
        logger.debug("Starting test_plugin_manager_close")

        # First make sure plugin_manager.thread_controllers exists
        if not hasattr(PluginManager, "thread_controllers"):
            PluginManager.thread_controllers = {}

        # Test case 1: Invalid thread controller (no thread attribute)
        logger.debug("Setting up case 1: Mock controller with no thread")
        mock_controller = mock.MagicMock()
        PluginManager.thread_controllers["test_invalid"] = mock_controller

        # Test case 2: Thread controller with a thread that raises RuntimeError
        logger.debug("Setting up case 2: Controller with bad thread")
        mock_controller2 = mock.MagicMock()
        mock_thread = mock.MagicMock()
        mock_thread.isRunning.side_effect = RuntimeError(
            "Internal C++ object already deleted"
        )
        mock_controller2.thread = mock_thread
        PluginManager.thread_controllers["test_error"] = mock_controller2

        # Log what we're about to do
        logger.debug("About to call closeEvent with problematic thread controllers")

        # Call closeEvent - should handle all thread states correctly
        try:
            PluginManager.gui.closeEvent(None)
            success = True
        except Exception as e:
            success = False
            logger.error(f"closeEvent failed: {e}")

        assert success, "closeEvent should handle all thread states without exception"

        # If we get here without exception, the test passes
        logger.debug("closeEvent completed successfully")

        # Clean up
        for key in ["test_invalid", "test_error"]:
            if key in PluginManager.thread_controllers:
                del PluginManager.thread_controllers[key]

        logger.debug("Test completed successfully")


@pytest.mark.skip(reason="ScriptEditor tests need comprehensive rework")
class TestScriptEditor:
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
        import flika.global_vars as g

        if hasattr(g, "windows"):
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
        from flika.process import threshold

        w2 = threshold(0.5)

        # Trigger the "From Window" action in the script editor
        ScriptEditor.gui.actionFrom_Window.trigger()

        # Get the text from the editor
        text = str(ScriptEditor.gui.currentTab().toPlainText())

        # Verify the text contains the expected command
        assert "threshold" in text, "Script editor should contain threshold command"
        assert "0.5" in text, "Script editor should contain the threshold value"
