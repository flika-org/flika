# -*- coding: utf-8 -*-
import numpy as np
import scipy
import scipy.ndimage
import skimage
from skimage import feature, measure
from skimage.morphology import remove_small_objects
from distutils.version import StrictVersion
from qtpy import QtCore, QtGui, QtWidgets
from .. import global_vars as g
from ..utils.BaseProcess import BaseProcess, SliderLabel, WindowSelector,  MissingWindowError, CheckBox, ComboBox
from ..roi import makeROI, ROI_Drawing
if StrictVersion(skimage.__version__) >= StrictVersion('0.13.0'):
    from skimage.filters import threshold_local
else:
    from skimage.filters import threshold_adaptive as threshold_local

__all__ = ['threshold','remove_small_blobs','adaptive_threshold','logically_combine','binary_dilation','binary_erosion', 'generate_rois', 'canny_edge_detector']
     
     
def convert2uint8(tif):
    oldmin = np.min(tif)
    oldmax = np.max(tif)
    newmax = 2**8-1
    tif = ((tif-oldmin)*newmax)/(oldmax-oldmin)
    tif = tif.astype(np.uint8)
    return tif
    
class Threshold(BaseProcess):
    """threshold(value, darkBackground=False, keepSourceWindow=False)

    Creates a boolean matrix by applying a threshold
    
    Parameters:
        value (float): The threshold to be applied
        darkBackground (bool): If this is True, pixels below the threshold will be True
    Returns:
        newWindow
    """
    def __init__(self):
        super().__init__()

    def gui(self):
        self.gui_reset()
        valueSlider = SliderLabel(2)
        if g.win is not None:
            image=g.win.image
            valueSlider.setRange(np.min(image),np.max(image))
            valueSlider.setValue(np.mean(image))
        preview=CheckBox()
        preview.setChecked(True)
        self.items.append({'name': 'value','string': 'Value','object': valueSlider})
        self.items.append({'name': 'darkBackground', 'string':'Dark Background','object': CheckBox()})
        self.items.append({'name': 'preview','string': 'Preview','object': preview})
        super().gui()

    def __call__(self, value, darkBackground=False, keepSourceWindow=False):
        self.start(keepSourceWindow)
        if self.oldwindow.nDims > 3:
            g.alert("You cannot run this function on an image of dimension greater than 3. If your window has color, convert to a grayscale image before running this function")
            return None
        if darkBackground:
            newtif = self.tif < value
        else:
            newtif = self.tif > value
        self.newtif = newtif.astype(np.uint8)
        self.newname = self.oldname+' - Thresholded '+str(value)
        return self.end()

    def preview(self):
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
            if win.nDims == 3: # if the image is 3d
                testimage = np.copy(win.image[win.currentIndex])
            elif win.nDims == 2:
                testimage = np.copy(win.image)
            if darkBackground:
                testimage = testimage<value
            else:
                testimage = testimage>value
            win.imageview.setImage(testimage, autoLevels=False)
            win.imageview.setLevels(-.1,1.1)
        else:
            win.reset()
            if win.nDims == 3:
                image = win.image[win.currentIndex]
            else:
                image = win.image
            win.imageview.setLevels(np.min(image), np.max(image))
threshold = Threshold()

class BlocksizeSlider(SliderLabel):
    def __init__(self,demicals=0):
        SliderLabel.__init__(self,demicals)
    def updateSlider(self,value):
        if value%2==0:
            if value<self.slider.value():
                value-=1
            else:
                value+=1
            self.label.setValue(value)
        self.slider.setValue(int(value*10**self.decimals))
    def updateLabel(self,value):
        if value%2==0:
            value-=1
        self.label.setValue(value)
    
