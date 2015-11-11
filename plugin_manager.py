from dependency_check import *
from glob import glob
import global_vars as g
from PyQt4.QtGui import *
from types import FunctionType, LambdaType
import sys

def import_plugin(folder):
	temp_ = __import__("plugins.%s" % folder, fromlist=['settings'])
	module = sys.modules[__name__]
	for dep in temp_.settings['dependencies']:
		val = __import__(dep, locals(), globals())
		setattr(module, dep, val)

def str2func(folder, function):
	names = function.split('.')
	return __import__('plugins.%s.%s' % (folder, '.'.join(names[:-1])), fromlist=[names[-1]]).__dict__[names[-1]]


def build_plugin_menus(parentMenu, name, value, folder):
	if isinstance(value, str):
		act = QAction(name, parentMenu, triggered=lambda : str2func(folder, value))
		act.hovered.connect(lambda : import_plugin(folder))
		parentMenu.addAction(act)
	elif isinstance(value, dict):
		menu = QMenu(name)
		for action, func in value.items():
			if isinstance(func, str):
				menu.addAction(QAction(action, menu, triggered=lambda : str2func(folder, value)))
			elif isinstance(func, dict):
				for k, v in func.items():
					build_plugin_menus(menu, k, v, folder)
		menu.triggered.connect(lambda f: import_plugin(folder, f))
		parentMenu.addMenu(menu)

def init_plugins():
	paths = glob(os.path.join(os.getcwd(), 'plugins\\*'))
	for p in paths:
		try:
			folder_name = os.path.basename(p)
			if folder_name.startswith('_') or not os.path.isdir(p):
				return
			temp_ = __import__("plugins.%s" % folder_name, fromlist=['settings'])
			for dep in temp_.settings['dependencies']:
				install(dep)
			for menu_name, value in temp_.settings['menu_layout'].items():
				build_plugin_menus(g.m.menuPlugins, menu_name, value, folder_name)
		except Exception as e:
			print('Could not import %s: %s' % (os.path.basename(p), e))
