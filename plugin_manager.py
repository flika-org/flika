from dependency_check import *
from glob import glob
import global_vars as g
from PyQt4.QtGui import *
	
def str2func(plugin_name, object_location, function):
    '''
    takes plugin_name, path to object, function as arguments
    imports plugin_name.path and gets the function from that imported object
    to be run when an action is clicked
    '''
    plugins = "plugins.%s" % (plugin_name)
    module = __import__(plugins, fromlist=[object_location]).__dict__[object_location]
    while '.' in function:
        dot = function.find('.')
        func, function = function[:dot], function[dot + 1:]
        module = getattr(module, func)
    try:
        return getattr(module, function)
    except:
        raise Exception("Failed to import %s from module %s. Check name and try again." % (function, module)) # only alerts on python 3?

def get_lambda(mod_name, path, func):
    return lambda : str2func(mod_name, path, func)()

def build_plugin_menus(parentMenu, name, value, module_name):
    if isinstance(value, list):
        act = QAction(name, parentMenu, triggered=get_lambda(module_name, *value))
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
