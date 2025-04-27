"""
Process module for flika - provides image processing operations.
"""

# Import specific functions/classes from each module
from flika.process.binary import (
    adaptive_threshold,
    binary_dilation,
    binary_erosion,
    canny_edge_detector,
    generate_rois,
    logically_combine,
    remove_small_blobs,
    threshold,
)
from flika.process.color import split_channels
from flika.process.file_ import close, open_file
from flika.process.filters import (
    bilateral_filter,
    boxcar_differential_filter,
    butterworth_filter,
    difference_filter,
    difference_of_gaussians,
    fourier_filter,
    gaussian_blur,
    mean_filter,
    median_filter,
    variance_filter,
    wavelet_filter,
)
from flika.process.math_ import (
    absolute_value,
    divide,
    divide_trace,
    multiply,
    power,
    ratio,
    sqrt,
    subtract,
    subtract_trace,
)
from flika.process.measure import measure
from flika.process.overlay import background, scale_bar, time_stamp
from flika.process.roi import set_value
from flika.process.stacks import (
    change_datatype,
    concatenate_stacks,
    deinterleave,
    duplicate,
    frame_binning,
    generate_random_image,
    image_calculator,
    pixel_binning,
    resize,
    trim,
    zproject,
)

# Define what's available when using `from flika.process import *`
__all__ = [
    # binary module
    "threshold",
    "remove_small_blobs",
    "adaptive_threshold",
    "logically_combine",
    "binary_dilation",
    "binary_erosion",
    "generate_rois",
    "canny_edge_detector",
    # color module
    "split_channels",
    # file_ module
    "open_file",
    "close",
    # filters module
    "gaussian_blur",
    "difference_of_gaussians",
    "mean_filter",
    "variance_filter",
    "median_filter",
    "butterworth_filter",
    "boxcar_differential_filter",
    "wavelet_filter",
    "difference_filter",
    "fourier_filter",
    "bilateral_filter",
    # math_ module
    "subtract",
    "multiply",
    "divide",
    "power",
    "sqrt",
    "ratio",
    "absolute_value",
    "subtract_trace",
    "divide_trace",
    # measure module
    "measure",
    # overlay module
    "time_stamp",
    "background",
    "scale_bar",
    # roi module
    "set_value",
    # stacks module
    "deinterleave",
    "trim",
    "zproject",
    "image_calculator",
    "pixel_binning",
    "frame_binning",
    "resize",
    "concatenate_stacks",
    "duplicate",
    "generate_random_image",
    "change_datatype",
]


def setup_menus():
    """Set up the flika menu structure for process operations."""
    import flika.global_vars as g

    if len(g.menus) > 0:
        print("flika menubar already initialized.")
        return
    from qtpy import QtWidgets

    imageMenu = QtWidgets.QMenu("Image")
    processMenu = QtWidgets.QMenu("Process")

    def addAction(menu, name, trigger):
        menu.addAction(QtWidgets.QAction(name, menu, triggered=trigger))

    stacksMenu = imageMenu.addMenu("Stacks")

    addAction(stacksMenu, "Duplicate", duplicate)
    addAction(stacksMenu, "Generate Random Image", generate_random_image.gui)
    addAction(stacksMenu, "Trim Frames", trim.gui)
    addAction(stacksMenu, "Deinterlace", deinterleave.gui)
    addAction(stacksMenu, "Z Project", zproject.gui)
    addAction(stacksMenu, "Pixel Binning", pixel_binning.gui)
    addAction(stacksMenu, "Frame Binning", frame_binning.gui)
    addAction(stacksMenu, "Resize", resize.gui)
    addAction(stacksMenu, "Concatenate Stacks", concatenate_stacks.gui)
    addAction(stacksMenu, "Change Data Type", change_datatype.gui)

    colorMenu = imageMenu.addMenu("Color")
    addAction(colorMenu, "Split Channels", split_channels.gui)

    addAction(imageMenu, "Measure", measure.gui)
    addAction(imageMenu, "Set Value", set_value.gui)
    overlayMenu = imageMenu.addMenu("Overlay")
    addAction(overlayMenu, "Background", background.gui)
    addAction(overlayMenu, "Timestamp", time_stamp.gui)
    addAction(overlayMenu, "Scale Bar", scale_bar.gui)

    binaryMenu = processMenu.addMenu("Binary")
    mathMenu = processMenu.addMenu("Math")
    filtersMenu = processMenu.addMenu("Filters")
    processMenu.addAction(
        QtWidgets.QAction(
            "Image Calculator", processMenu, triggered=image_calculator.gui
        )
    )

    addAction(binaryMenu, "Threshold", threshold.gui)
    addAction(binaryMenu, "Adaptive Threshold", adaptive_threshold.gui)
    addAction(binaryMenu, "Canny Edge Detector", canny_edge_detector.gui)
    binaryMenu.addSeparator()
    addAction(binaryMenu, "Logically Combine", logically_combine.gui)
    addAction(binaryMenu, "Remove Small Blobs", remove_small_blobs.gui)
    addAction(binaryMenu, "Binary Erosion", binary_erosion.gui)
    addAction(binaryMenu, "Binary Dilation", binary_dilation.gui)
    addAction(binaryMenu, "Generate ROIs", generate_rois.gui)

    addAction(mathMenu, "Multiply", multiply.gui)
    addAction(mathMenu, "Divide", divide.gui)
    addAction(mathMenu, "Subtract", subtract.gui)
    addAction(mathMenu, "Power", power.gui)
    addAction(mathMenu, "Square Root", sqrt.gui)
    addAction(mathMenu, "Ratio By Baseline", ratio.gui)
    addAction(mathMenu, "Absolute Value", absolute_value.gui)
    addAction(mathMenu, "Subtract Trace", subtract_trace.gui)
    addAction(mathMenu, "Divide Trace", divide_trace.gui)

    addAction(filtersMenu, "Gaussian Blur", gaussian_blur.gui)
    addAction(filtersMenu, "Difference of Gaussians", difference_of_gaussians.gui)
    filtersMenu.addSeparator()
    addAction(filtersMenu, "Butterworth Filter", butterworth_filter.gui)
    addAction(filtersMenu, "Mean Filter", mean_filter.gui)
    addAction(filtersMenu, "Variance Filter", variance_filter.gui)
    addAction(filtersMenu, "Median Filter", median_filter.gui)
    addAction(filtersMenu, "Fourier Filter", fourier_filter.gui)
    addAction(filtersMenu, "Difference Filter", difference_filter.gui)
    addAction(filtersMenu, "Boxcar Differential", boxcar_differential_filter.gui)
    addAction(filtersMenu, "Wavelet Filter", wavelet_filter.gui)
    addAction(filtersMenu, "Bilateral Filter", bilateral_filter.gui)

    g.menus.append(imageMenu)
    g.menus.append(processMenu)
