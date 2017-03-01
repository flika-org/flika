from flika.app import *
from flika.app.plugin_manager import PluginManager, load_local_plugins
from flika.app.terminal_widget import ScriptEditor
from flika.plugins import plugin_list
from flika.window import Window
import numpy as np

fa = FlikaApplication()

class TestPluginManager():
	def setup_method(self):
		PluginManager.show()

	def teardown_method(self):
		PluginManager.close()

	def test_local_plugins(self):
		load_local_plugins()
		local = set(plugin_list.keys())
		plugins = set(PluginManager.plugins.keys())

		assert local & plugins == local, "Local plugin list not loaded correctly"

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
