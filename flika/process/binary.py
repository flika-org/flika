"""
Binary image processing functions for the flika package.
"""
import numpy as np
import scipy
import scipy.ndimage
import skimage
from skimage import feature, measure
from skimage.filters.thresholding import threshold_local
from skimage.morphology import remove_small_objects
from qtpy import QtCore, QtGui, QtWidgets
import beartype
import jaxtyping

# Local application imports
import flika.window
from flika import global_vars as g
from flika.utils.BaseProcess import BaseProcess
from flika.utils.custom_widgets import (
    SliderLabel, WindowSelector, MissingWindowError, CheckBox, ComboBox
)
from flika.roi import makeROI, ROI_Drawing

__all__ = [
    'threshold', 'remove_small_blobs', 'adaptive_threshold', 'logically_combine',
    'binary_dilation', 'binary_erosion', 'generate_rois', 'canny_edge_detector'
]

@beartype.beartype
def convert2uint8(tif: np.ndarray) -> jaxtyping.Num[np.ndarray, "... uint8"]:
    """Convert any array to uint8 format with proper scaling.
    
    Args:
        tif: Input array to be converted
        
    Returns:
        Array in uint8 format
    """
    oldmin = np.min(tif)
    oldmax = np.max(tif)
    newmax = 2**8-1
    scaled_tif = ((tif-oldmin)*newmax)/(oldmax-oldmin)
    return scaled_tif.astype(np.uint8)





class Threshold(BaseProcess):
    """Applies a threshold to an image to create a binary mask.
    
    Parameters:
        value (float): The threshold to be applied
        darkBackground (bool): If True, pixels below the threshold will be True
        keepSourceWindow (bool): If True, don't close the source window
        
    Returns:
        newWindow: A new window with the thresholded image
    """
    
    def gui(self) -> None:
        self.gui_reset()
        valueSlider = SliderLabel(2)
        if g.win is not None:
            image = g.win.image
            valueSlider.setRange(np.min(image), np.max(image))
            valueSlider.setValue(np.mean(image))
        preview = CheckBox()
        preview.setChecked(True)
        self.items.append({'name': 'value', 'string': 'Value', 'object': valueSlider})
        self.items.append({'name': 'darkBackground', 'string': 'Dark Background', 'object': CheckBox()})
        self.items.append({'name': 'preview', 'string': 'Preview', 'object': preview})
        super().gui()

    
    def __call__(
        self, 
        value: float, 
        darkBackground: bool = False, 
        keepSourceWindow: bool = False
    ) -> flika.window.Window | None:
        self.start(keepSourceWindow)
        if self.oldwindow.nDims > 3:
            g.alert("You cannot run this function on an image of dimension greater than 3. If your window has color, convert to a grayscale image before running this function")
            return None
        
        if darkBackground:
            newtif = self.tif < value
        else:
            newtif = self.tif > value
            
        self.newtif = newtif.astype(np.uint8)
        self.newname = f"{self.oldname} - Thresholded {value}"
        return self.end()

    
    def preview(self) -> None:
        if g.win is None or g.win.closed:
            return
            
        win = g.win
        value = self.getValue('value')
        preview = self.getValue('preview')
        darkBackground = self.getValue('darkBackground')
        
        if win.nDims > 3:
            g.alert("You cannot run this function on an image of dimension greater than 3. If your window has color, convert to a grayscale image before running this function")
            return None
            
        if preview:
            if win.nDims == 3:  # if the image is 3d
                testimage = np.copy(win.image[win.currentIndex])
            elif win.nDims == 2:
                testimage = np.copy(win.image)
                
            if darkBackground:
                testimage = testimage < value
            else:
                testimage = testimage > value
                
            win.imageview.setImage(testimage, autoLevels=False)
            win.imageview.setLevels(-.1, 1.1)
        else:
            win.reset()
            if win.nDims == 3:
                image = win.image[win.currentIndex]
            else:
                image = win.image
            win.imageview.setLevels(np.min(image), np.max(image))


threshold = Threshold()

class BlocksizeSlider(SliderLabel):
    """A slider that only allows odd values."""
    
    def __init__(self, decimals: int = 0):
        SliderLabel.__init__(self, decimals)
        
    def updateSlider(self, value: int) -> None:
        if value % 2 == 0:
            if value < self.slider.value():
                value -= 1
            else:
                value += 1
            self.label.setValue(value)
        self.slider.setValue(int(value * 10**self.decimals))
        
    def updateLabel(self, value: int|float) -> None:
        if value % 2 == 0:
            value -= 1
        self.label.setValue(value)

