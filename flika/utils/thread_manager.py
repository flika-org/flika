#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Thread Management Module for Flika
----------------------------------

This module provides consistent thread management patterns for the Flika application.
It includes:

1. Properly structured QThread implementations
2. Worker pattern for background tasks
3. Thread Pool for managing multiple worker threads
4. Utilities for safe thread termination
"""

import logging
import threading
import time
from typing import Callable, Dict, List, Optional, Any, Union
from qtpy import QtCore

logger = logging.getLogger(__name__)


class StoppableThread(threading.Thread):
    """
    A thread class that supports stopping via a flag.
    This is a better approach than using Thread.join() with timeouts.
    """

    def __init__(self, *args, name=None, daemon=True, **kwargs):
        """
        Initialize the thread with daemon=True by default to allow proper application exit.

        Args:
            name: Optional name for the thread
            daemon: Whether the thread is a daemon thread (defaults to True)
            *args, **kwargs: Arguments passed to threading.Thread
        """
        super().__init__(*args, name=name, daemon=daemon, **kwargs)
        self._stop_event = threading.Event()

    def stop(self) -> None:
        """Signal the thread to stop"""
        self._stop_event.set()

    def stopped(self) -> bool:
        """Check if the thread should stop"""
        return self._stop_event.is_set()

    def join(self, timeout=None) -> None:
        """
        Join the thread with proper cleanup.

        Args:
            timeout: Maximum time to wait for thread to complete
        """
        self.stop()
        super().join(timeout)


class Worker(QtCore.QObject):
    """
    Worker object that performs work in a separate thread.
    Using the worker pattern is the recommended way to use QThread.
    """

    # Define signals
    started = QtCore.Signal()
    finished = QtCore.Signal()
    error = QtCore.Signal(str)
    result = QtCore.Signal(object)
    progress = QtCore.Signal(int)
    status = QtCore.Signal(str)

    def __init__(self, task_func: Callable, *args, **kwargs):
        """
        Initialize the worker with the task function and arguments.

        Args:
            task_func: The function to run in the thread
            *args, **kwargs: Arguments to pass to the task function
        """
        super().__init__()
        self.task_func = task_func
        self.args = args
        self.kwargs = kwargs
        self._is_running = False
        self._abort = False

    @QtCore.Slot()
    def run(self):
        """Execute the task function in the thread"""
        self._is_running = True
        self._abort = False
        self.started.emit()

        try:
            # Check if the task function accepts a worker argument to report progress
            if "worker" in self.task_func.__code__.co_varnames:
                result = self.task_func(*self.args, worker=self, **self.kwargs)
            else:
                result = self.task_func(*self.args, **self.kwargs)

            # Only emit result if we haven't aborted
            if not self._abort:
                self.result.emit(result)

        except Exception as e:
            logger.exception(f"Error in worker thread: {str(e)}")
            self.error.emit(str(e))
        finally:
            self._is_running = False
            self.finished.emit()

    def abort(self):
        """Signal the worker to abort its task"""
        self._abort = True

    def is_running(self) -> bool:
        """Check if the worker is currently running"""
        return self._is_running

    def should_abort(self) -> bool:
        """Check if the worker should abort its task"""
        return self._abort


class ThreadController:
    """
    Controller for managing a QThread with a Worker.
    This follows the recommended Qt pattern of moving a worker to a thread.
    """

    def __init__(self, task_func: Callable, *args, **kwargs):
        """
        Initialize the thread controller with a task function.

        Args:
            task_func: The function to run in the thread
            *args, **kwargs: Arguments to pass to the task function
        """
        self.thread = QtCore.QThread()
        self.worker = Worker(task_func, *args, **kwargs)
        self.worker.moveToThread(self.thread)

        # Connect signals/slots
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

    def start(self):
        """Start the thread and the worker"""
        self.thread.start()

    def connect(self, signal_name: str, slot_func: Callable):
        """
        Connect a worker signal to a slot function.

        Args:
            signal_name: Name of the signal to connect (started, finished, error, result, progress, status)
            slot_func: Function to call when the signal is emitted
        """
        signal = getattr(self.worker, signal_name, None)
        if signal is not None:
            signal.connect(slot_func)
        else:
            raise ValueError(f"Unknown signal: {signal_name}")

    def wait(self, timeout: Optional[int] = None):
        """
        Wait for the thread to finish.

        Args:
            timeout: Maximum time to wait in milliseconds
        """
        try:
            if self.thread.isRunning():
                return self.thread.wait(timeout)
            return True
        except RuntimeError:
            # If the QThread object has already been deleted, just return True
            logger.warning("Thread object already deleted while waiting")
            return True

    def abort(self):
        """Abort the worker and wait for the thread to finish"""
        try:
            # First check if the worker still exists and can be aborted
            if (
                hasattr(self, "worker")
                and self.worker is not None
                and hasattr(self.worker, "is_running")
            ):
                try:
                    if self.worker.is_running():
                        self.worker.abort()
                except RuntimeError:
                    # Worker's Qt object might have been deleted
                    logger.debug("Worker object already deleted")

            # Then check if the thread still exists and is running
            if hasattr(self, "thread") and self.thread is not None:
                try:
                    # Use a safe try/except around thread operations
                    if self.thread.isRunning():
                        self.thread.quit()
                        # Use a reasonable timeout
                        self.thread.wait(2000)  # Wait up to 2 seconds
                except (RuntimeError, AttributeError, Exception) as e:
                    # Thread C++ object might have been deleted
                    logger.debug(f"Thread object not accessible: {str(e)}")

                # Clear the reference to potentially deleted objects
                self.thread = None

            if hasattr(self, "worker"):
                self.worker = None

        except (RuntimeError, AttributeError, Exception) as e:
            # If any objects have already been deleted, just log and continue
            logger.warning(f"Error during thread abort: {str(e)}")


class ThreadPool:
    """
    A pool of threads for executing multiple tasks in parallel.
    """

    def __init__(self, max_threads: int = 10):
        """
        Initialize the thread pool with a maximum number of threads.

        Args:
            max_threads: Maximum number of threads to use
        """
        self.max_threads = max_threads
        self.controllers: List[ThreadController] = []
        self.active_count = 0

    def start_task(self, task_func: Callable, *args, **kwargs) -> ThreadController:
        """
        Start a new task in the thread pool.

        Args:
            task_func: The function to run in the thread
            *args, **kwargs: Arguments to pass to the task function

        Returns:
            ThreadController: The controller for the new thread
        """
        # Clean up completed threads
        valid_controllers = []
        for c in self.controllers:
            try:
                if c.thread is not None and c.thread.isRunning():
                    valid_controllers.append(c)
            except RuntimeError:
                # Thread was already deleted, skip it
                pass
        self.controllers = valid_controllers

        # Create and start a new thread controller
        controller = ThreadController(task_func, *args, **kwargs)

        # Connect to track active count
        controller.connect("started", lambda: self._increment_active())
        controller.connect("finished", lambda: self._decrement_active())

        self.controllers.append(controller)
        controller.start()
        return controller

    def _increment_active(self):
        """Increment the active thread count"""
        self.active_count += 1

    def _decrement_active(self):
        """Decrement the active thread count"""
        self.active_count -= 1

    def stop_all(self):
        """Stop all threads in the pool"""
        for controller in self.controllers:
            controller.abort()

    def wait_all(self, timeout_ms: int = 5000):
        """
        Wait for all threads to complete.

        Args:
            timeout_ms: Maximum time to wait in milliseconds for each thread
        """
        for controller in self.controllers:
            try:
                controller.wait(timeout_ms)
            except Exception as e:
                logger.error(f"Error waiting for thread: {e}")


# Global thread pool for the application
global_thread_pool = ThreadPool()


def run_in_thread(task_func: Callable, *args, **kwargs) -> ThreadController:
    """
    Convenience function to run a task in a thread.

    Args:
        task_func: The function to run in the thread
        *args, **kwargs: Arguments to pass to the task function

    Returns:
        ThreadController: The controller for the new thread
    """
    return global_thread_pool.start_task(task_func, *args, **kwargs)


def cleanup_threads():
    """
    Clean up all threads in the global thread pool.
    Call this function before the application exits.
    """
    try:
        logger.debug("Cleaning up all threads")
        global_thread_pool.stop_all()
        global_thread_pool.wait_all()
        logger.debug("Thread cleanup completed")
    except Exception as e:
        logger.error(f"Error during thread cleanup: {e}")
        # Continue despite errors, don't raise exceptions during cleanup
