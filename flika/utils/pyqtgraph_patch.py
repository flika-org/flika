"""
PyQtGraph patches to improve stability during object cleanup.

This module contains monkey patches for PyQtGraph classes to prevent errors
when Qt objects are deleted but Python still tries to access them.
"""

import pyqtgraph as pg
from qtpy import QtWidgets

# Track which components have been patched
_patched_components = {
    "ViewBox": False,
    "ViewBoxMenu": False,
    "LinearRegionItem": False,
    "QWidget": False,
}


def safe_disconnect(signal):
    """Safely disconnect a Qt signal, ignoring errors if it's not connected

    Args:
        signal: The Qt signal to disconnect

    Returns:
        bool: True if disconnect succeeded or if there was a handled error
    """
    try:
        if signal is not None:
            signal.disconnect()
        return True
    except (TypeError, RuntimeError):
        return False


try:
    # Import necessary PyQtGraph components
    from pyqtgraph.graphicsItems.ViewBox.ViewBoxMenu import ViewBoxMenu

    def apply_pyqtgraph_patches():
        """Apply all PyQtGraph patches to improve stability during cleanup"""
        # Only apply patches if they haven't been applied already
        if not getattr(pg.ViewBox, "_cleanup_patched", False):
            # Add a method to check if a QWidget is still valid
            if not hasattr(QtWidgets.QWidget, "isValid"):

                def isValid(self):
                    try:
                        self.isVisible()
                        return True
                    except RuntimeError:
                        return False

                QtWidgets.QWidget.isValid = isValid
                _patched_components["QWidget"] = True

            # Patch ViewBox.forgetView
            original_forgetView = pg.ViewBox.forgetView

            def safe_forgetView(sid, name):
                try:
                    return original_forgetView(sid, name)
                except RuntimeError:
                    return None

            pg.ViewBox.forgetView = safe_forgetView

            # Patch ViewBox.updateAllViewLists
            original_updateAllViewLists = pg.ViewBox.updateAllViewLists

            def safe_updateAllViewLists():
                try:
                    return original_updateAllViewLists()
                except RuntimeError:
                    return None

            pg.ViewBox.updateAllViewLists = safe_updateAllViewLists

            # Patch ViewBox.updateViewLists
            original_updateViewLists = pg.ViewBox.updateViewLists

            def safe_updateViewLists(self):
                try:
                    # Skip if menu is gone or any control is invalid
                    if not hasattr(self, "menu") or self.menu is None:
                        return None
                    if hasattr(self.menu, "ctrl"):
                        for ctrl in self.menu.ctrl.values():
                            if not ctrl.isValid():
                                return None
                    return original_updateViewLists(self)
                except (RuntimeError, AttributeError):
                    return None

            pg.ViewBox.updateViewLists = safe_updateViewLists
            _patched_components["ViewBox"] = True

            # Patch ViewBoxMenu.setViewList
            original_setViewList = ViewBoxMenu.setViewList

            def safe_setViewList(self, views):
                try:
                    if hasattr(self, "ctrl") and "view" in self.ctrl:
                        c = self.ctrl["view"]
                        if not hasattr(c, "isValid") or c.isValid():
                            return original_setViewList(self, views)
                        return
                    return original_setViewList(self, views)
                except (RuntimeError, AttributeError):
                    return

            ViewBoxMenu.setViewList = safe_setViewList
            _patched_components["ViewBoxMenu"] = True

            # Patch LinearRegionItem.paint
            original_lri_paint = pg.LinearRegionItem.paint

            def safe_lri_paint(self, p, *args, **kwargs):
                try:
                    return original_lri_paint(self, p, *args, **kwargs)
                except RuntimeError:
                    return

            pg.LinearRegionItem.paint = safe_lri_paint
            _patched_components["LinearRegionItem"] = True

            # Mark as patched
            pg.ViewBox._cleanup_patched = True

        return True

except Exception:
    # If patching fails, provide a function that logs the error
    def apply_pyqtgraph_patches():
        """Fallback function when patching fails"""
        import warnings

        warnings.warn("Failed to apply PyQtGraph patches")
        return False