class Adaptive_threshold(BaseProcess):
    """adaptive_threshold(value, block_size, darkBackground=False, keepSourceWindow=False)

    Creates a boolean matrix by applying an adaptive threshold using the scikit-image threshold_local function
    
    Parameters:
        value (int): The threshold to be applied
        block_size (int): size of a pixel neighborhood that is used to calculate a threshold value for the pixel. Must be an odd number greater than 3.
        darkBackground (bool): If this is True, pixels below the threshold will be True

    Returns:
        newWindow
    """
    def __init__(self):
        super().__init__()
    def gui(self):
        self.gui_reset()
        valueSlider=SliderLabel(2)
        valueSlider.setRange(-20,20)
        valueSlider.setValue(0)
        block_size=BlocksizeSlider(0)
        if g.win is not None:
            max_block = int(max([g.win.image.shape[-1],g.win.image.shape[-2]])/2)
        else:
            max_block = 100
        block_size.setRange(3, max_block)
        preview = CheckBox(); preview.setChecked(True)
        self.items.append({'name': 'value', 'string': 'Value', 'object': valueSlider})
        self.items.append({'name': 'block_size', 'string':'Block Size', 'object':block_size})
        self.items.append({'name': 'darkBackground', 'string': 'Dark Background', 'object': CheckBox()})
        self.items.append({'name': 'preview', 'string': 'Preview', 'object': preview})
        super().gui()
        self.preview()

    def __call__(self, value, block_size, darkBackground=False, keepSourceWindow=False):
        self.start(keepSourceWindow)
        if self.tif.dtype == np.float16:
            g.alert("Local Threshold does not support float16 type arrays")
            return
        newtif = np.copy(self.tif)

        if self.oldwindow.nDims == 2:
            newtif = threshold_local(newtif, block_size, offset=value)
        elif self.oldwindow.nDims == 3:
            for i in np.arange(len(newtif)):
                newtif[i] = threshold_local(newtif[i], block_size, offset=value)
        else:
            g.alert("You cannot run this function on an image of dimension greater than 3. If your window has color, convert to a grayscale image before running this function")
            return None
        if darkBackground:
            newtif = np.logical_not(newtif)
        self.newtif = newtif.astype(np.uint8)
        self.newname = self.oldname + ' - Thresholded ' + str(value)
        return self.end()

    def preview(self):
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
            if nDim == 3: # if the image is 3d
                testimage=np.copy(win.image[win.currentIndex])
            elif nDim == 2:
                testimage=np.copy(win.image)
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
adaptive_threshold=Adaptive_threshold()


class Canny_edge_detector(BaseProcess):
    """canny_edge_detector(sigma, keepSourceWindow=False)
    
    Parameters:
        sigma (float):
    Returns:
        newWindow
    """
    def __init__(self):
        super().__init__()
    def gui(self):
        self.gui_reset()
        sigma=SliderLabel(2)
        if g.win is not None:
            sigma.setRange(0,1000)
            sigma.setValue(1)
        preview=CheckBox(); preview.setChecked(True)
        self.items.append({'name':'sigma','string':'Sigma','object':sigma})
        self.items.append({'name':'preview','string':'Preview','object':preview})
        super().gui()
        self.preview()
    def __call__(self,sigma, keepSourceWindow=False):
        self.start(keepSourceWindow)
        nDim=len(self.tif.shape) 
        newtif=np.copy(self.tif)

        if self.tif.dtype == np.float16:
            g.alert("Canny Edge Detection does not work on float32 images. Change the data type to use this function.")
            return None

        if nDim==2:
            newtif=feature.canny(self.tif,sigma)
        else:
            for i in np.arange(len(newtif)):
                newtif[i] = feature.canny(self.tif[i],sigma)
        self.newtif=newtif.astype(np.uint8)
        self.newname=self.oldname+' - Canny '
        return self.end()

    def preview(self):
        if g.win is None or g.win.closed:
            return
        win = g.win
        sigma = self.getValue('sigma')
        preview = self.getValue('preview')
        nDim = len(win.image.shape)
        if preview:
            if nDim==3: # if the image is 3d
                testimage=np.copy(win.image[win.currentIndex])
            elif nDim==2:
                testimage=np.copy(win.image)
            testimage=feature.canny(testimage,sigma)
            win.imageview.setImage(testimage,autoLevels=False)
            win.imageview.setLevels(-.1,1.1)
        else:
            win.reset()
            if nDim==3:
                image=win.image[win.currentIndex]
            else:
                image=win.image
            win.imageview.setLevels(np.min(image),np.max(image))
