"""
Subtract Trace Example

This example demonstrates how to create an ROI, plot its trace, and then use
the subtract_trace function to subtract the trace from each frame in a video.
"""

from utils import run_in_ipython


def subtract_trace_demo():
    """Generate a video, create an ROI, and subtract the trace from each frame."""
    import numpy as np

    import flika
    from flika.roi import makeROI

    # Start flika
    print("Starting flika...")
    flika.start_flika()

    # Generate a random image stack with a simulated signal
    print("Generating synthetic video with a pulsing signal...")
    # Create base noise
    width, height = 128, 128
    nFrames = 100
    base_video = np.random.randn(nFrames, height, width) * 0.5

    # Add a pulsing signal in a small region (simulating a biological signal)
    signal_x, signal_y = width // 3, height // 3
    signal_width, signal_height = width // 4, height // 4

    # Create a pulsing signal (sine wave)
    time = np.arange(nFrames)
    signal = 2 * np.sin(2 * np.pi * time / 20) + 2  # Period of 20 frames

    # Add signal to the specific region
    for t in range(nFrames):
        base_video[
            t, signal_y : signal_y + signal_height, signal_x : signal_x + signal_width
        ] += signal[t]

    # Create the window with the synthetic video
    window = flika.window.Window(base_video, "Synthetic Video")

    # Display information about the generated image stack
    print(f"Created window: {window.name}")
    print(f"Image dimensions: {window.image.shape}")

    # Create a rectangular ROI over the signal area
    print("\nCreating ROI over the signal area...")
    roi_pts = np.array(
        [[signal_x, signal_y], [signal_x + signal_width, signal_y + signal_height]]
    )
    roi = makeROI("rectangle", roi_pts, window)

    # Plot the ROI to get the trace
    print("Plotting ROI trace...")
    trace_window = roi.plot()

    # The last plotted ROI trace is now accessible via g.currentTrace
    print(f"Trace window created: {trace_window}")
    print("The trace shows the pulsing signal that was added to the video")

    # Now use subtract_trace to remove the trace from each frame
    print("\nSubtracting the trace from each frame...")
    result_window = flika.process.math_.subtract_trace(keepSourceWindow=True)

    # Display information about the resulting window
    print(f"Result window: {result_window.name}")
    print("The signal has been removed, leaving mostly random noise")

    # Verify the effect of the subtract_trace operation
    print("\nVerifying subtract_trace operation:")
    # Get the trace from the same region in the result window
    result_roi = makeROI("rectangle", roi_pts, result_window)
    result_trace_window = result_roi.plot()

    # Now the trace should be much flatter (close to zero)
    print("The new trace should be much flatter, indicating the signal was removed")

    # Display both windows side by side for comparison
    print("\nCompare the original and result windows to see the effect")
    print(
        "The result window should have the pulsing signal removed from the ROI region"
    )


if __name__ == "__main__":
    # Run the demo in IPython
    run_in_ipython(subtract_trace_demo)
