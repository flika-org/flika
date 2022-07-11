from qtpy import QtCore, QtGui, QtWidgets, PYQT5

__all__ = ['get_qapp']

qapp = None


def get_qapp(icon_path=None):
    """Get the QApplication instance currently in use. If no QApplication exists,
    one is created and the standard windoe icon is set to icon_path

    Args:
        icon_path (str): location of icon to use as default window icon

    Returns:
        QtGui.QApplication: the current application process 
    """
    global qapp
    qapp = QtWidgets.QApplication.instance()
    if qapp is None:
        qapp = QtWidgets.QApplication([''])
        qapp.setQuitOnLastWindowClosed(True)
        if icon_path is not None:
            qapp.setWindowIcon(QtGui.QIcon(icon_path))

    # Make sure we use high resolution icons with PyQt5 for HDPI
    # displays. TODO: check impact on non-HDPI displays.
    if PYQT5:
        qapp.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps)

    return qapp