canny_edge_detector=Canny_edge_detector()


class Logically_combine(BaseProcess):
    """logically_combine(window1, window2,operator, keepSourceWindow=False)

    Combines two windows according to the operator
    
    Parameters:
        window1 (Window)
        window2 (Window)
        operator (str)

    Returns:
        newWindow
    """
    def __init__(self):
        super().__init__()
    def gui(self):
        self.gui_reset()
        window1=WindowSelector()
        window2=WindowSelector()
        operator=ComboBox()
        operator.addItem('AND')
        operator.addItem('OR')
        operator.addItem('XOR')
        self.items.append({'name':'window1','string':'Window 1','object':window1})
        self.items.append({'name':'window2','string':'Window 2','object':window2})
        self.items.append({'name':'operator','string':'Operator','object':operator})
        super().gui()
    def __call__(self,window1, window2,operator,keepSourceWindow=False):
        self.keepSourceWindow=keepSourceWindow
        g.m.statusBar().showMessage('Performing {}...'.format(self.__name__))
        if window1 is None or window2 is None:
            raise(MissingWindowError("You cannot execute '{}' without selecting a window first.".format(self.__name__)))
        if window1.image.shape!=window2.image.shape:
            g.m.statusBar().showMessage('The two windows have images of different shapes. They could not be combined')
            return None
        if operator=='AND':
            self.newtif=np.logical_and(window1.image,window2.image)
        elif operator=='OR':
            self.newtif=np.logical_or(window1.image,window2.image)
        elif operator=='XOR':
            self.newtif=np.logical_xor(window1.image,window2.image)
            
        self.oldwindow=window1
        self.oldname=window1.name
        self.newname=self.oldname+' - Logical {}'.format(operator)
        if keepSourceWindow is False:
            window2.close()
        g.m.statusBar().showMessage('Finished with {}.'.format(self.__name__))
        return self.end()
logically_combine=Logically_combine()

    
class Remove_small_blobs(BaseProcess):
    """remove_small_blobs(rank, value, keepSourceWindow=False)

    Finds all contiguous 'True' pixels in rank dimensions.  Removes regions which have fewer than the specified pixels.
    
    Parameters:
        rank  (int): The number of dimensions.  If rank==2, each frame is treated independently
        value (int): The size (in pixels) below which each contiguous region must be in order to be discarded.

    Returns:
        newWindow
    """
    def __init__(self):
        super().__init__()

    def gui(self):
        self.gui_reset()
        rank = QtWidgets.QSpinBox()
        rank.setRange(2,3)
        value = QtWidgets.QSpinBox()
        value.setRange(1, 100000)
        self.items.append({'name': 'rank', 'string': 'Number of Dimensions', 'object': rank})
        self.items.append({'name': 'value', 'string': 'Value', 'object': value})
        super().gui()

    def __call__(self, rank, value, keepSourceWindow=False):
        self.start(keepSourceWindow)
        if self.tif.dtype == np.float16:
            g.alert("remove_small_blobs() does not support float16 type arrays")
            return
        oldshape = self.tif.shape
        newtif = np.zeros_like(self.tif, dtype='bool')
        if self.oldwindow.nDims == 2:
            newtif = remove_small_objects(self.tif.astype('bool'), value, connectivity=2)
        elif self.oldwindow.nDims == 3:
            if rank == 2:
                for i in np.arange(len(self.tif)):
                    newtif[i] = remove_small_objects(self.tif[i].astype('bool'), value, connectivity=2)
            elif rank == 3:
                newtif = remove_small_objects(self.tif.astype('bool'), value, connectivity=2)
        self.newtif = newtif
        self.newname = self.oldname + ' - Removed Blobs ' + str(value)
        return self.end()

    def get_init_settings_dict(self):
        s = dict()
        s['rank'] = 2
        s['value'] = 1
        return s

