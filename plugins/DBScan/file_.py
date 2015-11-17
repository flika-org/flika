from process.file_ import open_file_gui
import global_vars as g
import numpy as np
from .window3d import Window3D
import os, time
from .dbscan_ import cluster

__all__ = ['load_scatter_gui', 'save_clusters', 'save_scatter', 'load_scatter', 'export_nearest_distances', 'export_distances']


def load_scatter_gui():
	open_file_gui(load_scatter, prompt='Import a scatter of points for clustering', filetypes='*.txt')

def save_scatter_gui():
	try:
		if len(g.m.window3D.scatterPoints) == 0:
			g.m.statusBar().showMessage('No points plotted for export')
			return
	except:
		g.m.statusBar().showMessage('Must open a scatter before exporting points')
		return
	save_file_gui(save_scatter, prompt='Save Scatter points to text file', filetypes='*.txt')

def save_scatter_gui():
	try:
		if len(cluster.clusters) == 0:
			g.m.statusBar().showMessage('No clusters found.')
			return
	except:
		g.m.statusBar().showMessage('Cluster the data first to export clusters')
		return
	save_file_gui(save_clusters, prompt='Save clustered points to text file', filetypes='*.txt')

def save_clusters(filename):
	with open(filename, 'w') as outf:
		for clust in cluster.clusters:
			for x, y, z in clust:
				outf.write('%.4f\t%4f\t%.4f\n' % (x, y, z))
			outf.write('\n')
		
def save_scatter(filename):
	g.m.statusBar().showMessage('Saving Scatter in {}'.format(os.path.basename(filename)))
	p_out=g.m.window3D.scatterPoints
	np.savetxt(filename,p_out)
	g.m.statusBar().showMessage('Successfully saved {}'.format(os.path.basename(filename)))
		
def load_scatter(filename=None):
	if filename is None and g.m.settings['filename'] is not None:
		filename=g.m.settings['filename']
	g.m.statusBar().showMessage('Loading {}'.format(os.path.basename(filename)))
	t=time.time()
	headers = [s.strip() for s in open(filename).readline().split('\t')]
	x = headers.index('Xc')
	y = headers.index('Yc')
	try:
		z = headers.index('Zc')
		data = np.loadtxt(filename, skiprows=1, usecols=(x, y, z))
	except:
		g.m.statusBar().showMessage('Could not locate Z axis, ignoring...')
		data2d = np.loadtxt(filename, skiprows=1, usecols=(x, y))
		data = np.zeros((len(data2d), 3))
		data[:,:-1] = data2d
	g.m.statusBar().showMessage('{} successfully loaded ({} s)'.format(os.path.basename(filename), time.time()-t))
	g.m.settings['filename']=filename
	commands = ["load_scatter('{}')".format(filename)]
	if not hasattr(g.m, 'window3D'):
		g.m.window3D = Window3D()
	g.m.window3D.addScatter(data)

def export_nearest_distances(filename):
	g.m.statusBar().showMessage('Saving nearest distances to %s...' % filename)
	pts = g.m.window3D.scatterPoints
	dists = []
	for i, pt in enumerate(pts):
		dist = np.min([np.linalg.norm(np.subtract(pt, pts[j])) for j in range(len(pts)) if j != i])
	np.savetxt(filename, dists, header="Nearest Distance")
	g.m.statusBar().showMessage('Nearest Distances Saved Successfully' % filename)

def export_distances(filename):
	pts = g.m.window3D.scatterPoints
	g.m.statusBar().showMessage('Saving all distances to %s...' % filename)
	with open(filename, 'w') as outf:
		outf.write('Distances\n')
		for i, pt in enumerate(pts):
			for j in range(i + 1, len(pts)):
				outf.write('%.3f\n' % np.linalg.norm(np.subtract(pt, pts[j])))
	g.m.statusBar().showMessage('All Distances Saved Successfully' % filename)