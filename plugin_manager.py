from dependency_check import *
from glob import glob
import global_vars as g
from PyQt4.QtGui import *
from types import FunctionType, LambdaType
import sys
	
def str2func(module_name, function):
	names = function.split('.')
	func_str = names[-1]
	module_location = '.'.join(names[:-1])
	plugins = "plugins.%s.%s" % (module_name, module_location)
	module = __import__('plugins.%s.%s' % (module_name, '.'.join(names[:-1])), fromlist=[func_str])
	return getattr(module, func_str)

def build_plugin_menus(parentMenu, name, value, module_name):
	if isinstance(value, str):
		act = QAction(name, parentMenu, triggered=lambda : str2func(module_name, value)())
		#act.hovered.connect(lambda : import_plugin(module_name))
		parentMenu.addAction(act)
	elif isinstance(value, dict):
		menu = QMenu(name)
		for action, func in value.items():
			if isinstance(func, str):
				menu.addAction(QAction(action, menu, triggered=lambda : str2func(module_name, value)()))
			elif isinstance(func, dict):
				for k, v in func.items():
					build_plugin_menus(menu, k, v, module_name)
		menu.triggered.connect(lambda f: import_plugin(module_name, f))
		parentMenu.addMenu(menu)

def init_plugins():
	paths = glob(os.path.join(os.getcwd(), 'plugins', '*'))
	for p in paths:
		try:
			config_file=os.path.join(p,'config.py')
			module_name=os.path.basename(p)
			if module_name.startswith('_') or not os.path.isfile(config_file):
				continue #there must be a config.py file or the module won't load, ignore __pycache__
			config = __import__("plugins.%s" % module_name, fromlist=['config']).config
			print(config)
			for dep in config.dependencies:
				install(dep)
			for menu_name, value in config.menu_layout.items():
				build_plugin_menus(g.m.menuPlugins, menu_name, value, module_name)
		except Exception as e:
			print('Could not import %s: %s' % (os.path.basename(p), e))
