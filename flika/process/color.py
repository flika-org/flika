import numpy as np
from window import Window
import global_vars as g
from process.BaseProcess import BaseProcess, WindowSelector, MissingWindowError, CheckBox
from qtpy import QtWidgets, QtCore, QtGui

__all__ = ['split_channels']


class Split_channels(BaseProcess):
    """ split_channels(keepSourceWindow=False)
    This splits the color channels in a Window

    Returns:
        list of new Windows
    """

    def __init__(self):
        super().__init__()

    def gui(self):
        self.gui_reset()
        super().gui()

    def __call__(self, keepSourceWindow=False):
        self.start(keepSourceWindow)
        newWindows = []
        if not self.oldwindow.metadata['is_rgb']:
            g.alert('Cannot split channels, no colors detected.')
            return None
        nChannels = self.tif.shape[-1]
        for i in range(nChannels):
            newtif = self.tif[..., i]
            name = self.oldname + ' - Channel ' + str(i)
            newWindow = Window(newtif, name, self.oldwindow.filename)
            newWindows.append(newWindow)
        if keepSourceWindow is False:
            self.oldwindow.close()
        g.m.statusBar().showMessage('Finished with {}.'.format(self.__name__))
        return newWindows


split_channels = Split_channels()