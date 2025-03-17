"""
IPython helper utilities for flika examples.

This module provides functions to help run flika scripts in IPython.
"""

import inspect
import subprocess
from typing import Callable


def run_in_ipython(func: Callable) -> None:
    """
    Run a function in IPython interactive mode.

    Args:
        func: The function to run in IPython

    Example:
        def my_flika_script():
            import flika
            flika.start_flika()
            # More code here...

        run_in_ipython(my_flika_script)
    """
    # Extract the script content, removing the initial indentation
    script_str = "\n".join(
        line[min(len(line) - len(line.lstrip()), 4) :]
        for line in inspect.getsource(func).splitlines()[1:]
    )

    # Start IPython with our script and keep the session interactive
    print(f"Launching IPython with {func.__name__}...")
    subprocess.run(
        [
            "ipython",
            "-i",
            "-c",
            f"{script_str}",
        ]
    )

    print("IPython session has ended.")
