from .stacks import deinterleave, trim, zproject, image_calculator, pixel_binning, frame_binning, resize, change_datatype, concatenate_stacks
from .math_ import multiply, subtract, power, ratio, absolute_value, subtract_trace, divide_trace
from .filters import gaussian_blur, butterworth_filter,boxcar_differential_filter, wavelet_filter, difference_filter, fourier_filter, mean_filter, median_filter, bilateral_filter
from .binary import threshold, adaptive_threshold, canny_edge_detector, remove_small_blobs, logically_combine, binary_dilation, binary_erosion, generate_rois
from .roi import set_value
from .measure import measure
from .color import split_channels
from .overlay import time_stamp,background, scale_bar
from .file_ import open_file, open_file_gui, save_file_gui, load_metadata, save_file, save_movie, save_movie_gui, save_points, load_points, save_current_frame, save_roi_traces



def setup_menus():
	import flika.global_vars as g
	from qtpy import QtGui, QtWidgets
	imageMenu = QtWidgets.QMenu("Image")
	processMenu = QtWidgets.QMenu("Process")
	
	def addAction(menu, name, trigger):
		menu.addAction(QtWidgets.QAction(name, menu, triggered=trigger))

	stacksMenu = imageMenu.addMenu("Stacks")
	
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
	processMenu.addAction(QtWidgets.QAction("Image Calculator", processMenu, triggered=image_calculator.gui))

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
	addAction(mathMenu,"Subtract", subtract.gui)
	addAction(mathMenu, "Power", power.gui)
	addAction(mathMenu, "Ratio By Baseline", ratio.gui)
	addAction(mathMenu, "Absolute Value", absolute_value.gui)
	addAction(mathMenu, "Subtract Trace", subtract_trace.gui)
	addAction(mathMenu, "Divide Trace", divide_trace.gui)

	addAction(filtersMenu, "Gaussian Blur", gaussian_blur.gui)
	filtersMenu.addSeparator()
	addAction(filtersMenu, "Butterworth Filter", butterworth_filter.gui)
	addAction(filtersMenu, "Mean Filter", mean_filter.gui)
	addAction(filtersMenu, "Median Filter", median_filter.gui)
	addAction(filtersMenu, "Fourier Filter", fourier_filter.gui)
	addAction(filtersMenu, "Difference Filter", difference_filter.gui)
	addAction(filtersMenu, "Boxcar Differential", boxcar_differential_filter.gui)
	addAction(filtersMenu, "Wavelet Filter", wavelet_filter.gui)
	addAction(filtersMenu, "Bilateral Filter", bilateral_filter.gui)

	g.menus.append(imageMenu)
	g.menus.append(processMenu)
