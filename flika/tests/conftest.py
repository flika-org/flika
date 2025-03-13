import pytest
from ..app.application import FlikaApplication
from qtpy import QtWidgets
import gc

flikaApp = FlikaApplication()

@pytest.fixture(scope='session', autouse=True)
def fa():
	return flikaApp

@pytest.fixture(scope="session", autouse=True)
def clean_qt_app_shutdown():
    """Ensure clean Qt application shutdown after all tests"""
    yield
    # After all tests, properly clean up Qt resources
    
    # Process any pending events before cleanup
    QtWidgets.QApplication.processEvents()
    
    # Safely close widgets that still exist
    for widget in QtWidgets.QApplication.topLevelWidgets():
        try:
            if widget.isVisible():
                widget.close()
        except (RuntimeError, AttributeError):
            # Skip widgets that are already deleted
            pass
    
    # Process events again to handle close signals
    QtWidgets.QApplication.processEvents()
    
    # Force garbage collection to clean up any remaining references
    gc.collect()

@pytest.fixture(scope="session")
def qapp():
    """Create and return a QApplication instance"""
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    yield app
    app.quit()