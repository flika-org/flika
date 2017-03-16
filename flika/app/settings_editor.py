# -*- coding: utf-8 -*-
"""
Flika
@author: Kyle Ellefsen
@author: Brett Settle
@license: MIT
"""
import numpy as np
import pyqtgraph as pg
from pyqtgraph import ComboBox
from qtpy import QtWidgets
from multiprocessing import cpu_count
from ..utils.misc import setConsoleVisible
from ..process.BaseProcess import BaseDialog, BaseProcess, ColorSelector
from .. import global_vars as g


__all__ = ['SettingsEditor', 'rectSettings', 'pointSettings']

data_types = ['uint8', 'uint16', 'uint32', 'uint64', 'int8', 'int16', 'int32', 'int64', 'float16', 'float32', 'float64']

class SettingsEditor(BaseDialog):
    gui = None
    def __init__(self):
        old_dtype=g.settings['internal_data_type']
        dataDrop = ComboBox(items=data_types, default=old_dtype)
        showCheck = QtWidgets.QCheckBox()
        showCheck.setChecked(g.settings['show_windows'])
        multipleTracesCheck = QtWidgets.QCheckBox()
        multipleTracesCheck.setChecked(g.settings['multipleTraceWindows'])
        multiprocessing = QtWidgets.QCheckBox()
        multiprocessing.setChecked(g.settings['multiprocessing'])
        nCores = QtWidgets.QComboBox()
        debug_check = QtWidgets.QCheckBox(checked=g.settings['debug_mode'])
        debug_check.toggled.connect(setConsoleVisible)
        for i in np.arange(cpu_count())+1:
            nCores.addItem(str(i))
        nCores.setCurrentIndex(g.settings['nCores']-1)
        random_color_check = QtWidgets.QCheckBox()
        random_color_check.setChecked(g.settings['roi_color'] == 'random')
        roi_color = ColorSelector()
        roi_color.setEnabled(g.settings['roi_color'] != 'random')
        roi_color.color=g.settings['roi_color'] if g.settings['roi_color'] != 'random' else '#ffff00'

        default_rect = QtWidgets.QCheckBox()
        default_rect.setChecked(g.settings['default_rect_on_click'])
        
        items = []
        items.append({'name': 'random_color_check', 'string': 'Randomly color ROIs', 'object': random_color_check})
        items.append({'name': 'roi_color', 'string': 'Default ROI Color', 'object': roi_color})
        items.append({'name': 'internal_data_type', 'string': 'Internal Data Type', 'object': dataDrop})
        items.append({'name': 'show_windows', 'string': 'Show Windows', 'object': showCheck})
        items.append({'name': 'multipleTraceWindows', 'string': 'Multiple Trace Windows', 'object': multipleTracesCheck})
        items.append({'name': 'multiprocessing', 'string': 'Multiprocessing On', 'object': multiprocessing})
        items.append({'name': 'nCores', 'string': 'Number of cores to use when multiprocessing', 'object': nCores})
        items.append({'name': 'debug_mode', 'string': 'Debug Mode', 'object': debug_check})
        items.append({'name': 'default_rect_on_click', 'string': 'Enable default ROI on right click', 'object': default_rect})
        
        def update():
            g.settings['internal_data_type'] = str(dataDrop.currentText())
            g.settings['show_windows'] = showCheck.isChecked()
            g.settings['multipleTraceWindows'] = multipleTracesCheck.isChecked()
            g.settings['multiprocessing']=multiprocessing.isChecked()
            g.settings['nCores']=int(nCores.itemText(nCores.currentIndex()))
            g.settings['debug_mode'] = debug_check.isChecked()
            if not random_color_check.isChecked() and roi_color.color == 'random':
                roi_color.color = "#ffff00"
            g.settings['roi_color'] = roi_color.value() if not random_color_check.isChecked() else "random"
            roi_color.setEnabled(g.settings['roi_color'] != 'random')
            

        super(SettingsEditor, self).__init__(items, 'FLIKA Settings', '')
        self.accepted.connect(update)
        self.changeSignal.connect(update)
        g.dialogs.append(self)

    @staticmethod
    def show():
        if SettingsEditor.gui == None:
            SettingsEditor.gui = SettingsEditor()
        BaseDialog.show(SettingsEditor.gui)


def pointSettings(pointButton):
    """
    default points color
    default points size
    currentWindow points color
    currentWindow points size
    clear current points

    """
    point_color = ColorSelector()
    point_color.color=g.settings['point_color']
    point_color.label.setText(point_color.color)
    point_size = QtWidgets.QSpinBox()
    point_size.setRange(1,50)
    point_size.setValue(g.settings['point_size'])
    show_all_points = QtWidgets.QCheckBox()
    show_all_points.setChecked(g.settings['show_all_points'])
    
    update_current_points_check = QtWidgets.QCheckBox()
    update_current_points_check.setChecked(False)
    
    items = []
    items.append({'name': 'point_color', 'string': 'Default Point Color', 'object': point_color})
    items.append({'name': 'point_size', 'string': 'Default Point Size', 'object': point_size})
    items.append({'name': 'show_all_points', 'string': 'Show points from all frames', 'object': show_all_points})
    items.append({'name': 'update_current_points_check', 'string': 'Update already plotted points', 'object': update_current_points_check})
    def update():
        win = g.currentWindow
        g.settings['point_color'] = point_color.value()
        g.settings['point_size'] = point_size.value()
        g.settings['show_all_points'] = show_all_points.isChecked()
        if win is not None and update_current_points_check.isChecked() == True:
            color = QtWidgets.QColor(point_color.value())
            size = point_size.value()
            for t in np.arange(win.mt):
                for i in np.arange(len(win.scatterPoints[t])):
                    win.scatterPoints[t][i][2] = color
                    win.scatterPoints[t][i][3] = size
            win.updateindex()
        if win is not None:
            if g.settings['show_all_points']:
                pts = []
                for t in np.arange(win.mt):
                    pts.extend(win.scatterPoints[t])
                pointSizes = [pt[3] for pt in pts]
                brushes = [pg.mkBrush(*pt[2].getRgb()) for pt in pts]
                win.scatterPlot.setPoints(pos=pts, size=pointSizes, brush=brushes)
            else:
                win.updateindex()
    dialog = BaseDialog(items, 'Points Settings', '')
    g.dialogs.append(dialog) 
    dialog.accepted.connect(update)
    dialog.changeSignal.connect(update)
    dialog.show()

def rectSettings(rectButton):
    """
    default rect height
    default rect width
    """
    rect_width = QtWidgets.QSpinBox()
    rect_width.setRange(1,50)
    rect_width.setValue(g.settings['rect_width'])
    rect_height = QtWidgets.QSpinBox()
    rect_height.setRange(1,50)
    rect_height.setValue(g.settings['rect_height'])

    items = []
    items.append({'name': 'rect_width', 'string': 'Default Rectangle Width', 'object': rect_width})
    items.append({'name': 'rect_height', 'string': 'Default Rectangle Height', 'object': rect_height})
    
    def update():
        win = g.currentWindow
        g.settings['rect_width'] = rect_width.value()
        g.settings['rect_height'] = rect_height.value()
        
    dialog = BaseDialog(items, 'Rectangle Settings', '')
    dialog.accepted.connect(update)
    dialog.changeSignal.connect(update)
    g.dialogs.append(dialog)
    dialog.show()