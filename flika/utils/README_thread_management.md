# Thread Management in Flika

This document outlines the thread management system in Flika and provides guidance on how to use it.

## Overview

Flika's thread management system is designed to provide a consistent, safe way to implement background threads in the application. It follows Qt's best practices and addresses common pitfalls associated with threading in PyQt/PySide applications.

## Key Components

### ThreadManager Module

The `thread_manager.py` module provides several core components:

1. **Worker Pattern**: A pattern that follows Qt's recommended approach for thread management
2. **Thread Pool**: A system for managing multiple worker threads
3. **Thread Controller**: A class to control and monitor threads
4. **Convenience Functions**: Helper functions for common threading operations

### Classes and Functions

- `Worker`: A QObject that can be moved to a QThread
- `ThreadController`: Manages the lifecycle of a Worker and its thread
- `ThreadPool`: A pool for managing multiple ThreadControllers
- `StoppableThread`: A standard Python thread with stop functionality
- `run_in_thread()`: A convenience function to quickly run a task in a thread
- `cleanup_threads()`: A function to safely clean up all threads

## Using the System

### Simple Background Task

```python
from flika.utils.thread_manager import run_in_thread

def my_background_task(param1, param2):
    # Do some long-running work
    return result

# Run the task in a background thread
controller = run_in_thread(my_background_task, param1, param2)

# Connect to signals
controller.connect('result', lambda result: print(f"Task completed with result: {result}"))
controller.connect('error', lambda error: print(f"Task failed: {error}"))
```

### Progress Reporting

```python
def task_with_progress(worker=None):
    for i in range(100):
        # Do some work
        if worker:
            worker.progress.emit(i)
            if worker.should_abort():
                return "Aborted"
    return "Complete"

controller = run_in_thread(task_with_progress)
controller.connect('progress', lambda percent: print(f"Progress: {percent}%"))
```

### Cleanup

Always clean up threads before the application exits:

```python
from flika.utils.thread_manager import cleanup_threads

# In your application's cleanup code:
cleanup_threads()
```

## Best Practices

1. **Never subclass QThread** - Use the Worker pattern instead
2. **Always connect to signals/slots** before starting the thread
3. **Check for abort signals** in long-running tasks
4. **Use cleanup_threads()** before application exit
5. **Avoid shared mutable state** between threads
6. **Keep GUI operations in the main thread** - use signals to communicate with the GUI

## Implementation Example

### Before (old way):

```python
class MyThread(QtCore.QThread):
    def __init__(self):
        QtCore.QThread.__init__(self)
        
    def run(self):
        # Do some work
        result = complex_calculation()
        # How to return the result?
```

### After (new way):

```python
from flika.utils.thread_manager import run_in_thread

def complex_calculation():
    # Do some work
    return result

# Run in a thread and handle the result
controller = run_in_thread(complex_calculation)
controller.connect('result', handle_result)
controller.connect('error', handle_error)
```

## Thread Safety Considerations

- Never access GUI elements directly from worker threads
- Use signals to communicate between threads
- Be cautious with shared resources
- Consider using thread-safe containers (Queue) for inter-thread communication

## Common Issues and Solutions

### Issue: Application crashes on exit
**Solution**: Call `cleanup_threads()` before application exit

### Issue: GUI freezes during operation
**Solution**: Move the operation to a background thread using `run_in_thread()`

### Issue: Thread results not appearing
**Solution**: Ensure you've connected to the 'result' signal before starting the thread

## For Plugin Developers

Plugin developers should use the thread_manager module instead of implementing their own threading solutions. This ensures compatibility with the rest of the application and proper cleanup during application exit.

```python
from flika.utils.thread_manager import run_in_thread

def my_plugin_background_task():
    # Plugin-specific code
    pass

controller = run_in_thread(my_plugin_background_task)
``` 