class Adaptive_threshold(BaseProcess):
    """Applies an adaptive threshold to an image using the scikit-image threshold_local function.
    
    Parameters:
        value (int): The threshold offset to be applied
        block_size (int): Size of pixel neighborhood used to calculate the threshold (must be odd)
        darkBackground (bool): If True, pixels below the threshold will be True
        keepSourceWindow (bool): If True, don't close the source window
        
    Returns:
        newWindow: A new window with the thresholded image
    """
    
    
    def gui(self) -> None:
        self.gui_reset()
        valueSlider = SliderLabel(2)
        valueSlider.setRange(-20, 20)
        valueSlider.setValue(0)
        
        block_size = BlocksizeSlider(0)
        if g.win is not None:
            max_block = int(max([g.win.image.shape[-1], g.win.image.shape[-2]]) / 2)
        else:
            max_block = 100
        block_size.setRange(3, max_block)
        
        preview = CheckBox()
        preview.setChecked(True)
        
        self.items.append({'name': 'value', 'string': 'Value', 'object': valueSlider})
        self.items.append({'name': 'block_size', 'string': 'Block Size', 'object': block_size})
        self.items.append({'name': 'darkBackground', 'string': 'Dark Background', 'object': CheckBox()})
        self.items.append({'name': 'preview', 'string': 'Preview', 'object': preview})
        
        super().gui()
        self.preview()

    
    def __call__(
        self, 
        value: float, 
        block_size: int, 
        darkBackground: bool = False, 
        keepSourceWindow: bool = False
    ) -> flika.window.Window | None:
        self.start(keepSourceWindow)
        
        if self.tif.dtype == np.float16:
            g.alert("Local Threshold does not support float16 type arrays")
            return None
            
        newtif = np.copy(self.tif)

        if self.oldwindow.nDims == 2:
            newtif = threshold_local(newtif, block_size, offset=value)
        elif self.oldwindow.nDims == 3:
            for i in range(len(newtif)):
                newtif[i] = threshold_local(newtif[i], block_size, offset=value)
        else:
            g.alert("You cannot run this function on an image of dimension greater than 3. If your window has color, convert to a grayscale image before running this function")
            return None
            
        if darkBackground:
            newtif = np.logical_not(newtif)
            
        self.newtif = newtif.astype(np.uint8)
        self.newname = f"{self.oldname} - Thresholded {value}"
        return self.end()

    
    def preview(self) -> None:
        if g.win is None or g.win.closed:
            return
            
        win = g.win
        value = self.getValue('value')
        block_size = self.getValue('block_size')
        preview = self.getValue('preview')
        darkBackground = self.getValue('darkBackground')
        
        nDim = len(win.image.shape)
        if nDim > 3:
            g.alert("You cannot run this function on an image of dimension greater than 3. If your window has color, convert to a grayscale image before running this function")
            return None
            
        if preview:
            if nDim == 3:  # if the image is 3d
                testimage = np.copy(win.image[win.currentIndex])
            elif nDim == 2:
                testimage = np.copy(win.image)
                
            testimage = threshold_local(testimage, block_size, offset=value)
            
            if darkBackground:
                testimage = np.logical_not(testimage)
                
            testimage = testimage.astype(np.uint8)
            win.imageview.setImage(testimage, autoLevels=False)
            win.imageview.setLevels(-.1, 1.1)
        else:
            win.reset()
            if nDim == 3:
                image = win.image[win.currentIndex]
            else:
                image = win.image
            win.imageview.setLevels(np.min(image), np.max(image))


adaptive_threshold = Adaptive_threshold()


