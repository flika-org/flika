# -*- coding: utf-8 -*-
from ..logger import logger
logger.debug("Started 'reading process/file_.py'")
import pyqtgraph as pg
import pyqtgraph.exporters
import time
import os.path
import sys
import numpy as np
from qtpy import uic, QtGui, QtCore, QtWidgets
import shutil, subprocess
import datetime
import json
import re
import pathlib

from .. import global_vars as g
from ..utils.BaseProcess import BaseDialog
from ..window import Window
from ..utils.misc import open_file_gui, save_file_gui
from ..utils.io import tifffile

__all__ = ['save_file', 'save_points', 'save_rois', 'save_movie_gui', 'open_file', 'open_file_from_gui', 'open_image_sequence_from_gui', 'open_points', 'close']

########################################################################################################################
######################                  SAVING FILES                                         ###########################
########################################################################################################################



def save_file(filename=None):
    """save_file(filename=None)
    Save the image in the currentWindow to a .tif file.

    Parameters:
        filename (str): The image or movie will be saved as  'filename'.tif.

    """
    if filename is None or filename is False:
        filetypes = '*.tif'
        prompt = 'Save File As Tif'
        filename = save_file_gui(prompt, filetypes=filetypes)
        if filename is None:
            return None
    if os.path.dirname(filename) == '':  # if the user didn't specify a directory
        directory = os.path.normpath(os.path.dirname(g.settings['filename']))
        filename = os.path.join(directory, filename)
    g.m.statusBar().showMessage('Saving {}'.format(os.path.basename(filename)))
    A = g.win.image
    if A.dtype == np.bool:
        A = A.astype(np.uint8)
    metadata = g.win.metadata
    try:
        metadata = json.dumps(metadata, default=JSONhandler)
    except TypeError as e:
        msg = "Error saving metadata.\n{}\nContinuing to save file".format(e)
        g.alert(msg)
    if len(A.shape) == 3:
        A = np.transpose(A, (0, 2, 1))  # This keeps the x and the y the same as in FIJI
    elif len(A.shape) == 2:
        A = np.transpose(A, (1, 0))
    tifffile.imsave(filename, A,
                    description=metadata)  # http://stackoverflow.com/questions/20529187/what-is-the-best-way-to-save-image-metadata-alongside-a-tif-with-python
    g.m.statusBar().showMessage('Successfully saved {}'.format(os.path.basename(filename)))
    return filename

def save_points(filename=None):
    """save_points(filename=None)
    Saves the points in the current window to a text file

    Parameters:
        filename (str): Address to save the points to, with .txt


    """

    if filename is None:
        filetypes = '*.txt'
        prompt = 'Save Points'
        filename = save_file_gui(prompt, filetypes=filetypes)
        if filename is None:
            return None
    g.m.statusBar().showMessage('Saving Points in {}'.format(os.path.basename(filename)))
    p_out = []
    p_in = g.win.scatterPoints
    for t in np.arange(len(p_in)):
        for p in p_in[t]:
            p_out.append(np.array([t, p[0], p[1]]))
    p_out = np.array(p_out)
    np.savetxt(filename, p_out)
    g.m.statusBar().showMessage('Successfully saved {}'.format(os.path.basename(filename)))
    return filename


def save_movie_gui():
    rateSpin = pg.SpinBox(value=50, bounds=[1, 1000], suffix='fps', int=True, step=1)
    rateDialog = BaseDialog([{'string': 'Framerate', 'object': rateSpin}], 'Save Movie', 'Set the framerate')
    rateDialog.accepted.connect(lambda: save_movie(rateSpin.value()))
    g.dialogs.append(rateDialog)
    rateDialog.show()

def save_rois( filename=None):
    g.currentWindow.save_rois(filename)


