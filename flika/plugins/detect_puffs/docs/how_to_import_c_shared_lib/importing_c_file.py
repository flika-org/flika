# -*- coding: utf-8 -*-
"""
Created on Wed Dec 23 15:06:32 2015
@author: Kyle Ellefsen

This file should explain how to write and compile c programs (shared libraries) that can be imported and used from within python.
These instructions are roughly based on examples found in https://github.com/ZhuangLab/storm-analysis/tree/master/sa_library

In order to compile shared libraries, you need a compiler with matching architecture (64-bit) and that links with the standard windows header files.  I used MinGW64
- Download mingw-w64 http://sourceforge.net/projects/mingw-w64/?source=typ_redirect
- Install mingw, set architecture to x86-64 and threading to win32
- Add the installed 'bin' directory to the path.  Something like "C:\Program Files\mingw-w64\x86_64-5.3.0-win32-seh-rt_v4-rev0\mingw64\bin".  To edit the path I like this program: https://patheditor2.codeplex.com/

Now write the C program and compile using these commands
cd "path\to\get_distance.c\"
gcc -c get_distance.c
gcc -shared -o get_distance.dll get_distance.o

After loading your library, you need to specify the argument types of each c function
https://docs.python.org/2/library/ctypes.html#specifying-the-required-argument-types-function-prototypes
|---------------------------------------------------------|
|type in C                                 type in python |
|---------------------------------------------------------|
|double        c_double                                   |
|double *      np.ctypeslib.ndpointer(dtype=np.float64)   |   or POINTER(c_double)
|int           c_int                                      |   
|int *         np.ctypeslib.ndpointer(dtype=np.int64)     |   or Pointer(c_int)
|---------------------------------------------------------|
"""

import ctypes
from ctypes import *
import numpy as np
from numpy.ctypeslib import ndpointer


lib_location=r'C:\Users\Kyle Ellefsen\Desktop\get_distance.dll'
util=ctypes.cdll.LoadLibrary(lib_location)
util.getDistance.argtypes = [ndpointer(dtype=np.float64),
                                ndpointer(dtype=np.float64),
                                ndpointer(dtype=np.float64),
                                ndpointer(dtype=np.float64),
                                ndpointer(dtype=np.float64),
                                c_int]
                                
def getDistance_c(x1, y1, x2, y2):
    c_x1 = np.ascontiguousarray(x1).astype(np.float64)
    c_y1 = np.ascontiguousarray(y1).astype(np.float64)
    c_x2 = np.ascontiguousarray(x2).astype(np.float64)
    c_y2 = np.ascontiguousarray(y2).astype(np.float64)
    n_x1 = x1.size
    c_dist = np.ascontiguousarray(np.zeros(n_x1))
    util.getDistance(c_x1, c_y1, c_x2, c_y2, c_dist, n_x1)
    return c_dist

    

n=100000
x1 = np.random.rand(n)
y1 = np.random.rand(n)
x2 = np.random.rand(n)
y2 = np.random.rand(n)

dist=getDistance_c(x1,xy1,x2,y2)
print dist


#def getDistance_py(x1,y1,x2,y2):
#    return np.sqrt((x1-x2)**2+(y1-y2)**2)
#import time
#tic=time.time()
#dist = getDistance_c(x1, y1, x2, y2)
#print("C time: {}".format(time.time()-tic))
#
#tic=time.time()
#dist = getDistance_py(x1, y1, x2, y2)
#print("Python time: {}".format(time.time()-tic))

