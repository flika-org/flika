from __future__ import absolute_import, division, print_function

import traceback
from functools import wraps

__all__ = ['die_on_error', 'die_on_error_no_gui']


def die_on_error(msg):
    """Decorator that catches errors, displays a popup message, and quits"""
    from flika.utils.qmessagebox_widget import QMessageBoxPatched as QMessageBox

    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Make sure application has been started
                from glue.utils.qt import get_qapp  # Here to avoid circ import
                get_qapp()

                m = "%s\n%s" % (msg, e)
                detail = str(traceback.format_exc())
                if len(m) > 500:
                    detail = "Full message:\n\n%s\n\n%s" % (m, detail)
                    m = m[:500] + '...'

                qmb = QMessageBox(QMessageBox.Critical, "Error", m)
                qmb.setDetailedText(detail)
                qmb.show()
                qmb.raise_()
                qmb.exec_()
                sys.exit(1)
        return wrapper
    return decorator

def die_on_error_no_gui(msg):
    """
    Non-GUI version of the decorator in flika.utils.qt.decorators.

    In this case we just let the Python exception terminate the execution.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                print('=' * 72)
                print(msg + ' (traceback below)')
                print('-' * 72)
                traceback.print_exc()
                print('=' * 72)
        return wrapper
    return decorator

'''
def messagebox_on_error(msg):
    """Decorator that catches exceptions and displays an error message"""
    from flika.utils.qmessagebox_widget import QMessageBoxPatched as QMessageBox  # Must be here

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                m = "%s\n%s" % (msg, e.args[0])
                detail = str(traceback.format_exc())
                qmb = QMessageBox(QMessageBox.Critical, "Error", m)
                qmb.setDetailedText(detail)
                qmb.resize(400, qmb.size().height())
                qmb.exec_()
        return wrapper

    return decorator
'''