def save_movie(rate, filename=None):
    """save_movie(rate, filename)
    Saves the currentWindow video as a .mp4 movie by joining .jpg frames together

    Parameters:
        rate (int): framerate
        filename (str): Address to save the movie to, with .mp4

    Notes:
        Once you've exported all of the frames you wanted, open a command line and run the following:
        ffmpeg -r 100 -i %03d.jpg output.mp4
        -r: framerate
        -i: input files.
        %03d: The files have to be numbered 001.jpg, 002.jpg... etc.

    """


    ## Check if ffmpeg is installed
    if os.name == 'nt':  # If we are running windows
        try:
            subprocess.call(["ffmpeg"])
        except FileNotFoundError as e:
            if e.errno == os.errno.ENOENT:
                # handle file not found error.
                # I used http://ffmpeg.org/releases/ffmpeg-2.8.4.tar.bz2 originally
                g.alert("The program FFmpeg is required to export movies. \
                \n\nFor instructions on how to install, go here: http://www.wikihow.com/Install-FFmpeg-on-Windows")
                return None
            else:
                # Something else went wrong while trying to run `wget`
                raise

    filetypes = "Movies (*.mp4)"
    prompt = "Save movie to .mp4 file"
    filename = save_file_gui(prompt, filetypes=filetypes)
    if filename is None:
        return None

    win = g.win
    A = win.image
    if len(A.shape) < 3:
        g.alert('Movie not the right shape for saving.')
        return None
    try:
        exporter = pg.exporters.ImageExporter(win.imageview.view)
    except TypeError:
        exporter = pg.exporters.ImageExporter.ImageExporter(win.imageview.view)

    nFrames = len(A)
    tmpdir = os.path.join(os.path.dirname(g.settings.settings_file), 'tmp')
    if os.path.isdir(tmpdir):
        shutil.rmtree(tmpdir)
    os.mkdir(tmpdir)
    win.top_left_label.hide()
    for i in np.arange(0, nFrames):
        win.setIndex(i)
        exporter.export(os.path.join(tmpdir, '{:03}.jpg'.format(i)))
        QtWidgets.qApp.processEvents()
    win.top_left_label.show()
    olddir = os.getcwd()
    os.chdir(tmpdir)
    subprocess.call(
        ['ffmpeg', '-r', '%d' % rate, '-i', '%03d.jpg', '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2', 'output.mp4'])
    os.rename('output.mp4', filename)
    os.chdir(olddir)
    g.m.statusBar().showMessage('Successfully saved movie as {}.'.format(os.path.basename(filename)))










########################################################################################################################
######################                         OPENING FILES                                 ###########################
########################################################################################################################

def open_image_sequence_from_gui():
    open_image_sequence(None, True)

def open_file_from_gui():
    open_file(None, True)


def open_image_sequence(filename=None, from_gui=False):
    """ open_image_sequencefilename(filename=None)
    Opens an image sequence (.tif, .png) into a newWindow.

    Parameters:
        filename (str): Address of the first of a series of files that will be stitched together into a movie.
                            If no filename is provided, the last opened file is used.
    Returns:
        newWindow

    """
    if filename is None:
        if from_gui:
            filetypes = 'Image Files (*.tif *.tiff *.png);;All Files (*.*)'
            prompt = 'Open File'
            filename = open_file_gui(prompt, filetypes=filetypes)
            if filename is None:
                return None
        else:
            filename = g.settings['filename']
            if filename is None:
                g.alert('No filename selected')
                return None
    print("Filename: {}".format(filename))
    g.m.statusBar().showMessage('Loading {}'.format(os.path.basename(filename)))
    t = time.time()
    metadata = dict()

    filename = pathlib.Path(filename)
    assert filename.is_file()
    directory = filename.parents[0]
    ext = filename.suffix
    all_image_filenames = [p for p in directory.iterdir() if p.suffix == ext]

    all_images = []
    if ext in ['.tif', '.stk', '.tiff', '.ome']:
        for f in all_image_filenames:
            results = open_tiff(f, metadata)
            if results is None:
                return None
            else:
                A, metadata = results
                all_images.append(A)
        all_images = np.array(all_images)
    elif ext in ['.png']:
        pass

    append_recent_file(str(filename))  # make first in recent file menu
    g.m.statusBar().showMessage('{} successfully loaded ({} s)'.format(filename.parts[-1], time.time() - t))
    g.settings['filename'] = str(filename)
    commands = ["open_image_sequence('{}')".format(str(filename))]
    newWindow = Window(all_images, filename.parts[-1], str(filename), commands, metadata)
    return newWindow