class Canny_edge_detector(BaseProcess):
    """Detects edges in an image using the Canny edge detection algorithm.
    
    Parameters:
        sigma (float): Standard deviation for Gaussian kernel
        keepSourceWindow (bool): If True, don't close the source window
        
    Returns:
        newWindow: A new window with the edge detection results
    """
    
    
    def gui(self) -> None:
        self.gui_reset()
        sigma = SliderLabel(2)
        if g.win is not None:
            sigma.setRange(0, 1000)
            sigma.setValue(1)
            
        preview = CheckBox()
        preview.setChecked(True)
        
        self.items.append({'name': 'sigma', 'string': 'Sigma', 'object': sigma})
        self.items.append({'name': 'preview', 'string': 'Preview', 'object': preview})
        
        super().gui()
        self.preview()
        
    
    def __call__(
        self, 
        sigma: float, 
        keepSourceWindow: bool = False
    ) -> flika.window.Window | None:
        self.start(keepSourceWindow)
        nDim = len(self.tif.shape)
        newtif = np.copy(self.tif)

        if self.tif.dtype == np.float16:
            g.alert("Canny Edge Detection does not work on float16 images. Change the data type to use this function.")
            return None

        if nDim == 2:
            newtif = feature.canny(self.tif, sigma)
        else:
            for i in range(len(newtif)):
                newtif[i] = feature.canny(self.tif[i], sigma)
                
        self.newtif = newtif.astype(np.uint8)
        self.newname = f"{self.oldname} - Canny"
        return self.end()

    
    def preview(self) -> None:
        if g.win is None or g.win.closed:
            return
            
        win = g.win
        sigma = self.getValue('sigma')
        preview = self.getValue('preview')
        nDim = len(win.image.shape)
        
        if preview:
            if nDim == 3:  # if the image is 3d
                testimage = np.copy(win.image[win.currentIndex])
            elif nDim == 2:
                testimage = np.copy(win.image)
                
            testimage = feature.canny(testimage, sigma)
            win.imageview.setImage(testimage, autoLevels=False)
            win.imageview.setLevels(-.1, 1.1)
        else:
            win.reset()
            if nDim == 3:
                image = win.image[win.currentIndex]
            else:
                image = win.image
            win.imageview.setLevels(np.min(image), np.max(image))


canny_edge_detector = Canny_edge_detector()


class Logically_combine(BaseProcess):
    """Combines two binary images with a logical operation.
    
    Parameters:
        window1: First binary image window
        window2: Second binary image window  
        operator (str): Logical operation to perform ('AND', 'OR', 'XOR')
        keepSourceWindow (bool): If True, don't close the source window
        
    Returns:
        newWindow: A new window with the combined binary image
    """
    
    
    def gui(self) -> None:
        self.gui_reset()
        window1 = WindowSelector()
        window2 = WindowSelector()
        operator = ComboBox()
        operator.addItem('AND')
        operator.addItem('OR')
        operator.addItem('XOR')
        
        self.items.append({'name': 'window1', 'string': 'Window 1', 'object': window1})
        self.items.append({'name': 'window2', 'string': 'Window 2', 'object': window2})
        self.items.append({'name': 'operator', 'string': 'Operator', 'object': operator})
        
        super().gui()
        
    
    def __call__(
        self, 
        window1: flika.window.Window, 
        window2: flika.window.Window, 
        operator: str, 
        keepSourceWindow: bool = False
    ) -> flika.window.Window | None:
        self.keepSourceWindow = keepSourceWindow
        g.m.statusBar().showMessage(f'Performing {self.__name__}...')
        
        if window1 is None or window2 is None:
            raise MissingWindowError(f"You cannot execute '{self.__name__}' without selecting a window first.")
            
        if window1.image.shape != window2.image.shape:
            g.m.statusBar().showMessage('The two windows have images of different shapes. They could not be combined')
            return None
            
        if operator == 'AND':
            self.newtif = np.logical_and(window1.image, window2.image)
        elif operator == 'OR':
            self.newtif = np.logical_or(window1.image, window2.image)
        elif operator == 'XOR':
            self.newtif = np.logical_xor(window1.image, window2.image)
            
        self.oldwindow = window1
        self.oldname = window1.name
        self.newname = f"{self.oldname} - Logical {operator}"
        
        if not keepSourceWindow:
            window2.close()
            
        g.m.statusBar().showMessage(f'Finished with {self.__name__}.')
        return self.end()


logically_combine = Logically_combine()


