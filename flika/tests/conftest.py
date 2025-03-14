import pytest
from ..app.application import FlikaApplication
from qtpy import QtWidgets, QtCore
import gc

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
    
    # Clean up all QThreads by using low-level Qt functions
    from ..app.plugin_manager import PluginManager, Load_Local_Plugins_Thread
    
    # Process remaining events first to allow threads to finish naturally
    QtWidgets.QApplication.processEvents()
    
    # Find all QThread instances in the application
    all_threads = []
    # First add the known thread instances
    if hasattr(flikaApp, 'load_local_plugins_thread'):
        all_threads.append(flikaApp.load_local_plugins_thread)
    
    # Then find all QThread instances in the gc
    for obj in gc.get_objects():
        if isinstance(obj, QtCore.QThread) and obj not in all_threads:
            all_threads.append(obj)
    
    # Terminate all threads
    for thread in all_threads:
        try:
            if thread.isRunning():
                print(f"Terminating thread: {thread}")
                thread.requestInterruption()
                thread.quit()
                thread.wait(1000)  # Wait up to 1 second
                if thread.isRunning():
                    thread.terminate()
                    thread.wait(500)  # Wait another 500ms after termination
        except Exception as e:
            print(f"Error terminating thread: {e}")
    
    # Handle Python threads too
    if hasattr(PluginManager, 'loadThread') and PluginManager.loadThread is not None:
        try:
            if PluginManager.loadThread.is_alive():
                PluginManager.loadThread.join(timeout=1)
        except Exception as e:
            print(f"Error cleaning up PluginManager.loadThread: {e}")
    
    # Process events after thread termination
    QtWidgets.QApplication.processEvents()
    
    # Close all windows
    for widget in QtWidgets.QApplication.topLevelWidgets():
        try:
            widget.close()
        except Exception:
            pass
    
    # Process any remaining events
    QtWidgets.QApplication.processEvents()
    
    # Call quit on the application to ensure proper shutdown
    app.quit()
    
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