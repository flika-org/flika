# -*- coding: utf-8 -*-
import sys
import os
import atexit
from contextlib import contextmanager
from typing import Any, Dict, Optional, Type, Union

# Import Qt functionality through qtpy for abstraction
from qtpy import QtCore, QtWidgets

# IPython imports
import IPython
from IPython.core.usage import default_banner
from IPython import get_ipython

# ZMQ imports
from zmq import ZMQError
# Remove deprecated zmq.eventloop.ioloop import
# from zmq.eventloop import ioloop
# Import tornado's ioloop directly instead (if needed)
import tornado.ioloop
# Use current import location for ZMQStream
from zmq.eventloop.zmqstream import ZMQStream

# Import version
from flika.version import __version__

# Import traitlets
from traitlets import TraitError

# Import ipykernel components
from ipykernel.connect import _find_connection_file as find_connection_file
from ipykernel.kernelbase import Kernel
from ipykernel.kernelapp import IPKernelApp
from ipykernel.iostream import OutStream
from ipykernel.inprocess.ipkernel import InProcessInteractiveShell
from ipykernel.connect import get_connection_file

# Import qtconsole components
from qtconsole.client import QtKernelClient
from qtconsole.manager import QtKernelManager
from qtconsole.inprocess import QtInProcessKernelManager
from qtconsole.rich_jupyter_widget import RichJupyterWidget as RichIPythonWidget


def in_process_console(console_class: Type[RichIPythonWidget] = RichIPythonWidget, **kwargs: Any) -> RichIPythonWidget:
    """Create a console widget, connected to an in-process Kernel

    Parameters:
        console_class: The class of the console widget to create
        kwargs: Extra variables to put into the namespace
    """
    km = QtInProcessKernelManager()
    km.start_kernel()

    kernel = km.kernel
    kernel.gui = 'qt'

    client = km.client()
    client.start_channels()

    control = console_class()
    control.kernel_manager = km
    control.kernel_client = client
    control.shell = kernel.shell
    control.shell.user_ns.update(**kwargs)
    return control


def connected_console(console_class: Type[RichIPythonWidget] = RichIPythonWidget, **kwargs: Any) -> RichIPythonWidget:
    """Create a console widget, connected to another kernel running in
       the current process

    Parameters:
        console_class: The class of the console widget to create
        kwargs: Extra variables to put into the namespace
    """
    shell = get_ipython()
    if shell is None:
        raise RuntimeError("There is no IPython kernel in this process")

    client = QtKernelClient(connection_file=get_connection_file())
    client.load_connection_file()
    client.start_channels()

    control = console_class()
    control.kernel_client = client
    control.shell = shell
    control.shell.user_ns.update(**kwargs)
    return control


class Terminal(RichIPythonWidget):
    """IPython terminal widget for embedding in the application."""
    
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.setAcceptDrops(True)
        self.shell = None

    @property
    def namespace(self) -> Optional[Dict[str, Any]]:
        """Return the namespace dictionary of the shell."""
        return self.shell.user_ns if self.shell is not None else None

    def update_namespace(self, kwargs: Dict[str, Any]) -> None:
        """Update the namespace with the given variables."""
        if self.shell is not None:
            self.shell.push(kwargs)


@contextmanager
def redirect_output(session: Any, pub_socket: Any) -> None:
    """Prevent any of the widgets from permanently hijacking stdout or stderr"""
    sys.stdout = OutStream(session, pub_socket, u'stdout')
    sys.stderr = OutStream(session, pub_socket, u'stderr')
    try:
        yield
    finally:
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__


def non_blocking_eventloop(kernel: Kernel) -> None:
    """Set up a non-blocking event loop for the kernel."""
    kernel.timer = QtCore.QTimer()
    kernel.timer.timeout.connect(kernel.do_one_iteration)
    kernel.timer.start(1000 * kernel._poll_interval)


class EmbeddedQtKernel(Kernel):
    """Kernel class that embeds the Qt event loop."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.eventloop = non_blocking_eventloop

    def do_one_iteration(self) -> None:
        with redirect_output(self.session, self.iopub_socket):
            super().do_one_iteration()

    def execute_request(self, stream: Any, ident: Any, parent: Any) -> None:
        with redirect_output(self.session, self.iopub_socket):
            super().execute_request(stream, ident, parent)


class EmbeddedQtKernelApp(IPKernelApp):
    """Application class for embedded Qt kernel."""

    def init_kernel(self) -> None:
        shell_stream = ZMQStream(self.shell_socket)
        kernel = EmbeddedQtKernel(
            config=self.config, 
            session=self.session,
            shell_streams=[shell_stream],
            iopub_socket=self.iopub_socket,
            stdin_socket=self.stdin_socket,
            log=self.log,
            profile_dir=self.profile_dir,
        )
        self.kernel = kernel
        kernel.record_ports(self.ports)

    def start(self) -> None:
        # Handoff between IOLoop and QApplication event loops
        loop = tornado.ioloop.IOLoop.instance()
        # Use 1ms callback time to prevent application hanging
        stopper = tornado.ioloop.PeriodicCallback(loop.stop, 1, loop)
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(loop.start)
        self.timer.start(100)
        stopper.start()
        super().start()


class EmbeddedIPythonWidget(Terminal):
    """Modern embedded IPython widget."""
    
    gui_completion = 'droplist'

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._init_kernel_app()
        self._init_kernel_manager()
        self.update_namespace(kwargs)

    def _init_kernel_app(self) -> None:
        app = EmbeddedQtKernelApp.instance()
        try:
            app.initialize([])
        except ZMQError:
            pass  # Already set up
        try:
            app.start()
        except RuntimeError:  # Already started
            pass
        self.app = app
        self.shell = app.shell

    def _init_kernel_manager(self) -> None:
        connection_file = find_connection_file(self.app.connection_file)
        manager = QtKernelManager(connection_file=connection_file)
        manager.load_connection_file()
        manager.start_channels()
        atexit.register(manager.cleanup_connection_file)
        self.kernel_manager = manager

    def update_namespace(self, ns: Dict[str, Any]) -> None:
        self.app.shell.user_ns.update(ns)


def ipython_terminal(banner: str = '', **kwargs: Any) -> Terminal:
    """Return a qt widget which embeds an IPython interpreter.

    Extra keywords will be added to the namespace of the shell.

    Parameters:
        banner: Text to display at the top of the terminal
        kwargs: Extra variables to be added to the namespace

    Returns:
        Terminal widget with embedded IPython interpreter
    """
    Terminal.banner = f"""flika version {__version__}

{banner}

"""

    # In modern Python with recent IPython, we only need the in-process console
    # (version checking logic simplified for Python 3.13)
    shell = get_ipython()
    if shell is None or isinstance(shell, InProcessInteractiveShell):
        return in_process_console(console_class=Terminal, **kwargs)
    return connected_console(console_class=Terminal, **kwargs)


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    new_widget = ipython_terminal()
    new_widget.show()
    app.exec()  # Using exec() in Python 3 (not exec_())