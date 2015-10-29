
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
from window3d import Window3D
import pyqtgraph.opengl as gl

#cluster, open_scatter, save_scatter, save_clusters, export_distances, export_nearest_distances

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

	def __call__(self, epsilon, minP, minNeighbors=1):
		g.m.statusBar().showMessage('Clustering %d points...' % len(g.m.currentWindow.scatterPoints))
		scanner = DBSCAN(eps = epsilon, min_samples=minNeighbors)
		db = scanner.fit(g.m.currentWindow.scatterPoints)
		count = len(set(db.labels_)) - (1 if -1 in db.labels_ else 0)
		clusters = []
		for i in range(count):
			cl = np.array([g.m.currentWindow.scatterPoints[j] for j in np.where(db.labels_ == i)[0]])
			if len(cl) >= minP:
				clusters.append(cl)
		g.m.currentWindow.reset()
		g.m.statusBar().showMessage('%d clusters found.' % len(clusters))
		self.clusters = clusters
		self.cluster_id = 0
		self.showCluster()
		g.m.currentWindow.view.keyPressEvent = self.keyPressed

	def hideCluster(self):
		g.m.currentWindow.view.removeItem(self.cluster_mesh)
		del self.cluster_mesh

	def showCluster(self):
		g.m.statusBar().showMessage('Plotting Cluster %d of %d. Point count: %d. Press +/- to change cluster, "H" to hide Cluster' % (self.cluster_id + 1, len(self.clusters), len(self.clusters[self.cluster_id])))
		ch = ConvexHull(self.clusters[self.cluster_id])
		md = gl.MeshData(vertexes=ch.points, faces=ch.simplices)
		if hasattr(self, 'cluster_mesh'):
			self.cluster_mesh.setMeshData(meshdata=md)
		else:
			self.cluster_mesh = gl.GLMeshItem(meshdata=md, drawFaces=False, drawEdges=True, color=(0, 255, 0, 255))
			g.m.currentWindow.view.addItem(self.cluster_mesh)
		g.m.currentWindow.moveTo(np.average(self.clusters[self.cluster_id], 0))

	def keyPressed(self, e):
		if e.key() == 45:
			self.cluster_id = (self.cluster_id - 1) % len(self.clusters)
			self.showCluster()
		elif e.key() == 61:
			self.cluster_id = (self.cluster_id + 1) % len(self.clusters)
			self.showCluster()
		else:
			print(e.key())
			gl.GLViewWidget.keyPressEvent(g.m.currentWindow.view, e)
	
	def gui(self):
		epsiSpin=QDoubleSpinBox()
		minPSpin = QSpinBox()
		minNeighborsSpin = QSpinBox()
		if g.m.currentWindow is not None:
			epsiSpin.setValue(g.m.epsilonSpin.value())
			minPSpin.setValue(g.m.minPointsSpin.value())
			minNeighborsSpin.setValue(g.m.minNeighborsSpin.value())
		self.items = []
		self.items.append({'name':'epsilon','string':'Epsilon','object':epsiSpin})
		self.items.append({'name':'minP','string':'Minimum Points','object':minPSpin})
		self.items.append({'name':'minNeighbors','string':'Minimum Neighbors','object':minNeighborsSpin})
		#self.items.append({'name':'preview','string':'Preview','object':QCheckBox()})
		super().gui()

	def preview(self):
		epsilon=self.getValue('epsilon')
		minP=self.getValue('minP')
		minNeighbors=self.getValue('minNeighbors')
		preview=self.getValue('preview')
		#if preview:
		#	g.m.currentWindow.reset()
		#	#self(epsilon, minP, minNeighbors)
		#else:
		#	g.m.currentWindow.reset()
cluster = Cluster()

def save_scatter_gui():
	if g.m.currentWindow is None:
		return False
	filename=g.m.settings['filename']
	directory=os.path.dirname(filename)
	if filename is not None and directory != '':
		filename= QFileDialog.getSaveFileName(g.m, 'Save Scatter', directory, '*.txt')
	else:
		filename= QFileDialog.getSaveFileName(g.m, 'Save Scatter', '*.txt')
	filename=str(filename)
	if filename=='':
		return False
	else:
		save_scatter(filename)

def save_clusters(filename):
	global cluster
	with open(filename, 'w') as outf:
		for cluster in cluster.clusters:
			for x, y, z in cluster:
				outf.write('%.4f\t%4f\t%.4f\n' % (x, y, z))
			outf.write('\n')
		
def save_scatter(filename):
	g.m.statusBar().showMessage('Saving Scatter in {}'.format(os.path.basename(filename)))
	p_out=g.m.currentWindow.scatterPoints
	np.savetxt(filename,p_out)
	g.m.statusBar().showMessage('Successfully saved {}'.format(os.path.basename(filename)))
	
def load_scatter_gui():
	filename=g.m.settings['filename']
	if filename is not None and os.path.isfile(filename):
		filename= QFileDialog.getOpenFileName(g.m, 'Open Scatter', filename, '*.txt')
	else:
		filename= QFileDialog.getOpenFileName(g.m, 'Open Scatter', '','*.txt')
	filename=str(filename)
	if filename=='':
		return False
	else:
		load_scatter(filename)
		
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
	commands = ["open_file('{}')".format(filename)]
	if g.m.currentWindow == None:
		Window3D()
	g.m.currentWindow.addScatter(data)


def getSaveFilename(title, extensions):
	filename=g.m.settings['filename']
	if filename is not None and os.path.isfile(filename):
		filename= QFileDialog.getSaveFileName(g.m, title, filename, extensions)
	else:
		filename= QFileDialog.getSaveFileName(g.m, title, '',extensions)
	filename=str(filename)
	if filename=='':
		return False
	else:
		return filename

def export_nearest_distances(filename):
	g.m.statusBar().showMessage('Saving nearest distances to %s...' % filename)
	pts = g.m.currentWindow.scatterPoints
	dists = []
	for i, pt in enumerate(pts):
		dist = np.min([np.linalg.norm(np.subtract(pt, pts[j])) for j in range(len(pts)) if j != i])
	np.savetxt(filename, dists, header="Nearest Distance")
	g.m.statusBar().showMessage('Nearest Distances Saved Successfully' % filename)

def export_distances(filename):
	pts = g.m.currentWindow.scatterPoints
	g.m.statusBar().showMessage('Saving all distances to %s...' % filename)
	with open(filename, 'w') as outf:
		outf.write('Distances\n')
		for i, pt in enumerate(pts):
			for j in range(i + 1, len(pts)):
				outf.write('%.3f\n' % np.linalg.norm(np.subtract(pt, pts[j])))
	g.m.statusBar().showMessage('All Distances Saved Successfully' % filename)