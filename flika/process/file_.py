# -*- coding: utf-8 -*-
"""
Flika
@author: Kyle Ellefsen
@author: Brett Settle
@license: MIT
"""

import pyqtgraph as pg
import pyqtgraph.exporters
import time
import os.path
import numpy as np
from skimage.io import imread, imsave
from qtpy import uic, QtGui, QtCore, QtWidgets
import codecs
import shutil, subprocess
import json
import re
import nd2reader
import datetime
import json

from .. import global_vars as g
from ..app.terminal_widget import ScriptEditor
from .BaseProcess import BaseDialog
from ..window import Window
from ..utils.misc import open_file_gui, save_file_gui
from ..utils.io import tifffile

__all__ = ['save_window', 'save_points', 'export_movie_gui', 'open_file', 'open_file_from_gui', 'load_points', 'close']

########################################################################################################################
######################                  SAVING FILES                                         ###########################
########################################################################################################################



def save_window(filename=None):
    """ save_window(filename)
    Save the image in the currentWindow to a .tif file.

    Parameters:
        | filename (str) -- The image or movie will be saved here.
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
    A = g.currentWindow.image
    metadata = g.currentWindow.metadata
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
    if filename is None:
        filetypes = '*.txt'
        prompt = 'Save Points'
        filename = save_file_gui(prompt, filetypes=filetypes)
        if filename is None:
            return None
    g.m.statusBar().showMessage('Saving Points in {}'.format(os.path.basename(filename)))
    p_out = []
    p_in = g.currentWindow.scatterPoints
    for t in np.arange(len(p_in)):
        for p in p_in[t]:
            p_out.append(np.array([t, p[0], p[1]]))
    p_out = np.array(p_out)
    np.savetxt(filename, p_out)
    g.m.statusBar().showMessage('Successfully saved {}'.format(os.path.basename(filename)))
    return filename


def export_movie_gui():
    rateSpin = pg.SpinBox(value=50, bounds=[1, 1000], suffix='fps', int=True, step=1)
    rateDialog = BaseDialog([{'string': 'Framerate', 'object': rateSpin}], 'Save Movie', 'Set the framerate')
    rateDialog.accepted.connect(lambda: export_movie(rateSpin.value()))
    g.dialogs.append(rateDialog)
    rateDialog.show()


def export_movie(rate, filename=None):
    """save_movie(rate, filename)
    Saves the currentWindow video as a .mp4 movie by joining .jpg frames together

    Parameters:
        | rate (int) -- framerate
        | filename (str) -- Address to save the movie to, with .mp4

    Notes:
        | Once you've exported all of the frames you wanted, open a command line and run the following:
        |   ffmpeg -r 100 -i %03d.jpg output.mp4
        | -r: framerate
        | -i: input files.
        | %03d: The files have to be numbered 001.jpg, 002.jpg... etc.
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

    win = g.currentWindow
    A = win.image
    if len(A.shape) < 3:
        g.alert('Movie not the right shape for saving.')
        return None
    try:
        exporter = pg.exporters.ImageExporter(win.imageview.view)
    except TypeError:
        exporter = pg.exporters.ImageExporter.ImageExporter(win.imageview.view)

    nFrames = len(A)
    tmpdir = os.path.join(os.path.dirname(g.settings.config_file), 'tmp')
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


def open_file_from_gui():
    open_file(None, True)


