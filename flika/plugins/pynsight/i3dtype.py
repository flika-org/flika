# -*- coding: utf-8 -*-
"""
This file was copied from https://github.com/ZhuangLab/storm-analysis/blob/master/sa_library/i3dtype.py
Originally written by Hazen Babcock (https://github.com/HazenBabcock)
"""

import numpy as np


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


def createDefaultI3Data(size):
    data = np.zeros(size, dtype = i3DataType())
    defaults = [['x',   1.0],
                ['y',   1.0],
                ['xc',  1.0],
                ['yc',  1.0],
                ['h',   100.0],
                ['a',   10000.0],
                ['w',   300.0],
                ['phi', 0.0],
                ['ax',  1.0],
                ['bg',  0.0],
                ['i',   10000.0],
                ['c',   1],
                ['fi',  1],
                ['fr',  1],
                ['tl',  1],
                ['lk', -1],
                ['z',   0.0],
                ['zc',  0.0]]

    for elt in defaults:
        setI3Field(data, elt[0], elt[1])
    return data


def getI3DataTypeSize():
    data = np.zeros(1, dtype = i3DataType())
    return len(data.dtype.names)


def maskData(i3data, mask):
    """Creates a new i3 data structure containing only those elements where mask is True."""
    new_i3data = np.zeros(mask.sum(), dtype = i3DataType())
    for field in i3data.dtype.names:
        new_i3data[field] = i3data[field][mask]
    return new_i3data


def posSet(i3data, field, value):
    """ Convenience function for setting both a position and it's corresponding drift corrected value. """
    setI3Field(i3data, field, value)
    setI3Field(i3data, field + 'c', value)


def setI3Field(i3data, field, value):
    if field in i3data.dtype.names:
        data_type = i3data.dtype.fields[field][0]
        if type(value) == type(np.array([])):
            i3data[field] = value.astype(data_type)
        else:
            i3data[field] = value * np.ones(i3data[field].size, dtype = data_type)

    
if __name__ == "__main__":
    if 0:
        data = createDefaultI3Data(10)
        print(data['x'])

        test = data.dtype.fields
        for name in data.dtype.names:
            print(name, test[name], test[name][0])

    if 1:
        print(getI3DataTypeSize())


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