remove_small_blobs = Remove_small_blobs()


class Binary_Dilation(BaseProcess):
    """binary_dilation(rank,connectivity,iterations, keepSourceWindow=False)

    Performs a binary dilation on a binary image.  The 'False' pixels neighboring 'True' pixels become converted to 'True' pixels.

    Parameters:
        rank (int): The number of dimensions to dilate. Can be either 2 or 3.
        connectivity (int): `connectivity` determines the distance to dilate.
             `connectivity` may range from 1 (no diagonal elements are neighbors) 
             to `rank` (all elements are neighbors).
        iterations (int): How many times to repeat the dilation
        keepSourceWindow (bool): If this is False, a new Window is created with the result. Otherwise, the currentWindow is used

    Returns:
        newWindow
    """
    def __init__(self):
        super().__init__()
    def gui(self):
        self.gui_reset()
        rank=QtWidgets.QSpinBox()
        rank.setRange(2,3)
        connectivity=QtWidgets.QSpinBox()
        connectivity.setRange(1,3)
        iterations=QtWidgets.QSpinBox()
        iterations.setRange(1,100)
        self.items.append({'name':'rank','string':'Number of Dimensions','object':rank})
        self.items.append({'name':'connectivity','string':'Connectivity','object':connectivity})
        self.items.append({'name':'iterations','string':'Iterations','object':iterations})

        super().gui()
    def __call__(self,rank,connectivity,iterations, keepSourceWindow=False):
        self.start(keepSourceWindow)
        if self.tif.dtype == np.float16:
            g.alert("Adaptive Threshold does not support float16 type arrays")
            return
        if len(self.tif.shape)==3 and rank==2:
            s=scipy.ndimage.generate_binary_structure(3,connectivity)
            s[0]=False
            s[2]=False
        else:
            s=scipy.ndimage.generate_binary_structure(rank,connectivity)
        self.newtif=scipy.ndimage.morphology.binary_dilation(self.tif,s,iterations)
        self.newtif=self.newtif.astype(np.uint8)
        self.newname=self.oldname+' - Dilated '
        return self.end()
binary_dilation=Binary_Dilation()


class Binary_Erosion(BaseProcess):
    """binary_erosion(rank,connectivity,iterations, keepSourceWindow=False)

    Performs a binary erosion on a binary image.  The 'True' pixels neighboring 'False' pixels become converted to 'False' pixels.
    
    Parameters:
        rank (int): The number of dimensions to erode. Can be either 2 or 3.
        connectivity (int): `connectivity` determines the distance to erode. `connectivity` may range from 1 (no diagonal elements are neighbors) to `rank` (all elements are neighbors).
        iterations (int): How many times to repeat the erosion
        keepSourceWindow (bool): If this is False, a new Window is created with the result. Otherwise, the currentWindow is used

    Returns:
        newWindow
    """
    def __init__(self):
        super().__init__()

    def gui(self):
        self.gui_reset()
        rank=QtWidgets.QSpinBox()
        rank.setRange(2,3)
        connectivity=QtWidgets.QSpinBox()
        connectivity.setRange(1,3)
        iterations=QtWidgets.QSpinBox()
        iterations.setRange(1,100)
        self.items.append({'name':'rank','string':'Number of Dimensions','object':rank})
        self.items.append({'name':'connectivity','string':'Connectivity','object':connectivity})
        self.items.append({'name':'iterations','string':'Iterations','object':iterations})

        super().gui()
    def __call__(self, rank, connectivity, iterations, keepSourceWindow=False):
        self.start(keepSourceWindow)
        if self.tif.dtype == np.float16:
            g.alert("Binary Erosion does not work on float32 images. Change the data type to use this function.")
            return None
        if len(self.tif.shape)==3 and rank==2:
            s = scipy.ndimage.generate_binary_structure(3, connectivity)
            s[0] = False
            s[2] = False
        else:
            s = scipy.ndimage.generate_binary_structure(rank, connectivity)
        self.newtif = scipy.ndimage.morphology.binary_erosion(self.tif, s, iterations)
        self.newtif = self.newtif.astype(np.uint8)
        self.newname = self.oldname+' - Dilated '
        return self.end()
