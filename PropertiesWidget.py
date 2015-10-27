"""
@author: Brett Settle
@Department: UCI Neurobiology and Behavioral Science
@Lab: Parker Lab
@Date: August 6, 2015
"""
from pyqtgraph.Qt import QtGui, QtCore
import numpy as np
import pyqtgraph as pg
import pyqtgraph.parametertree.parameterTypes as pTypes
from pyqtgraph.parametertree import Parameter, ParameterTree, ParameterItem, registerParameterType
from types import FunctionType

import sys
if sys.version.startswith('3'):
	QtCore.Signal = QtCore.pyqtSignal

class MultiSpinBox(QtGui.QWidget):
	valueChanged = QtCore.Signal(object)
	def __init__(self, values):
		super(MultiSpinBox, self).__init__()
		self.layout = QtGui.QGridLayout(self)
		self.spins = []
		for i,v in enumerate(values):
			to_add = pg.SpinBox(value=v)
			to_add.valueChanged.connect(lambda : self.valueChanged.emit(self.value()))
			self.spins.append(to_add)
			self.layout.addWidget(to_add, 0, i)
		self.setLayout(self.layout)

	def value(self):
		return [spin.value() for spin in self.spins]

	def setValue(self, val):
		for i in range(len(self.spins)):
			self.spins[i].setValue(val[i])


class ScalableGroup(pTypes.GroupParameter):
	'''Group used for entering and adding parameters to ParameterWidget'''
	def __init__(self, **opts):
		opts['type'] = 'group'
		opts['addText'] = "Add"
		opts['addList'] = ['str', 'float', 'int', 'color']
		pTypes.GroupParameter.__init__(self, **opts)

	def addNew(self, typ):
		val = {
			'str': '',
			'float': 0.0,
			'int': 0,
			'color': (255, 255, 255)
		}[typ]
		self.addChild(dict(name="New Parameter %d" % (len(self.childs)+1), type=typ, value=val, removable=True, renamable=True))

	def getItems(self):
		items = {}
		for k, v in self.names.items():
			if isinstance(v, ScalableGroup):
				items[k] = v.getItems()
			else:
				items[k] = v.value()
		return items

