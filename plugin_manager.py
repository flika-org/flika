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
		act = QAction(name, parentMenu, triggered=str2func(module_name, value))
		parentMenu.addAction(act)
	elif isinstance(value, dict):
		#menu = QMenu(name)
		menu = parentMenu.addMenu(name)
		for k, v in value.items():
			build_plugin_menus(menu, k, v, module_name)

def init_plugins():
	paths = glob(os.path.join(os.getcwd(), 'plugins', '*'))
	for p in paths:
		try:
			init_file=os.path.join(p,'__init__.py')
			module_name=os.path.basename(p)
			if module_name.startswith('_') or not os.path.isfile(init_file):
				continue #there must be a __init__.py file or the module won't load, ignore __pycache__
			module = __import__("plugins.%s" % module_name, fromlist=['dependencies', 'menu_layout'])
			if not hasattr(module, 'dependencies') or not hasattr(module, 'menu_layout'):
				print('Module %s must have a list of dependencies and menu layout dictionary' % module_name)
				continue
			for dep in module.dependencies:
				install(dep)
			for menu_name, value in module.menu_layout.items():
				build_plugin_menus(g.m.menuPlugins, menu_name, value, module_name)
		except Exception as e:
			print('Could not import %s: %s' % (os.path.basename(p), e))