def open_file(filename=None, from_gui=False):
    """ open_file(filename=None)
    Opens an image or movie file (.tif, .stk, .nd2) into a newWindow.

    Parameters:
        filename (str): Address of file to open. If no filename is provided, the last opened file is used.
    Returns:
        newWindow

    """
    if filename is None:
        if from_gui:
            filetypes = 'Image Files (*.tif *.stk *.tiff *.nd2);;All Files (*.*)'
            prompt = 'Open File'
            filename = open_file_gui(prompt, filetypes=filetypes)
            if filename is None:
                return None
        else:
            filename = g.settings['filename']
            if filename is None:
                g.alert('No filename selected')
                return None
    print("Filename: {}".format(filename))
    g.m.statusBar().showMessage('Loading {}'.format(os.path.basename(str(filename))))
    t = time.time()
    metadata = dict()
    ext = os.path.splitext(str(filename))[1]
    if ext in ['.tif', '.stk', '.tiff', '.ome']:
        results = open_tiff(str(filename), metadata)
        if results is None:
            return None
        else:
            A, metadata = results
    elif ext == '.nd2':
        import nd2reader
        nd2 = nd2reader.ND2Reader(str(filename))
        axes = nd2.axes
        mx = nd2.metadata['width']
        my = nd2.metadata['height']
        mt = nd2.metadata['total_images_per_channel']
        A = np.zeros((mt, mx, my))
        percent = 0
        for frame in range(mt):
            A[frame] = nd2[frame].T
            if percent < int(100 * float(frame) / mt):
                percent = int(100 * float(frame) / mt)
                g.m.statusBar().showMessage('Loading file {}%'.format(percent))
                QtWidgets.qApp.processEvents()
        metadata = nd2.metadata
    elif ext == '.py':
        from ..app.script_editor import ScriptEditor
        ScriptEditor.importScript(filename)
        return
    elif ext == '.whl':
        # first, remove trailing (1) or (2)
        newfilename = re.sub(r' \([^)]*\)', '', filename)
        try:
            os.rename(filename, newfilename)
        except FileExistsError:
            pass
        filename = newfilename
        result = subprocess.call([sys.executable, '-m', 'pip', 'install', '{}'.format(filename)])
        if result == 0:
            g.alert('Successfully installed {}'.format(filename))
        else:
            g.alert('Install of {} failed'.format(filename))
        return
    elif ext == '.jpg' or ext == '.png':
        import skimage.io
        A = skimage.io.imread(filename)
        if len(A.shape) == 3:
            perm = get_permutation_tuple(['y', 'x', 'c'], ['x', 'y', 'c'])
            A = np.transpose(A, perm)
            metadata['is_rgb'] = True

    else:
        msg = "Could not open.  Filetype for '{}' not recognized".format(filename)
        g.alert(msg)
        if filename in g.settings['recent_files']:
            g.settings['recent_files'].remove(filename)
        # make_recent_menu()
        return
        
    append_recent_file(str(filename))  # make first in recent file menu
    g.m.statusBar().showMessage('{} successfully loaded ({} s)'.format(os.path.basename(str(filename)), time.time() - t))
    g.settings['filename'] = str(filename)
    commands = ["open_file('{}')".format(filename)]
    newWindow = Window(A, os.path.basename(str(filename)), filename, commands, metadata)
    return newWindow

