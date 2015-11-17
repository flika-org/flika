from collections import OrderedDict
dependencies = ['sklearn', 'PyOpenGL']

menu_layout = {'Density Based Scan': OrderedDict([('Load Scatter', ['file_', 'load_scatter_gui']), ('Cluster Points', ['dbscan_', 'cluster.gui']), ('Save Clusters', ['file_', 'save_scatter_gui'])])}