def open_file(filename=None, from_gui=False):
    """ open_file(filename=None)
    Opens an image or movie file (.tif, .stk, .nd2) into a newWindow.

    Parameters:
        | filename (str) -- Address of file to open. If no filename is provided, the last opened file is used.
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
    append_recent_file(filename)  # make first in recent file menu
    g.m.statusBar().showMessage('Loading {}'.format(os.path.basename(filename)))
    t = time.time()
    metadata = dict()
    ext = os.path.splitext(filename)[1]
    if ext in ['.tif', '.stk', '.tiff', '.ome']:
        try:
            Tiff = tifffile.TiffFile(filename)
        except Exception as s:
            g.alert("Unable to open {}. {}".format(filename, s))
            return None
        metadata = get_metadata_tiff(Tiff)
        A = Tiff.asarray()
        Tiff.close()
        axes = [tifffile.AXES_LABELS[ax] for ax in Tiff.pages[0].axes]
        # print("Original Axes = {}".format(axes)) #sample means RBGA, plane means frame, width means X, height means Y
        if Tiff.is_rgb:
            if A.ndim == 3:  # still color image.  [X, Y, RBGA]
                A = np.transpose(A, (1, 0, 2))
            elif A.ndim == 4:  # movie in color.  [T, X, Y, RGBA]
                A = np.transpose(A, (0, 2, 1, 3))
        else:
            if A.ndim == 2:  # black and white still image [X,Y]
                A = np.transpose(A, (1, 0))
            elif A.ndim == 3:  # black and white movie [T,X,Y]
                A = np.transpose(A, (0, 2, 1))  # This keeps the x and y the same as in FIJI.
            elif A.ndim == 4:
                if axes[3] == 'sample' and A.shape[3] == 1:
                    A = np.squeeze(A)  # this gets rid of the meaningless 4th dimention in .stk files
                    A = np.transpose(A, (0, 2, 1))
    elif ext == '.nd2':
        nd2 = nd2reader.Nd2(filename)
        mt, mx, my = len(nd2), nd2.width, nd2.height
        A = np.zeros((mt, mx, my))
        percent = 0
        for frame in range(mt):
            A[frame] = nd2[frame].T
            if percent < int(100 * float(frame) / mt):
                percent = int(100 * float(frame) / mt)
                g.m.statusBar().showMessage('Loading file {}%'.format(percent))
                QtWidgets.qApp.processEvents()
        metadata = get_metadata_nd2(nd2)
    elif ext == '.py':
        ScriptEditor.importScript(filename)
        return
    else:
        msg = "Could not open.  Filetype for '{}' not recognized".format(filename)
        g.alert(msg)
        if filename in g.settings['recent_files']:
            g.settings['recent_files'].remove(filename)
        # make_recent_menu()
        return
    g.m.statusBar().showMessage('{} successfully loaded ({} s)'.format(os.path.basename(filename), time.time() - t))
    g.settings['filename'] = filename
    commands = ["open_file('{}')".format(filename)]
    newWindow = Window(A, os.path.basename(filename), filename, commands, metadata)
    return newWindow

        
def load_points(filename=None):
    if filename is not None:
        filetypes = '*.txt'
        prompt = 'Load Points'
        filename = open_file_gui(prompt, filetypes=filetypes)
        if filename is None:
            return None
    g.m.statusBar().showMessage('Loading points from {}'.format(os.path.basename(filename)))
    pts = np.loadtxt(filename)
    nCols = pts.shape[1]
    pointSize = g.settings['point_size']
    pointColor = QtGui.QColor(g.settings['point_color'])
    if nCols == 3:
        for pt in pts:
            t = int(pt[0])
            if g.currentWindow.mt == 1:
                t = 0
            g.currentWindow.scatterPoints[t].append([pt[1],pt[2], pointColor, pointSize])
        t = g.currentWindow.currentIndex
        g.currentWindow.scatterPlot.setPoints(pos=g.currentWindow.scatterPoints[t])
    elif nCols == 2:
        t = 0
        for pt in pts:
            g.currentWindow.scatterPoints[t].append([pt[0], pt[1], pointColor, pointSize])
        t = g.currentWindow.currentIndex
        g.currentWindow.scatterPlot.setPoints(pos=g.currentWindow.scatterPoints[t])
    g.m.statusBar().showMessage('Successfully loaded {}'.format(os.path.basename(filename)))

    


    
########################################################################################################################
######################                INTERNAL HELPER FUNCTIONS                              ###########################
########################################################################################################################


def append_recent_file(fname):
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


def get_metadata_nd2(nd2):
    metadata = dict()
    metadata['channels'] = nd2.channels
    metadata['date'] = nd2.date
    metadata['fields_of_view'] = nd2.fields_of_view
    metadata['frames'] = nd2.frames
    metadata['height'] = nd2.height
    metadata['width'] = nd2.width
    metadata['z_levels'] = nd2.z_levels
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
    if isinstance(obj,datetime.datetime):
        return obj.isoformat()
    else:
        json.JSONEncoder().default(obj)


def close(windows=None):
    '''
    Will close a window or a set of windows.

    Values for windows:
        | 'all' (str) -- closes all windows
        | windows (list) - closes each window in the list
        | (Window) - closes individual window
        | (None) - closes current window
    '''
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
        if g.currentWindow is not None:
            g.currentWindow.close()


########################################################################################################################
######################             OLD FUNCTIONS THAT MIGHT BE USEFUL SOMEDAY                ###########################
########################################################################################################################
"""

def save_roi_traces(filename):
    g.m.statusBar().showMessage('Saving traces to {}'.format(os.path.basename(filename)))
    to_save = [roi.getTrace() for roi in g.currentWindow.rois]
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
    A=np.average(g.currentWindow.image, 0)#.astype(g.settings['internal_data_type'])
    metadata=json.dumps(g.currentWindow.metadata)
    if len(A.shape)==3:
        A = A[g.currentWindow.currentIndex]
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