## detect_puffs ##
detect\_puffs is a plugin for the image processing program [Flika](http://flika-org.github.io/).  It contains a set of algorithms for detecting local calcium signals from movies.

### Tutorials ###
[How to detect subcellular Ca2+ signals using Flika](
http://htmlpreview.github.io/?https://github.com/kyleellefsen/detect_puffs/blob/master/docs/How%20to%20detect%20subcellular%20Ca2%2B%20signals%20using%20Flika.html)

### Sample Code ###
```python
from plugins.detect_puffs.threshold_cluster import threshold_cluster
from plugins.detect_puffs.puff_simulator.puff_simulator import simulate_puffs
simulate_puffs(nFrames=1000,nPuffs=20)
baseline = -5  # This is the mean pixel value in the absence of photons.
subtract(baseline)
data_window=ratio(0, 30, 'average')  # ratio(first_frame, nFrames, ratio_type). Now we are in F/F0
data_window.setName('Data Window (F/F0)')
norm_image = data_window.image - 1
norm_window = Window(norm_image)
norm_window.setName('Normalized Window')
blurred_window = gaussian_blur(2, norm_edges=True, keepSourceWindow=True)
blurred_window.setName('Blurred Window')
threshold_cluster(data_window, blurred_window, blurred_window, blur_thresh=.1)
```
