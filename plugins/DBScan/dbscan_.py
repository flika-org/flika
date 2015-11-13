
from __future__ import (absolute_import, division,print_function, unicode_literals)
from future.builtins import (bytes, dict, int, list, object, range, str, ascii, chr, hex, input, next, oct, open, pow, round, super, filter, map, zip)

import numpy as np
import pyqtgraph as pg
import sys, os, time
import global_vars as g
from process.BaseProcess import BaseProcess, BaseDialog
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from sklearn.cluster import DBSCAN
from scipy.spatial import ConvexHull
from .window3d import Window3D
import pyqtgraph.opengl as gl
from process.file_ import open_file_gui

#cluster, open_scatter, save_scatter, save_clusters, export_distances, export_nearest_distances
__all__ = ['load_scatter_gui', 'save_scatter', 'save_clusters', 'load_scatter', 'export_distances', 'export_nearest_distances']

class Cluster(BaseProcess):
	'''cluster(epsilon, minPoints, minNeighbors=1)
	This takes three values used to cluster coordinates with the Density Based Scanning algorithm
	
	Parameters:
		| epsilon (float) -- The maximum distance between neighboring points.
		| minPoints (int) -- The minimum number of points to be considered a cluster
		| minNeighbors (int) -- The minimum neighboring points to include a point in a cluster
	Returns:
		List of lists of clustered points
	'''
	__name__ = "Density Based Scan Cluster Algorithm"
	def __init__(self):
		pass

	def __call__(self, epsilon, minP, minNeighbors=1, keepSourceWindow=False):
		g.m.statusBar().showMessage('Clustering %d points...' % len(g.m.window3D.scatterPoints))
		scanner = DBSCAN(eps = epsilon, min_samples=minNeighbors)
		db = scanner.fit(g.m.window3D.scatterPoints)
		count = len(set(db.labels_)) - (1 if -1 in db.labels_ else 0)
		clusters = []
		for i in range(count):
			cl = np.array([g.m.window3D.scatterPoints[j] for j in np.where(db.labels_ == i)[0]])
			if len(cl) >= minP:
				clusters.append(cl)
		g.m.window3D.reset()
		g.m.statusBar().showMessage('%d clusters found.' % len(clusters))
		self.clusters = clusters
		self.cluster_id = 0
		self.showCluster()
		g.m.window3D.view.keyPressEvent = self.keyPressed

	def hideCluster(self):
		g.m.window3D.view.removeItem(self.cluster_mesh)
		del self.cluster_mesh

	def showCluster(self):
		g.m.statusBar().showMessage('Plotting Cluster %d of %d. Point count: %d. Press +/- to change cluster, "H" to hide Cluster' % (self.cluster_id + 1, len(self.clusters), len(self.clusters[self.cluster_id])))
		ch = ConvexHull(self.clusters[self.cluster_id])
		md = gl.MeshData(vertexes=ch.points, faces=ch.simplices)
		if hasattr(self, 'cluster_mesh'):
			self.cluster_mesh.setMeshData(meshdata=md)
		else:
			self.cluster_mesh = gl.GLMeshItem(meshdata=md, drawFaces=False, drawEdges=True, color=(0, 255, 0, 255))
			g.m.window3D.view.addItem(self.cluster_mesh)
		g.m.window3D.moveTo(np.average(self.clusters[self.cluster_id], 0))

	def keyPressed(self, e):
		if e.key() == 45:
			self.cluster_id = (self.cluster_id - 1) % len(self.clusters)
			self.showCluster()
		elif e.key() == 61:
			self.cluster_id = (self.cluster_id + 1) % len(self.clusters)
			self.showCluster()
		else:
			print(e.key())
			gl.GLViewWidget.keyPressEvent(g.m.window3D.view, e)
	
	def gui(self):
		epsiSpin=QDoubleSpinBox()
		minPSpin = QSpinBox()
		minNeighborsSpin = QSpinBox()
		if g.m.window3D is not None:
			epsiSpin.setValue(5)
			minPSpin.setValue(5)
			minNeighborsSpin.setValue(2)
		self.items = []
		self.items.append({'name':'epsilon','string':'Epsilon','object':epsiSpin})
		self.items.append({'name':'minP','string':'Minimum Points in Cluster','object':minPSpin})
		self.items.append({'name':'minNeighbors','string':'Minimum Neighbors per Point','object':minNeighborsSpin})
		old_window = g.m.currentWindow
		g.m.currentWindow = g.m.window3D
		super().gui()
		g.m.currentWindow = old_window
cluster = Cluster()

def cluster_gui():
	cluster.gui()

def load_scatter_gui():
	open_file_gui(load_scatter, prompt='Import a scatter of points for clustering', filetypes='*.txt')

def save_clusters(filename):
	global cluster
	with open(filename, 'w') as outf:
		for cluster in cluster.clusters:
			for x, y, z in cluster:
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
	z = headers.index('Zc')
	data = np.loadtxt(filename, skiprows=1, usecols=(x, y, z))
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