def open_tiff(filename, metadata):
    try:
        Tiff = tifffile.TiffFile(str(filename))
    except Exception as s:
        g.alert("Unable to open {}. {}".format(filename, s))
        return None
    metadata = get_metadata_tiff(Tiff)
    A = Tiff.asarray()
    Tiff.close()
    axes = [tifffile.AXES_LABELS[ax] for ax in Tiff.series[0].axes]
    # print("Original Axes = {}".format(Tiff.series[0].axes)) #sample means RBGA, plane means frame, width means X, height means Y
    try:
        assert len(axes) == len(A.shape)
    except AssertionError:
        msg = 'Tiff could not be loaded because the number of axes in the array does not match the number of axes found by tifffile.py\n'
        msg += "Shape of array: {}\n".format(A.shape)
        msg += "Axes found by tifffile.py: {}\n".format(axes)
        g.alert(msg)
        return None
    if set(axes) == set(['height', 'width']):  # still image in black and white.
        target_axes = ['width', 'height']
    elif set(axes) == set(['height', 'width', 'channel']):  # still image in color.
        target_axes = ['width', 'height', 'channel']
        metadata['is_rgb'] = True
    elif set(axes) == set(['height', 'width', 'sample']):  # still image in color.
        target_axes = ['width', 'height', 'sample']
        metadata['is_rgb'] = True
    elif set(axes) == set(['height', 'width', 'series']):  # movie in black and white
        target_axes = ['series', 'width', 'height']
    elif set(axes) == set(['height', 'width', 'time']):  # movie in black and white
        target_axes = ['time', 'width', 'height']
    elif set(axes) == set(['height', 'width', 'depth']):  # movie in black and white
        target_axes = ['depth', 'width', 'height']
    elif set(axes) == set(['channel', 'time', 'height', 'width']):  # movie in color
        target_axes = ['time', 'width', 'height', 'channel']
        metadata['is_rgb'] = True
    elif set(axes) == set(['sample', 'time', 'height', 'width']):  # movie in color
        target_axes = ['time', 'width', 'height', 'sample']
        metadata['is_rgb'] = True
    elif set(axes) == set(['other', 'height', 'width']):
        target_axes = ['other', 'height', 'width']
        metadata['is_rgb'] = False

    perm = get_permutation_tuple(axes, target_axes)
    A = np.transpose(A, perm)
    if target_axes[-1] in ['channel', 'sample', 'series'] and A.shape[-1] == 2:
        B = np.zeros(A.shape[:-1])
        B = np.expand_dims(B, len(B.shape))
        A = np.append(A, B, len(A.shape) - 1)  # add a column of zeros to the last dimension.
        # if A.ndim == 4 and axes[3] == 'sample' and A.shape[3] == 1:
        #    A = np.squeeze(A)  # this gets rid of the meaningless 4th dimention in .stk files
    return [A, metadata]


def open_points(filename=None):
    """open_points(filename=None)
    Opens a specified text file and displays the points from that file into the currentWindow

    Parameters:
        filename (str): Address of file to open. If no filename is provided, the last opened file is used.

    Note:
        Any existing points on a currentWindow will persist when another points file is opened and displayed

    """
    if g.win is None:
        g.alert('Points cannot be loaded if no window is selected. Open a file and click on a window.')
        return None
    if filename is None:
        filetypes = '*.txt'
        prompt = 'Load Points'
        filename = open_file_gui(prompt, filetypes=filetypes)
        if filename is None:
            return None
    g.m.statusBar().showMessage('Loading points from {}'.format(os.path.basename(filename)))
    try:
        pts = np.loadtxt(filename)
    except UnicodeDecodeError:
        g.alert('This points file contains text that cannot be read. No points loaded.')
        return None
    if len(pts) == 0:
        g.alert('This points file is empty. No points loaded.')
        return None
    nCols = pts.shape[1]
    pointSize = g.settings['point_size']
    pointColor = QtGui.QColor(g.settings['point_color'])
    if nCols == 3:
        for pt in pts:
            t = int(pt[0])
            if g.win.mt == 1:
                t = 0
            g.win.scatterPoints[t].append([pt[1],pt[2], pointColor, pointSize])
        if g.settings['show_all_points']:
            pts = []
            for t in np.arange(g.win.mt):
                pts.extend(g.win.scatterPoints[t])
            pointSizes = [pt[3] for pt in pts]
            brushes = [pg.mkBrush(*pt[2].getRgb()) for pt in pts]
            g.win.scatterPlot.setPoints(pos=pts, size=pointSizes, brush=brushes)
        else:
            t = g.win.currentIndex
            g.win.scatterPlot.setPoints(pos=g.win.scatterPoints[t])
            g.win.updateindex()
    elif nCols == 2:
        t = 0
        for pt in pts:
            g.win.scatterPoints[t].append([pt[0], pt[1], pointColor, pointSize])
        t = g.win.currentIndex
        g.win.scatterPlot.setPoints(pos=g.win.scatterPoints[t])

    g.m.statusBar().showMessage('Successfully loaded {}'.format(os.path.basename(filename)))




    