binary_erosion=Binary_Erosion()


class Generate_ROIs(BaseProcess):
    """generate_rois(level, keepSourceWindow=False)

    Uses a binary image to create ROIs from positive clusters.
    
    Parameters:
        level (float): value in [0, 1] to use when finding contours
        keepSourceWindow (bool): If this is False, a new Window is created with the result. Otherwise, the currentWindow is used
    Returns:
        newWindow
    """
    def __init__(self):
        super().__init__()
        self.ROIs = []
    def gui(self):
        self.gui_reset()
        self.previewing = False
        self.toPreview = False
        level=SliderLabel(2)
        level.setRange(0,1)
        level.setValue(.5)
        minDensity=QtWidgets.QSpinBox()
        minDensity.setRange(4, 1000)
        self.items.append({'name':'level','string':'Contour Level','object':level})
        self.items.append({'name':'minDensity','string':'Minimum Density','object':minDensity})
        self.ROIs = []
        super().gui()
        self.ui.rejected.connect(self.removeROIs)

    def removeROIs(self):
        for roi in self.ROIs:
            roi.cancel()
        self.ROIs = []

    def __call__(self, level, minDensity, keepSourceWindow=False):
        self.start(keepSourceWindow)
        if self.tif.dtype == np.float16:
            g.alert("Adaptive Threshold does not support float16 type arrays")
            return
        for roi in self.ROIs:
            roi.cancel()
        self.ROIs = []

        im = g.win.image if g.win.image.ndim == 2 else g.win.image[g.win.currentIndex]
        im = scipy.ndimage.morphology.binary_closing(im)
        if np.any(im < 0) or np.any(im > 1):
            raise Exception("The current image is not a binary image. Threshold first")

        thresholded_image = np.squeeze(im)
        labelled=measure.label(thresholded_image)
        ROIs = []
        for i in range(1, np.max(labelled)+1):
            if np.sum(labelled == i) >= minDensity:
                im = scipy.ndimage.morphology.binary_dilation(scipy.ndimage.morphology.binary_closing(labelled == i))
                outline_coords = measure.find_contours(im, level)
                if len(outline_coords) == 0:
                    continue
                outline_coords = outline_coords[0]
                new_roi = makeROI("freehand", outline_coords)
                ROIs.append(new_roi)

    def preview(self):
        if g.win is None or g.win.closed:
            return
        win = g.win
        if self.previewing:
            self.toPreview = True
            return
        self.previewing = True
        im = win.image if win.image.ndim == 2 else win.image[win.currentIndex]
        im = scipy.ndimage.morphology.binary_closing(im)
        if np.any(im < 0) or np.any(im > 1):
            raise Exception("The current image is not a binary image. Threshold first")

        level = self.getValue('level')
        minDensity = self.getValue('minDensity')
        thresholded_image = np.squeeze(im)
        labelled=measure.label(thresholded_image)
        for roi in self.ROIs:
            roi.cancel()
        self.ROIs = []

        for i in range(1, np.max(labelled)+1):
            QtWidgets.qApp.processEvents()
            if np.sum(labelled == i) >= minDensity:
                im = scipy.ndimage.morphology.binary_dilation(scipy.ndimage.morphology.binary_closing(labelled == i))
                outline_coords = measure.find_contours(im, level)
                if len(outline_coords) == 0:
                    continue
                outline_coords = outline_coords[0]
                self.ROIs.append(ROI_Drawing(win, outline_coords[0][0], outline_coords[0][1], 'freehand'))
                for p in outline_coords[1:]:
                    self.ROIs[-1].extend(p[0], p[1])
                    QtWidgets.qApp.processEvents()

        self.previewing = False
        if self.toPreview:
            self.toPreview = False
            self.preview()

generate_rois = Generate_ROIs()













    
    
    