class ParameterWidget(QtGui.QWidget):
	'''Settings Widget takes a list of dictionaries and provides a widget to edit the values (and key names)

		Each dict object must include these keys:
			name: The string used to get/set the value, shown to left of value
			value: The value to show next to name, matches 'type' if given else use type of this value
				accepts QColor, lambda, list, generic types

		Optional keys are:
			type: Specify the type if it is not obvious by the value provided, as a string
			suffix: (for float/int values only) added for user readability
			children: a list of dicts under a 'group' parameter
			removable: bool specifying if this can be removed (set to False)
			renamable: bool specifying if this can be renamed (set to False)
			appendable: bool specifying if user can add to this group

		To pass in a parent parameter with children, pass 'group' to the 'value' key and the list of dicts to a new 'children' parameter

	'''
	valueChanged = QtCore.Signal(str, object)
	def __init__(self, title, paramlist, about="", appendable=False):
		super(ParameterWidget, self).__init__()
		self.ParamGroup = ScalableGroup if appendable else pTypes.GroupParameter

		self.parameters = self.ParamGroup(name="Parameters", children=ParameterWidget.build_parameter_list(paramlist))
		self.parameters.sigTreeStateChanged.connect(self.paramsChanged)
		self.info = about
		self.tree = ParameterTree()
		self.tree.setParameters(self.parameters, showTop=False)
		self.tree.setWindowTitle(title)
		self.makeLayout()
		self.resize(800,600)

	@staticmethod
	def type_as_str(var):
		if type(var) == tuple and len(var) != 3:
			var = list(var)
		elif isinstance(var, np.string_):
			return 'str'
		elif isinstance(var, np.generic):
			var = float(var)
		elif isinstance(var, QtGui.QColor) or (type(var) == tuple and len(var) == 3):
			return 'color'
		elif isinstance(var, dict) or (isinstance(var, list) and all([type(i) == dict for i in var])):
			return 'group'
		elif isinstance(var, (int, float, bool, list, str)):
			return type(var).__name__
		elif isinstance(var, FunctionType):
			return 'action'
		return 'text'

	def paramsChanged(self, params, change):
		obj, change, val = change[0]
		if change == 'value':
			self.valueChanged.emit(obj.opts['name'], val)
		else:
			pass

	def makeLayout(self):
		layout = QtGui.QGridLayout()
		self.setLayout(layout)

		if len(self.info) > 0:
			self.scrollArea = QtGui.QScrollArea(self)
			self.scrollArea.setWidgetResizable(True)
			self.scrollArea.setWidget(QtGui.QLabel(self.info))
			layout.addWidget(self.scrollArea, 0,  0, 1, 2)

		layout.addWidget(self.tree, 1, 0, 1, 2)
		layout.setRowStretch(1, 4)

	@staticmethod
	def from_dict(title, d, about="", **kargs):
		params = []
		for key, value in d.items():
			params.append({"name": key, "value": value, "type": ParameterWidget.type_as_str(value)})
		return ParameterWidget(title, d, about, **kargs)

	@staticmethod
	def get_group_dict(groupParam):
		d = {}
		for c in groupParam.childs:
			if isinstance(c, pTypes.GroupParameter):
				d[c.opts['name']] = ParameterWidget.get_group_dict(c)
			else:
				d[c.opts['name']] = c.opts['value']
		return d

	@staticmethod
	def build_parameter_list(params):
		'''
		condenses dict object into usable Parameter object recursively
		'''
		return_params = []
		for param_dict in params:

			assert 'name' in param_dict, 'Must provide a name for each item'
			if 'children' in param_dict:
				return_params.append(pTypes.GroupParameter(name=param_dict['name'], children=ParameterWidget.build_parameter_list(param_dict['children'])))
				continue

			assert 'value' in param_dict, 'Must provide a value for each non-group item; %s does not have a value' % param_dict['name']
			if param_dict['value'] == None:
				continue
			if 'type' not in param_dict:
				param_dict['type'] = ParameterWidget.type_as_str(param_dict['value'])

			if param_dict['type'] == 'list':
				param_dict['values'] = param_dict.pop('value')

			return_params.append(param_dict)
		return return_params

class ParameterEditor(QtGui.QWidget):
	done = QtCore.pyqtSignal(dict)
	cancelled = QtCore.pyqtSignal()
	def __init__(self, title, params, about="", **kargs):
		super(ParameterEditor, self).__init__()
		layout = QtGui.QVBoxLayout()
		self.setLayout(layout)
		self.param_widget = ParameterWidget(title, params, about, **kargs)
		buttonPanel = QtGui.QWidget()
		buttonLayout = QtGui.QHBoxLayout()
		cancelButton = QtGui.QPushButton("Cancel")
		doneButton = QtGui.QPushButton("Done")

		cancelButton.pressed.connect(lambda : self.close(cancelled = True))
		doneButton.pressed.connect(self.close)

		buttonLayout.addStretch(1)
		buttonLayout.addWidget(cancelButton)
		buttonLayout.addWidget(doneButton)
		buttonPanel.setLayout(buttonLayout)
		layout.addWidget(self.param_widget)
		layout.addWidget(buttonPanel)
		self.resize(800,600)

	def close(self, cancelled=False):
		super(ParameterEditor, self).close()
		if not cancelled:
			self.done.emit(ParameterWidget.get_group_dict(self.param_widget.parameters))
		else:
			self.cancelled.emit()



if __name__ == "__main__":
	app = QApplication([])
	pw = ParameterEditor("Options", [{"name": "Key", "value": "Name"}, {"name": "Age", "value": 18, "type": "int", "min": 0}, {"name": "Gender", "value": ["Male", "Female"]},\
									{"name": "Color", "value": (0, 1, 2), "type": "color"}, {"name": "Subcategory", "children": [{"name": "Sub 1", "value": 0.0}, {"name": "Sub 2", "value": "Val"}]}])
	pw.show()
	app.exec_()