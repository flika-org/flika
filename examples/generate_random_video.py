"""
Random Image Stack Example

This example demonstrates how to generate a random image stack using flika
and perform basic operations on it.
"""

from utils import run_in_ipython


def random_image_demo():
    """Generate a random image stack and display information about it."""
    import flika
    import flika.global_vars as g  # noqa: F401

    # Start flika
    print("Starting flika...")
    flika.start_flika()

    # Generate a random image stack
    print("Generating random image stack...")
    window = flika.process.stacks.generate_random_image(nFrames=100, width=128)

    # Display information about the generated image stack
    print(f"Created window: {window.name}")
    print(f"Image dimensions: {window.image.shape}")
    print(f"Data type: {window.image.dtype}")


if __name__ == "__main__":
    # Run the demo in IPython
    run_in_ipython(random_image_demo)
