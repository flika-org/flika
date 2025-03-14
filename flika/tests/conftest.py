import pytest
from ..app.application import FlikaApplication
from qtpy import QtWidgets, QtCore
import gc
import time
import sys

flikaApp = FlikaApplication()

@pytest.fixture(scope='session', autouse=True)
def fa() -> FlikaApplication:
    return flikaApp

@pytest.fixture(scope="session", autouse=True)
def clean_qt_app_shutdown():
    """Ensure clean Qt application shutdown after all tests"""
    yield
    # After all tests, properly clean up Qt resources
    
    # First, make sure application instance is available
    app = QtWidgets.QApplication.instance()
    if app is None:
        return  # No QApplication, nothing to clean up
    
    from ..app.plugin_manager import PluginManager
    from ..app.script_editor import ScriptEditor
    from ..window import Window
    from .. import global_vars as g
    from ..utils.thread_manager import cleanup_threads
    
    # Process events to finish pending operations
    QtWidgets.QApplication.processEvents()
    
    # Clean up all threads first
    cleanup_threads()
    
    # Close ScriptEditor first if it exists
    if hasattr(ScriptEditor, 'gui'):
        try:
            ScriptEditor.close()
            QtWidgets.QApplication.processEvents()
        except Exception as e:
            print(f"Error closing ScriptEditor: {e}")
    
    # Close PluginManager if it exists
    try:
        PluginManager.close()
        QtWidgets.QApplication.processEvents()
    except Exception as e:
        print(f"Error closing PluginManager: {e}")
    
    # Close all windows safely
    if hasattr(g, 'windows'):
        while g.windows:
            try:
                g.windows[0].close()
                QtWidgets.QApplication.processEvents()
            except Exception as e:
                print(f"Error closing window: {e}")
                g.windows.pop(0)
    
    # Close any remaining top-level widgets
    for widget in QtWidgets.QApplication.topLevelWidgets():
        try:
            widget.close()
            QtWidgets.QApplication.processEvents()
        except Exception as e:
            print(f"Error closing widget: {e}")
    
    # Process any remaining events
    QtWidgets.QApplication.processEvents()
    
    # Small delay to let everything finish
    time.sleep(0.1)
    QtWidgets.QApplication.processEvents()
    
    # Call quit on the application to ensure proper shutdown
    app.quit()
    
    # Process events once more
    QtWidgets.QApplication.processEvents()
    
    # Final garbage collection
    gc.collect()

@pytest.fixture(scope="session")
def qapp():
    """Create and return a QApplication instance"""
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    yield app
    app.quit()

@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Clean up after each test"""
    yield
    from ..app.script_editor import ScriptEditor
    from ..window import Window
    from .. import global_vars as g
    from ..utils.thread_manager import cleanup_threads
    
    # Process events to finish pending operations
    QtWidgets.QApplication.processEvents()
    
    # Clean up threads
    cleanup_threads()
    
    # Close ScriptEditor if it exists
    if hasattr(ScriptEditor, 'gui'):
        try:
            ScriptEditor.close()
            QtWidgets.QApplication.processEvents()
        except Exception as e:
            print(f"Error closing ScriptEditor: {e}")
    
    # More carefully close any open windows and explicitly delete ROIs
    if hasattr(g, 'windows'):
        for window in list(g.windows):
            try:
                # First remove all ROIs from the window
                if hasattr(window, 'rois'):
                    # Make a copy of the list since we'll be modifying it
                    rois = list(window.rois)
                    for roi in rois:
                        try:
                            # Explicitly disconnect signals
                            if hasattr(roi, 'resetSignals'):
                                roi.resetSignals()
                            # Delete the ROI
                            if hasattr(roi, 'delete'):
                                roi.delete()
                            # Process events after each ROI deletion
                            QtWidgets.QApplication.processEvents()
                        except Exception as e:
                            print(f"Error deleting ROI: {e}")
                
                # Now close the window
                window.close()
                QtWidgets.QApplication.processEvents()
            except Exception as e:
                print(f"Error closing window: {e}")
                g.windows.remove(window)
    
    # Process events again and do partial garbage collection before full gc
    QtWidgets.QApplication.processEvents()
    
    # Run garbage collection without attempting to clear everything
    import gc
    gc.collect(0)  # Only collect the youngest generation
    QtWidgets.QApplication.processEvents()
    
    # Now do a full collection
    gc.collect()