# -*- coding: utf-8 -*-
"""
Created on Tue Apr 05 16:19:30 2016

@author: kyle
"""
from numpy import random
import numpy as np
import sys, os
from .gaussianFitting import gaussian
import matplotlib.pyplot as plt


def generate_model_particle(x_remander,y_remander, amp):
    x = np.arange(7)
    y = np.arange(7)
    xorigin = 3+x_remander
    yorigin = 3+y_remander
    sigma = 1
    model_particle=gaussian(x[:,None], y[None,:], xorigin, yorigin, sigma, amp)
    return model_particle


def addParticle(A, t, x, y, amp, mx, my):
    x_int = int(np.round(x))
    y_int = int(np.round(y))
    x_remander = x-x_int
    y_remander = y-y_int
    model_particle = generate_model_particle(x_remander,y_remander, amp)
    dx, dy = model_particle.shape
    assert dx % 2 == 1
    tt = np.array([t])
    dx = (dx-1)/2
    dy = (dy-1)/2
    yy = np.arange(y_int-dy,y_int+dy+1, dtype=np.int)
    xx = np.arange(x_int-dx,x_int+dx+1, dtype=np.int)
    if np.min(yy)<0 or np.min(xx)<0 or np.max(yy)>=my or np.max(xx)>=mx:
        return A, None
    A[np.ix_(tt,xx,yy)]=A[np.ix_(tt,xx,yy)]+model_particle
    true_pt = [t,x,y]
    return A, true_pt


def get_accuracy(true_pts, det_pts):
    """
    Frames are independent, so I can group true points and detected points by frame and search that much smaller subset
    """
    true_pos_dist_cutoff=2
    true_pts_by_frame=[]
    det_pts_by_frame = []
    max_frame=int(np.max([np.max(txy_pts[:,0]), np.max(true_pts[:,0])]))
    for frame in np.arange(max_frame+1):
        true_pts_by_frame.append(np.where(true_pts[:,0]==frame)[0])
        det_pts_by_frame.append(np.where(det_pts[:,0]==frame)[0])
    
    linked_pts=[]  #list of lists where each entry is [true_pt_idx, det_pt_idx, distance]
    false_pos=[]   #list of detected point indicies which have no corresponding true_pt entry
    false_neg=[]   #list of true point indicies which have no corresponding det_pt entry
    for frame in np.arange(max_frame+1):
        tru=true_pts_by_frame[frame]
        det=det_pts_by_frame[frame]
        D=np.zeros((len(tru),len(det)))
        for i in np.arange(len(tru)):
            for j in np.arange(len(det)):
                D[i,j]=np.sqrt(np.sum((true_pts[tru[i]][1:]-det_pts[det[j]][1:])**2))
                
        used_det=[]
        for i in np.arange(len(tru)):
            if len(det)>0 and np.min(D[i,:])<true_pos_dist_cutoff:
                j=np.argmin(D[i,:])
                linked_pts.append([tru[i],det[j],D[i,j]])
                used_det.append(j)
                D[:,j]=true_pos_dist_cutoff #this prevents double counting, even though it might not be optimal
            else:
                false_neg.append(tru[i])
        remaining_det=np.array(list(set(range(len(det))).difference(set(used_det))))
        if len(remaining_det)>0:
            false_pos.extend(det[remaining_det])
    linked_pts=np.array(linked_pts)
    return linked_pts, false_pos, false_neg


def simulate_particles(mt=500, mx=256, my=256):
    rate_of_appearance = .1  # total rate over the entire field of view
    rate_of_disappearance = .01  # for every particle
    amp = 5
    A = random.randn(mt, mx, my)
    true_pts = []
    current_particles = []
    for frame in np.arange(mt):
        print(frame)
        old_particles = current_particles
        current_particles = []
        for i, particle in enumerate(old_particles):
            if random.random() < rate_of_disappearance:
                continue  # remove the particle
            else:
                x, y = particle
                delta = 1.0  # Delta determines the "speed" of the Brownian motion.  The random variable of the position at time t, X(t), has a normal distribution whose mean is the position at time t=0 and whose variance is delta**2*t.
                dt = 1.0  # Time Step

                x += random.randn() * delta**2 * dt
                y += random.randn() * delta**2 * dt
                current_particles.append([x, y])
                A, true_pt = addParticle(A, frame, x, y, amp, mx, my)
                if true_pt is not None:
                    true_pts.append(true_pt)
        Nparticles_to_add = random.poisson(rate_of_appearance)
        for i in np.arange(Nparticles_to_add):
            x = random.random() * mx
            y = random.random() * my
            current_particles.append([x, y])
            A, true_pt = addParticle(A, frame, x, y, amp, mx, my)
            if true_pt is not None:
                true_pts.append(true_pt)
    return A, true_pts

if __name__=='__main__':


    true_pts=np.array(true_pts)
    np.savetxt(r'C:\Users\kyle\Desktop\true_points.txt',true_pts)
    I=Window(A)
    gaussian_blur(1,keepSourceWindow=True)
    threshold(2,keepSourceWindow=True)

    txy_pts=get_points(g.m.currentWindow.image)
    linked_pts, false_pos, false_neg = get_accuracy(true_pts, txy_pts)
    refined_pts=refine_pts(txy_pts,I.image)
    refined_pts_txy=np.vstack((refined_pts[:,0],refined_pts[:,3], refined_pts[:,4])).T
    linked_pts, false_pos, false_neg = get_accuracy(true_pts, refined_pts_txy)

    refined_pts_txy[:,1:]+=.5
    np.savetxt(r'C:\Users\kyle\Desktop\simulated.txt',refined_pts_txy)
    p=Points(refined_pts_txy)
    p.link_pts()
    tracks=p.tracks
    filename=r'C:\Users\kyle\Desktop\simulated.bin'
    write_insight_bin(filename, refined_pts, tracks)



    fig, ax = plt.subplots()
    bins=np.arange(0,2,.01)
    n, _, patches = ax.hist(linked_pts[:,2], bins=bins, facecolor='blue', alpha=0.3)
    sigma=.8/particle_amp
    r=bins
    P=r/sigma**2*np.exp(-(r**2/(2*sigma**2)))
    ax.plot(bins,P*26)