########################################################################################################################
######################                INTERNAL HELPER FUNCTIONS                              ###########################
########################################################################################################################
def get_permutation_tuple(src, dst):
    """get_permtation_tuple(src, dst)

    Parameters:
        src (list): The original ordering of the axes in the tiff.
        dst (list): The desired ordering of the axes in the tiff.

    Returns:
        result (tuple): The required permutation so the axes are ordered as desired.
    """
    result = []
    for i in dst:
        result.append(src.index(i))
    result = tuple(result)
    return result

def append_recent_file(fname):
    fname = os.path.abspath(fname)
    if fname in g.settings['recent_files']:
        g.settings['recent_files'].remove(fname)
    if os.path.exists(fname):
        g.settings['recent_files'].append(fname)
        if len(g.settings['recent_files']) > 8:
            g.settings['recent_files'] = g.settings['recent_files'][-8:]
    return fname


def get_metadata_tiff(Tiff):
    metadata = {}
    if hasattr(Tiff[0], 'is_micromanager') and Tiff[0].is_micromanager:
        imagej_tags_unpacked = {}
        if hasattr(Tiff[0],'imagej_tags'):
            imagej_tags = Tiff[0].imagej_tags
            imagej_tags['info']
            imagej_tags_unpacked = json.loads(imagej_tags['info'])
        micromanager_metadata = Tiff[0].tags['micromanager_metadata']
        metadata = {**micromanager_metadata.value, **imagej_tags_unpacked}
        if 'Frames' in metadata and metadata['Frames'] > 1:
            timestamps = [c.tags['micromanager_metadata'].value['ElapsedTime-ms'] for c in Tiff]
            metadata['timestamps'] = timestamps
            metadata['timestamp_units'] = 'ms'
        keys_to_remove = ['NextFrame', 'ImageNumber', 'Frame', 'FrameIndex']
        for key in keys_to_remove:
            metadata.pop(key)
    else:
        try:
            metadata = Tiff[0].image_description
            metadata = txt2dict(metadata)
        except AttributeError:
            metadata = dict()
    metadata['is_rgb'] = Tiff[0].is_rgb
    return metadata



def txt2dict(metadata):
    meta = dict()
    try:
        metadata = json.loads(metadata.decode('utf-8'))
        return metadata
    except ValueError:  # if the metadata isn't in JSON
        pass
    for line in metadata.splitlines():
        line = re.split('[:=]', line.decode())
        if len(line) == 1:
            meta[line[0]] = ''
        else:
            meta[line[0].lstrip().rstrip()] = line[1].lstrip().rstrip()
    return meta


