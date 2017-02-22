# -*- coding: utf-8 -*-
"""
This file was modified from https://github.com/ZhuangLab/storm-analysis/blob/master/sa_library/writeinsight3.py
Originally written by Hazen Babcock (https://github.com/HazenBabcock)

"""
import numpy as np
import struct

def i3DataType():
    return np.dtype([('x',  np.float32),   # original x location
                     ('y',  np.float32),   # original y location
                     ('xc', np.float32),   # drift corrected x location
                     ('yc', np.float32),   # drift corrected y location
                     ('h',  np.float32),   # fit height
                     ('a',  np.float32),   # fit area
                     ('w',  np.float32),   # fit width
                     ('phi',np.float32),   # fit angle (for unconstrained elliptical gaussian)
                     ('ax', np.float32),   # peak aspect ratio
                     ('bg', np.float32),   # fit background
                     ('i',  np.float32),   # sum - baseline for pixels included in the peak
                     ('c',  np.int32),     # peak category ([0..9] for STORM images)
                     ('fi', np.int32),     # fit iterations
                     ('fr', np.int32),     # frame
                     ('tl', np.int32),     # track length
                     ('lk', np.int32),     # link (id of the next molecule in the trace)
                     ('z',  np.float32),   # original z coordinate
                     ('zc', np.float32)])  # drift corrected z coordinate
                    
def _putV(fp, format, data):
    fp.write(struct.pack(format, data))
    
def getMolecules(pts,tracks):
    data = np.zeros(len(pts), dtype = i3DataType())
    for track in tracks:
        track_length = len(track)
        for i, pt in enumerate(track):
            data[pt]['fr'] = pts[pt][0]
            data[pt]['x' ] = pts[pt][3]
            data[pt]['y' ] = pts[pt][4]
            data[pt]['xc'] = pts[pt][3]
            data[pt]['yc'] = pts[pt][4]
            data[pt]['w' ] = pts[pt][5]
            data[pt]['h' ] = pts[pt][6]
            if i+1 == track_length:
                data[pt]['lk'] = -1
            else:
                data[pt]['lk'] = track[i+1]
    return data
    
    
def write_insight_bin(filename, pts, tracks):
    frames=int(np.max(pts[:,0]))
    
    fp = open(filename, "wb")
    _putV(fp, "4s", b'M425')
    _putV(fp, "i", frames)
    _putV(fp, "i", 6) # *int32 ;% identified = 2, traced = 3, tracked = 4, stormed = 6
    _putV(fp, "i", 0)
    
    molecules=getMolecules(pts,tracks)
    molecules.tofile(fp)
    nMolecules=len(pts)
    
    _putV(fp, "i", 0)
    fp.seek(12)
    _putV(fp, "i", nMolecules)
    fp.close()
    


#
# The MIT License
#
# Copyright (c) 2012 Zhuang Lab, Harvard University
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
