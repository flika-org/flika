from flika.app import *
from flika.app.plugin_manager import PluginManager, load_local_plugins
from flika.app.terminal_widget import ScriptEditor
from flika.plugins import plugin_list
from flika.window import Window
import numpy as np

fa = FlikaApplication()

class TestPluginManager():
	@classmethod
	def setup_method(cls):
		PluginManager.show()
		load_local_plugins()

	@classmethod
	def teardown_method(cls):
		PluginManager.close()

	def test_local_plugins(self):
		
		local = set(plugin_list.keys())
		plugins = set(PluginManager.plugins.keys())

		assert (local & plugins) == plugins, "Local plugin list not loaded correctly"

	#def test_install_plugin(self):
	#	plugin_name = 'Detect Puffs'
	#	if PluginManager.plugins[plugin_name].installed:
	#		return
	#	PluginManager.downloadPlugin(plugin_name)
	#	assert PluginManager.plugins[plugin_name].menu is not None and PluginManager.plugins[plugin_name].installed, "Plugin install"
	#	PluginManager.removePlugin(plugin_name)
	#	assert PluginManager.plugins[plugin_name].menu is None and not PluginManager.plugins[plugin_name].installed, "Plugin uninstall"


class TestScriptEditor():
	def setup_method(self):
		ScriptEditor.show()

	def teardown_method(self):
		ScriptEditor.close()

	def test_from_window(self):
		w1 = Window(np.random.random([10, 20, 20]))
		from flika.process import threshold
		w2 = threshold(.5)
		ScriptEditor.gui.actionFrom_Window.trigger()
		text = str(ScriptEditor.gui.currentTab().toPlainText())
		assert text == "threshold(value=0.5, darkBackground=False, keepSourceWindow=False)", "From window command not expected"

fa.close()