def JSONhandler(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    else:
        json.JSONEncoder().default(obj)


def close(windows=None):
    """close(window=None)
    Will close a window or a set of windows.

    Parameters:
        'all' (str): closes all windows
        windows (list): closes each window in the list
        Window: closes individual window
        (None): closes current window

    """
    if isinstance(windows, str):
        if windows == 'all':
            windows = [window for window in g.windows]
            for window in windows:
                window.close()
    elif isinstance(windows,list):
        for window in windows:
            if isinstance(window,Window):
                window.close()
    elif isinstance(windows,Window):
        windows.close()
    elif windows is None:
        if g.win is not None:
            g.win.close()


########################################################################################################################
######################             OLD FUNCTIONS THAT MIGHT BE USEFUL SOMEDAY                ###########################
########################################################################################################################
"""

def save_roi_traces(filename):
    g.m.statusBar().showMessage('Saving traces to {}'.format(os.path.basename(filename)))
    to_save = [roi.getTrace() for roi in g.win.rois]
    np.savetxt(filename, np.transpose(to_save), header='\t'.join(['ROI %d' % i for i in range(len(to_save))]), fmt='%.4f', delimiter='\t', comments='')
    g.settings['filename'] = filename
    g.m.statusBar().showMessage('Successfully saved traces to {}'.format(os.path.basename(filename)))

def load_metadata(filename=None):
    '''This function loads the .txt file corresponding to a file into a dictionary
    The .txt is a file which includes database connection information'''
    meta=dict()
    if filename is None:
        filename=os.path.splitext(g.settings['filename'])[0]+'.txt'
    BOM = codecs.BOM_UTF8.decode('utf8')
    if not os.path.isfile(filename):
        g.alert("'"+filename+"' is not a file.")
        return dict()
    with codecs.open(filename, encoding='utf-8') as f:
        for line in f:
            line = line.lstrip(BOM)
            line=line.split('=')
            meta[line[0].lstrip().rstrip()]=line[1].lstrip().rstrip()
    for k in meta.keys():
        if meta[k].isdigit():
            meta[k]=int(meta[k])
        else:
            try:
                meta[k]=float(meta[k])
            except ValueError:
                pass
    return meta

def save_metadata(meta):
    filename=os.path.splitext(g.settings['filename'])[0]+'.txt'
    f=open(filename, 'w')
    text=''
    for item in meta.items():
        text+="{}={}\n".format(item[0],item[1])
    f.write(text)
    f.close()


def save_current_frame(filename):
    "" save_current_frame(filename)
    Save the current single frame image of the currentWindow to a .tif file.

    Parameters:
        | filename (str) -- Address to save the frame to.
    ""
    if os.path.dirname(filename)=='': #if the user didn't specify a directory
        directory=os.path.normpath(os.path.dirname(g.settings['filename']))
        filename=os.path.join(directory,filename)
    g.m.statusBar().showMessage('Saving {}'.format(os.path.basename(filename)))
    A=np.average(g.win.image, 0)#.astype(g.settings['internal_data_type'])
    metadata=json.dumps(g.win.metadata)
    if len(A.shape)==3:
        A = A[g.win.currentIndex]
        A=np.transpose(A,(0,2,1)) # This keeps the x and the y the same as in FIJI
    elif len(A.shape)==2:
        A=np.transpose(A,(1,0))
    tifffile.imsave(filename, A, description=metadata) #http://stackoverflow.com/questions/20529187/what-is-the-best-way-to-save-image-metadata-alongside-a-tif-with-python
    g.m.statusBar().showMessage('Successfully saved {}'.format(os.path.basename(filename)))

def make_recent_menu():
    g.m.menuRecent_Files.clear()
    if len(g.settings['recent_files']) == 0:
        no_recent = QtWidgets.QAction("No Recent Files", g.m)
        no_recent.setEnabled(False)
        g.m.menuRecent_Files.addAction(no_recent)
        return
    def openFun(f):
        return lambda: open_file(append_recent_file(f))
    for fname in g.settings['recent_files'][:10]:
        if os.path.exists(fname):
            g.m.menuRecent_Files.addAction(QtWidgets.QAction(fname, g.m, triggered=openFun(fname)))

"""

logger.debug("Completed 'reading process/file_.py'")