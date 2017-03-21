from .. import global_vars as g
from ..window import Window
import numpy as np
from ..roi import makeROI

class TestSettings():

	def test_random_roi_color(self):
		initial = g.settings['roi_color']
		g.settings['roi_color'] = 'random'
		w1 = Window(np.random.random([10, 10, 10]))
		roi1 = makeROI('rectangle', [[1, 1], [3, 3]])
		roi2 = makeROI('rectangle', [[2, 2], [3, 3]])
		assert roi1.pen.color().name() != roi2.pen.color().name(), 'Random ROI color is the same. This could be a random chance. Run repeatedly.'
		
		g.settings['roi_color'] = '#00ff00'
		roi3 = makeROI('rectangle', [[3, 3], [3, 3]])
		assert roi3.pen.color().name() == "#00ff00", 'ROI color set. all rois are same color'

		g.settings['roi_color'] = initial

	def test_multitrace(self):
		initial = g.settings['multipleTraceWindows']
		g.settings['multipleTraceWindows'] = False

		w1 = Window(np.random.random([10, 10, 10]))
		roi1 = makeROI('rectangle', [[1, 1], [3, 3]])
		roi1.plot()
		roi2 = makeROI('rectangle', [[2, 2], [3, 3]])
		roi2.plot()
		assert roi1.traceWindow == roi2.traceWindow, 'Traces not plotted together.'
		
		g.settings['multipleTraceWindows'] = True
		roi3 = makeROI('rectangle', [[3, 3], [3, 3]])
		roi3.plot()
		assert roi3.traceWindow != roi1.traceWindow, 'Multiple trace windows'

		g.settings['multipleTraceWindows'] = initial
