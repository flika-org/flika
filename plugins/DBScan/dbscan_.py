
from __future__ import (absolute_import, division,print_function, unicode_literals)
from future.builtins import (bytes, dict, int, list, object, range, str, ascii, chr, hex, input, next, oct, open, pow, round, super, filter, map, zip)

import numpy as np
import pyqtgraph as pg
import sys
import global_vars as g
from process.BaseProcess import BaseProcess, BaseDialog
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from sklearn.cluster import DBSCAN
from scipy.spatial import ConvexHull
import pyqtgraph.opengl as gl
from .file_ import *

class Cluster(BaseProcess):
	'''cluster(epsilon, minPoints, minNeighbors=1)
	This takes three values used to cluster coordinates with the Density Based Scanning algorithm
	
	Parameters:
		| epsilon (float) -- The maximum distance between neighboring points.
		| minPoints (int) -- The minimum number of points to be considered a cluster
		| minNeighbors (int) -- The minimum neighboring points to include a point in a cluster
	Returns:
		Clusters of points
	'''
	__url__='file:///'+os.path.join(os.getcwd(),'docs','_build','html','index.html')
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
		if all([p[2] == 0 for p in self.clusters[self.cluster_id]]):
			g.m.statusBar().showMessage('Cluster is 2D, attempting to draw')
			ch = ConvexHull(self.clusters[self.cluster_id][:,:-1])
			pos = self.clusters[self.cluster_id][ch.vertices]
			pos = np.vstack((pos, pos[-1]))
			item = gl.GLLinePlotItem(pos=pos, color=(0, 255, 0, 255))
			g.m.window3D.view.addItem(item)
			g.m.window3D.moveTo(np.average(self.clusters[self.cluster_id], 0))
			return
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
		if not hasattr(g.m, 'window3D'):
			g.m.statusBar().showMessage('No points file loaded.')
			return
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