class Remove_small_blobs(BaseProcess):
    """Removes small connected regions from binary images.
    
    Parameters:
        rank (int): Number of dimensions to consider for connectivity (2 or 3)
        value (int): Minimum size (in pixels) for a region to be kept
        keepSourceWindow (bool): If True, don't close the source window
        
    Returns:
        newWindow: A new window with small regions removed
    """
    
    
    def gui(self) -> None:
        self.gui_reset()
        rank = QtWidgets.QSpinBox()
        rank.setRange(2, 3)
        
        value = QtWidgets.QSpinBox()
        value.setRange(1, 100000)
        
        self.items.append({'name': 'rank', 'string': 'Number of Dimensions', 'object': rank})
        self.items.append({'name': 'value', 'string': 'Value', 'object': value})
        
        super().gui()

    
    def __call__(
        self, 
        rank: int, 
        value: int, 
        keepSourceWindow: bool = False
    ) -> flika.window.Window | None:
        self.start(keepSourceWindow)
        
        if self.tif.dtype == np.float16:
            g.alert("remove_small_blobs() does not support float16 type arrays")
            return None
            
        oldshape = self.tif.shape
        newtif = np.zeros_like(self.tif, dtype=bool)
        
        if self.oldwindow.nDims == 2:
            newtif = remove_small_objects(self.tif.astype(bool), value, connectivity=2)
        elif self.oldwindow.nDims == 3:
            if rank == 2:
                for i in range(len(self.tif)):
                    newtif[i] = remove_small_objects(self.tif[i].astype(bool), value, connectivity=2)
            elif rank == 3:
                newtif = remove_small_objects(self.tif.astype(bool), value, connectivity=2)
                
        self.newtif = newtif
        self.newname = f"{self.oldname} - Removed Blobs {value}"
        return self.end()

    
    def get_init_settings_dict(self) -> dict[str, int]:
        s = {}
        s['rank'] = 2
        s['value'] = 1
        return s


remove_small_blobs = Remove_small_blobs()


class Binary_Dilation(BaseProcess):
    """Performs binary dilation on a binary image to expand regions.
    
    Parameters:
        rank (int): Number of dimensions to consider (2 or 3)
        connectivity (int): Connectivity pattern (1 to rank)  
        iterations (int): Number of times to repeat the dilation
        keepSourceWindow (bool): If True, don't close the source window
        
    Returns:
        newWindow: A new window with the dilated binary image
    """
    
    
    def gui(self) -> None:
        self.gui_reset()
        rank = QtWidgets.QSpinBox()
        rank.setRange(2, 3)
        
        connectivity = QtWidgets.QSpinBox()
        connectivity.setRange(1, 3)
        
        iterations = QtWidgets.QSpinBox()
        iterations.setRange(1, 100)
        
        self.items.append({'name': 'rank', 'string': 'Number of Dimensions', 'object': rank})
        self.items.append({'name': 'connectivity', 'string': 'Connectivity', 'object': connectivity})
        self.items.append({'name': 'iterations', 'string': 'Iterations', 'object': iterations})

        super().gui()
        
    
    def __call__(
        self,
        rank: int,
        connectivity: int,
        iterations: int,
        keepSourceWindow: bool = False
    ) -> flika.window.Window | None:
        self.start(keepSourceWindow)
        
        if self.tif.dtype == np.float16:
            g.alert("binary_dilation does not support float16 type arrays")
            return None
            
        if len(self.tif.shape) == 3 and rank == 2:
            s = scipy.ndimage.generate_binary_structure(3, connectivity)
            s[0] = False
            s[2] = False
        else:
            s = scipy.ndimage.generate_binary_structure(rank, connectivity)
            
        self.newtif = scipy.ndimage.binary_dilation(self.tif, s, iterations)
        self.newtif = self.newtif.astype(np.uint8)
        self.newname = f"{self.oldname} - Dilated"
        return self.end()


binary_dilation = Binary_Dilation()


class Binary_Erosion(BaseProcess):
    """Performs binary erosion on a binary image to shrink regions.
    
    Parameters:
        rank (int): Number of dimensions to consider (2 or 3)
        connectivity (int): Connectivity pattern (1 to rank)
        iterations (int): Number of times to repeat the erosion
        keepSourceWindow (bool): If True, don't close the source window
        
    Returns:
        newWindow: A new window with the eroded binary image
    """
    
    
    def gui(self) -> None:
        self.gui_reset()
        rank = QtWidgets.QSpinBox()
        rank.setRange(2, 3)
        
        connectivity = QtWidgets.QSpinBox()
        connectivity.setRange(1, 3)
        
        iterations = QtWidgets.QSpinBox()
        iterations.setRange(1, 100)
        
        self.items.append({'name': 'rank', 'string': 'Number of Dimensions', 'object': rank})
        self.items.append({'name': 'connectivity', 'string': 'Connectivity', 'object': connectivity})
        self.items.append({'name': 'iterations', 'string': 'Iterations', 'object': iterations})

        super().gui()
        
    
    def __call__(
        self, 
        rank: int, 
        connectivity: int, 
        iterations: int, 
        keepSourceWindow: bool = False
    ) -> flika.window.Window | None:
        self.start(keepSourceWindow)
        
        if self.tif.dtype == np.float16:
            g.alert("Binary Erosion does not work on float16 images. Change the data type to use this function.")
            return None
            
        if len(self.tif.shape) == 3 and rank == 2:
            s = scipy.ndimage.generate_binary_structure(3, connectivity)
            s[0] = False
            s[2] = False
        else:
            s = scipy.ndimage.generate_binary_structure(rank, connectivity)
            
        self.newtif = scipy.ndimage.binary_erosion(self.tif, s, iterations)
        self.newtif = self.newtif.astype(np.uint8)
        self.newname = f"{self.oldname} - Eroded"
        return self.end()


