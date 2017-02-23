w = generate_random_image(100, 100)

from flika.roi import makeROI

rois = [('rectangle', [[5, 7], [20, 24]]),
            ('line', [[60, 15], [72, 33]]),
            ('freehand', [[35, 46], [60, 75], [50, 36]]),
            ('rect_line', [[10, 60], [20, 90], [25, 80]])]

import time

im2 = np.zeros_like(w.image[0])
im3 = np.zeros_like(w.image[0])

for a, b in rois:
    roi = makeROI(a, b)
    m = roi.getMask()
    m = roi.mask
    for x, y in m:
        im2[x, y] = 1

Window(im2)