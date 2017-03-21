import sys, os
import optparse

from ..process import *
from .. import global_vars as g
from ..window import Window
from ..roi import makeROI
import numpy as np
import time
import pytest
import warnings
warnings.filterwarnings("ignore")


g.settings['multiprocessing'] = False
zproject.gui()
obj = [i for i in zproject.items if i['name'] == 'projection_type'][0]['object']
ZPROJECTS = [obj.itemText(i) for i in range(obj.count())]
zproject.ui.close()

image_calculator.gui()
obj = [i for i in image_calculator.items if i['name'] == 'operation'][0]['object']
OPERANDS = [obj.itemText(i) for i in range(obj.count())]
image_calculator.ui.close()



@pytest.mark.parametrize("img", [
    (np.random.randint(2, size=[10, 20, 20]).astype("uint8")),
    (np.random.randint(2, size=[10, 20, 20]).astype("uint16")),
    (np.random.randint(2, size=[10, 20, 20]).astype("uint32")),
    (np.random.randint(2, size=[10, 20, 20]).astype("uint64")),
    (np.random.randint(2, size=[10, 20, 20]).astype("int8")),
    (np.random.randint(2, size=[10, 20, 20]).astype("int16")),
    (np.random.randint(2, size=[10, 20, 20]).astype("int32")),
    (np.random.randint(2, size=[10, 20, 20]).astype("int64")),
    (np.random.randint(2, size=[10, 20, 20]).astype("float16")),
    (np.random.randint(2, size=[10, 20, 20]).astype("float32")),
    (np.random.randint(2, size=[10, 20, 20]).astype("float64")),
    ((np.random.random([10, 20, 20])*10).astype("uint8")),
    ((np.random.random([10, 20, 20])*10).astype("uint16")),
    ((np.random.random([10, 20, 20])*10).astype("uint32")),
    ((np.random.random([10, 20, 20])*10).astype("uint64")),
    ((np.random.random([10, 20, 20])*10).astype("int8")),
    ((np.random.random([10, 20, 20])*10).astype("int16")),
    ((np.random.random([10, 20, 20])*10).astype("int32")),
    ((np.random.random([10, 20, 20])*10).astype("int64")),
    (np.random.random([10, 20, 20]).astype('float16')),
    (np.random.random([10, 20, 20]).astype('float32')),
    (np.random.random([10, 20, 20]).astype('float64')),
   	((np.random.random([10, 20, 20, 3])*10).astype("uint8")),
    ((np.random.random([10, 20, 20, 3])*10).astype("uint16")),
    ((np.random.random([10, 20, 20, 3])*10).astype("uint32")),
    ((np.random.random([10, 20, 20, 3])*10).astype("uint64")),
    ((np.random.random([10, 20, 20, 3])*10).astype("int8")),
    ((np.random.random([10, 20, 20, 3])*10).astype("int16")),
    ((np.random.random([10, 20, 20, 3])*10).astype("int32")),
    ((np.random.random([10, 20, 20, 3])*10).astype("int64")),
    (np.random.random([10, 20, 20, 3]).astype('float16')),
    (np.random.random([10, 20, 20, 3]).astype('float32')),
    (np.random.random([10, 20, 20, 3]).astype('float64')),
   	((np.random.random([20, 20])*10).astype("uint8")),
    ((np.random.random([20, 20])*10).astype("uint16")),
    ((np.random.random([20, 20])*10).astype("uint32")),
    ((np.random.random([20, 20])*10).astype("uint64")),
    ((np.random.random([20, 20])*10).astype("int8")),
    ((np.random.random([20, 20])*10).astype("int16")),
    ((np.random.random([20, 20])*10).astype("int32")),
    ((np.random.random([20, 20])*10).astype("int64")),
    (np.random.random([20, 20]).astype('float16')),
    (np.random.random([20, 20]).astype('float32')),
    (np.random.random([20, 20]).astype('float64')),
   	((np.random.random([20, 20, 3])*10).astype("uint8")),
    ((np.random.random([20, 20, 3])*10).astype("uint16")),
    ((np.random.random([20, 20, 3])*10).astype("uint32")),
    ((np.random.random([20, 20, 3])*10).astype("uint64")),
    ((np.random.random([20, 20, 3])*10).astype("int8")),
    ((np.random.random([20, 20, 3])*10).astype("int16")),
    ((np.random.random([20, 20, 3])*10).astype("int32")),
    ((np.random.random([20, 20, 3])*10).astype("int64")),
    (np.random.random([20, 20, 3]).astype('float16')),
    (np.random.random([20, 20, 3]).astype('float32')),
    (np.random.random([20, 20, 3]).astype('float64')),
])
class ProcessTest:
	def teardown_method(self):
		from .conftest import fa
		fa().clear()