binary_erosion = Binary_Erosion()


class Generate_ROIs(BaseProcess):
    """Generates Region of Interest (ROI) objects from binary image clusters.
    
    Parameters:
        level (float): Contour level for finding boundaries (0-1)
        minDensity (int): Minimum pixel count for a region to be considered
        keepSourceWindow (bool): If True, don't close the source window
        
    Returns:
        newWindow: A new window with the generated ROIs
    """
    
    def __init__(self):
        super().__init__()
        self.ROIs: list = []

    
    def gui(self) -> None:
        self.gui_reset()
        level = SliderLabel(2)
        level.setRange(0, 1)
        level.setValue(.5)
        
        minDensity = QtWidgets.QSpinBox()
        minDensity.setRange(4, 1000)
        
        preview = CheckBox()
        preview.setChecked(True)
        
        self.items.append({'name': 'level', 'string': 'Contour Level', 'object': level})
        self.items.append({'name': 'minDensity', 'string': 'Minimum Density', 'object': minDensity})
        self.items.append({'name': 'preview', 'string': 'Preview', 'object': preview})
        
        self.ROIs = []
        super().gui()
        self.ui.rejected.connect(self.removeROIs)

    
    def removeROIs(self) -> None:
        for roi in self.ROIs:
            roi.cancel()
        self.ROIs = []

    
    def __call__(
        self, 
        level: float, 
        minDensity: int, 
        keepSourceWindow: bool = False
    ) -> flika.window.Window | None:
        self.start(keepSourceWindow)
        
        if self.tif.dtype == np.float16:
            g.alert("generate_rois does not support float16 type arrays")
            return None
            
        if not np.all((self.tif == 0) | (self.tif == 1)):
            g.alert("The current image is not a binary image. Threshold first")
            return None
            
        for roi in self.ROIs:
            roi.cancel()
        self.ROIs = []

        im = g.win.image if g.win.image.ndim == 2 else g.win.image[g.win.currentIndex]
        im = scipy.ndimage.binary_closing(im)
        thresholded_image = np.squeeze(im)
        labelled = measure.label(thresholded_image)
        ROIs = []
        
        for i in range(1, np.max(labelled) + 1):
            if np.sum(labelled == i) >= minDensity:
                im = scipy.ndimage.binary_dilation(scipy.ndimage.binary_closing(labelled == i))
                outline_coords = measure.find_contours(im, level)
                if len(outline_coords) == 0:
                    continue
                outline_coords = outline_coords[0]
                new_roi = makeROI("freehand", outline_coords)
                ROIs.append(new_roi)
        
        self.newtif = self.tif.copy()
        self.newname = f"{self.oldname} - ROIs Generated"
        return self.end()

    
    def preview(self) -> None:
        if g.win is None or g.win.closed:
            return
            
        win = g.win
        im = win.image if win.image.ndim == 2 else win.image[win.currentIndex]
        
        if not np.all((im == 0) | (im == 1)):
            g.alert("The current image is not a binary image. Threshold first")
            return None
            
        im = scipy.ndimage.binary_closing(im)
        level = self.getValue('level')
        minDensity = self.getValue('minDensity')
        thresholded_image = np.squeeze(im)
        labelled = measure.label(thresholded_image)
        
        for roi in self.ROIs:
            roi.cancel()
        self.ROIs = []

        for i in range(1, np.max(labelled) + 1):
            QtWidgets.QApplication.processEvents()
            if np.sum(labelled == i) >= minDensity:
                im = scipy.ndimage.binary_dilation(scipy.ndimage.binary_closing(labelled == i))
                outline_coords = measure.find_contours(im, level)
                if len(outline_coords) == 0:
                    continue
                outline_coords = outline_coords[0]
                self.ROIs.append(ROI_Drawing(win, outline_coords[0][0], outline_coords[0][1], 'freehand'))
                for p in outline_coords[1:]:
                    self.ROIs[-1].extend(p[0], p[1])
                    QtWidgets.QApplication.processEvents()


generate_rois = Generate_ROIs()













    
    
    