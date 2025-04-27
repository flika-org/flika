# Flika Examples

This directory contains example scripts demonstrating various features and use cases of Flika, an interactive image processing program for biologists.

## Running Examples

### Prerequisites

These examples assume you have Flika installed in your Python environment. If you haven't already installed Flika, follow these steps:

```bash
# Clone the repository (if you haven't already)
git clone https://github.com/flika-org/flika.git
cd flika

# Create and activate a virtual environment (recommended)
python -m venv ~/venvs/flika
source ~/venvs/flika/bin/activate

# Install flika in development mode
pip install -e .
```

### Running an Example

Each example can be run directly with Python:

```bash
python examples/generate_random_video.py
```

All examples launch an IPython interactive terminal by default, allowing you to interact with the flika objects after the initial script runs.

## Utils Directory

The `utils/` subdirectory contains shared code and utilities used across multiple examples:

- `ipython_helper.py`: Helpers for running scripts in IPython
- Common initialization code
- Shared helper functions

### Using the IPython Helper

All examples use the `run_in_ipython` helper to create an interactive IPython environment. You can use this in your own examples:

```python
from utils import run_in_ipython

def my_flika_demo():
    import flika
    flika.start_flika()
    # Your flika code here

if __name__ == "__main__":
    run_in_ipython(my_flika_demo)
```