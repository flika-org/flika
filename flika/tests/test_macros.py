from ..app.plugin_manager import PluginManager, load_local_plugins, plugin_list
from ..app.script_editor import ScriptEditor
from ..window import Window
import numpy as np

class TestPluginManager():
	def setup_method(self, method):
		PluginManager.show()
		load_local_plugins()
		
	def teardown_method(self, method):
		PluginManager.close()

	def test_local_plugins(self):
		local = set(plugin_list.keys())
		plugins = set(PluginManager.plugins.keys())

		assert (local & plugins) == local, "Local plugin list not loaded correctly"

	def test_install_plugin(self):
		load_local_plugins()
		plugin_name = 'Detect Puffs'
		if PluginManager.plugins[plugin_name].installed:
			return
		PluginManager.refresh_online_plugins()
		i = 0
		while PluginManager.plugins[plugin_name].url == None:
			i += 1
			if i == 1000:
				return
			continue
		PluginManager.downloadPlugin(plugin_name)
		assert PluginManager.plugins[plugin_name].menu is not None and PluginManager.plugins[plugin_name].installed, "Plugin install"
		PluginManager.removePlugin(plugin_name)
		assert PluginManager.plugins[plugin_name].menu is None and not PluginManager.plugins[plugin_name].installed, "Plugin uninstall"


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