class TestBinary(ProcessTest):
	
	def test_threshold(self, img, fa):
		w1 = Window(img)
		w = threshold(.5)
		

	def test_adaptive_threshold(self, img, fa):
		w1 = Window(img)
		w = adaptive_threshold(.5, 3)
		

	def test_canny_edge_detector(self, img):
		if img.ndim == 4:
			return
		w1 = Window(img)
		w = canny_edge_detector(.5)
		
	
	def test_binary_dilation(self, img):
		if img.ndim == 4 or not ((img==0)|(img==1)).all():
			return
		w1 = Window(img)
		w = binary_dilation(2, 3, 1)
		
	
	def test_binary_erosion(self, img):
		if img.ndim == 4 or not ((img==0)|(img==1)).all():
			return
		w1 = Window(img)
		w = binary_erosion(2, 3, 1)
		

	def test_generate_rois(self, img):
		if img.ndim == 4 or not ((img==0)|(img==1)).all():
			return
		w1 = Window(img)
		w = generate_rois(.5, 10)
		

	def test_remove_small_blobs(self, img):
		if img.ndim == 4 or not ((img==0)|(img==1)).all():
			return
		w1 = Window(img)
		w = threshold(.5)
		


class TestFilters(ProcessTest):
	def test_gaussian_blur(self, img):
		w1 = Window(img)
		w = gaussian_blur(.5)
		

	def test_butterworth_filter(self, img):
		w1 = Window(img)
		w = butterworth_filter(1, .2, .6)
		

	def test_mean_filter(self, img):
		w1 = Window(img)
		w = mean_filter(5)
		

	def test_median_filter(self, img):
		w1 = Window(img)
		w = median_filter(5)
		

	def test_fourier_filter(self, img):
		w1 = Window(img)
		w = fourier_filter(3, .2, .6, False)
		

	def test_difference_filter(self, img):
		w1 = Window(img)
		w = difference_filter()
		

	def test_boxcar_differential_filter(self, img):
		w1 = Window(img)
		w = boxcar_differential_filter(2, 3)
		

	def test_wavelet_filter(self, img):
		w1 = Window(img)
		w = wavelet_filter(2, 3)
		

	def test_bilateral_filter(self, img):
		w1 = Window(img)
		w = bilateral_filter(True, 30, 10, .05, 100) # soft filter
		w2 = bilateral_filter(False, 30, 10, .05, 100) # hard filter
		

class TestMath(ProcessTest):
	def test_subtract(self, img):
		w1 = Window(img)
		subtract(2)
		

	def test_subtract_trace(self, img):
		w1 = Window(img)
		roi1 = makeROI('rectangle', [[3, 3], [5, 6]])
		tr = roi1.plot()
		if tr:
			subtract_trace()
		

	def test_divide_trace(self, img):
		w1 = Window(img)
		roi1 = makeROI('rectangle', [[3, 3], [5, 6]])
		tr = roi1.plot()
		if tr:
			divide_trace()
		

	def test_multiply(self, img):
		w1 = Window(img)
		multiply(2.4)
		

	def test_power(self, img):
		w1 = Window(img)
		power(2)
		

	def test_ratio(self, img):
		w1 = Window(img)
		ratio(2, 6, 'average')
		ratio(2, 6, 'standard deviation')
		

	def test_absolute_value(self, img):
		w1 = Window(img)
		absolute_value()
		

class TestOverlay(ProcessTest):
	def test_time_stamp(self, img):
		w1 = Window(img)
		time_stamp(2)
		

	def test_background(self, img):
		w1 = Window(img)
		w2 = Window(img/2)
		background(w1, w2, .5, True)
		

	def test_scale_bar(self, img):
		w1 = Window(img)
		scale_bar.gui()
		scale_bar(30, 5, 12, 'White', 'None','Lower Left')
		

class TestColor(ProcessTest):
	def test_split_channels(self, img):
		if img.ndim == 4 or (img.ndim == 3 and img.shape[2] == 3):
			w1 = Window(img)
			split_channels()
		

class TestROIProcess(ProcessTest):
	def test_set_value(self, img):
		w1 = Window(img)
		roi = makeROI('rectangle', [[3, 3], [4, 5]])
		set_value(2, 2, 5)
		

class TestStacks(ProcessTest):
	def test_deinterleave(self, img):
		w1 = Window(img)
		deinterleave(2)
		

	def test_trim(self, img):
		w1 = Window(img)
		trim(2, 6, 2)
		

	def test_zproject(self, img):
		w1 = Window(img)
		
		for i in ZPROJECTS:
			w3 = zproject(2, 6, i, True)
			if isinstance(w3, Window):
				w3.close()
			w1.setAsCurrentWindow()
		

	def test_image_calculator(self, img):
		w1 = Window(img)
		w2 = Window(img)
		for i in OPERANDS:
			w3 = image_calculator(w1, w2, i, True)
			if isinstance(w3, Window):
				w3.close()
		

	def test_pixel_binning(self, img):
		w1 = Window(img)
		pixel_binning(2)
		

	def test_frame_binning(self, img):
		w1 = Window(img)
		frame_binning(2)
		

	def test_resize(self, img):
		w1 = Window(img)
		resize(2)
		
