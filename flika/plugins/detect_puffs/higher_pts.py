# -*- coding: utf-8 -*-
"""
Created on Mon Jan 04 15:17:57 2016

@author: Kyle Ellefsen
"""
from qtpy.QtWidgets import qApp
from process.progress_bar import ProgressBar
import numpy as np
import global_vars as g
from scipy import spatial
import time


def getMask(nt=5,nx=5,ny=5):
    mask=np.zeros((nt,nx,ny))
    center=np.array([(nt-1)/2, (nx-1)/2, (ny-1)/2]).astype(np.int)
    t0,x0,y0=center
    for t in np.arange(nt):
        for x in np.arange(nx):
            for y in np.arange(ny):
                if  ((t-t0)**2) / (t0**2) + ((x-x0)**2) / (x0**2)   +   ((y-y0)**2) / (y0**2) <= 1:
                    mask[t,x,y]=1
    return mask, center

'''

Densities=g.m.puffAnalyzer.Densities
density_thresh=g.m.puffAnalyzer.udc['density_threshold']
time_factor=g.m.puffAnalyzer.udc['time_factor']
from plugins.detect_puffs.higher_pts import *

'''


def getHigherPoints(blurred, udc):
    """"
    STRUCTURE OF HIGHER_PTS:
    ['Distance to next highest point, index of higher point, value of current point']
    """
    blur_thresh = udc['blur_thresh']
    time_factor = udc['time_factor']
    nCores = g.settings['nCores']
    idxs=np.where(blurred>blur_thresh)
    densities=blurred[idxs]
    densities_jittered=densities+np.arange(len(densities))/(2*np.float(len(densities))) #I do this so no two densities are the same, so each cluster has a peak.
    C = np.zeros(blurred.shape )
    C_idx=np.zeros(blurred.shape, dtype=np.int)
    idxs=np.vstack((idxs[0],idxs[1],idxs[2])).T
    C[idxs[:, 0], idxs[:, 1], idxs[:, 2]] = densities_jittered
    C_idx[idxs[:, 0], idxs[:,1], idxs[:,2]] = np.arange(len(idxs))
    print("Number of pixels to analyze: {}".format(len(idxs)))
    remander=np.arange(len(idxs))
    nTotal_pts = len(idxs)
    block_ends = np.linspace(0, len(remander), nCores+1, dtype=np.int)
    data_blocks = [remander[block_ends[i]:block_ends[i+1]] for i in np.arange(nCores)]
    

    if g.settings['multiprocessing']:
        # create the ProgressBar object
        args=(nTotal_pts, C, idxs, densities_jittered, C_idx, time_factor)
        progress = ProgressBar(getHigherPoint, data_blocks, args, nCores, msg='Getting Higher Points')
        if progress.results is None or any(r is None for r in progress.results):
            higher_pts=None
        else:
            higher_pts=np.sum(progress.results,0)
    else:
        args=(nTotal_pts, C, idxs, densities_jittered, C_idx, time_factor)
        remander=np.arange(len(idxs))
        higher_pts=getHigherPointSingleProcess(args,remander)
        
        
    mt,mx,my = blurred.shape
    maxDistance = np.sqrt((mt/time_factor)**2 + mx**2 + my**2)
    remander = np.argwhere(higher_pts[:,0] == 0)
    remander=remander.T[0]
    if len(remander) == 1:
        ii = remander[0]
        higher_pts[ii] = [maxDistance, ii, densities_jittered[ii]]
    elif len(remander) > 1:
        if True:
            dens2 = densities_jittered[remander]
            possible_higher_pts = np.where(densities_jittered>np.min(dens2))[0]
            dens3 = densities_jittered[possible_higher_pts]
            pos1=idxs[remander].astype(np.float)
            pos1[:,0]=pos1[:,0]/time_factor
            pos2=idxs[possible_higher_pts].astype(np.float)
            pos2[:,0]=pos2[:,0]/time_factor
            print('Constructing {}x{} distance matrix'.format(len(pos1),len(pos2)))
            D=spatial.distance_matrix(pos1,pos2)
            for i, pt in enumerate(remander):
                density=densities_jittered[pt]
                idxs2=dens3>density
                pts_of_higher_density=possible_higher_pts[idxs2]
                if len(pts_of_higher_density)==0: #this is the most dense point
                    higher_pts[pt]= [maxDistance, pt, density]
                else:
                    distances_to_pts_of_higher_density=D[i,:][idxs2]
                    higher_pt=pts_of_higher_density[np.argmin(distances_to_pts_of_higher_density)]
                    distance_to_nearest_pt_with_higher_density=np.min(distances_to_pts_of_higher_density)
                    higher_pts[pt]= [distance_to_nearest_pt_with_higher_density, higher_pt, density]
        elif False:
            idxs_time_adjusted=idxs[:].astype(np.float)
            idxs_time_adjusted[:,0]=idxs_time_adjusted[:,0]/time_factor
            while len(remander)>1:
                print(len(remander))
                dens2=densities_jittered[remander]
                density=np.min(dens2)
                current_pt=remander[np.argmin(dens2)]
                possible_higher_pts=np.where(densities_jittered>density)[0]            
                pos1=idxs_time_adjusted[current_pt]
                pos2=idxs_time_adjusted[possible_higher_pts]
                Dsq=np.sum((pos2-pos1)**2, 1)
                higher_pt=possible_higher_pts[np.argmin(Dsq)]
                d=np.sqrt(np.min(Dsq))
                higher_pts[current_pt] = [d, higher_pt, density]
                remander = remander[remander!=current_pt]
            highest_pt=remander[0]
            density=densities_jittered[highest_pt]
            higher_pts[highest_pt]=[maxDistance, highest_pt, density]
        else:
            blockFrames=200
            block_ends=np.arange(0,mt,blockFrames).astype(np.int)
            block_ends=np.append(block_ends, mt)
            times_remander=idxs[remander][:,0]
            times_remander_blocks=[np.where(np.logical_and(times_remander>block_ends[i], times_remander<=block_ends[i+1]))[0] for i in np.arange(nCores)]
            idxs_time_adjusted=idxs[:].astype(np.float)
            idxs_time_adjusted[:,0]=idxs_time_adjusted[:,0]/time_factor
            for times_remander_block in times_remander_blocks:   # times_remander_block is the 
                density_block=densities_jittered[times_remander_block]
                possible_higher_pts=np.where(densities_jittered>np.min(density_block))[0]
                
                
    return higher_pts, idxs


def getHigherPoint(q_results, q_progress, q_status, child_conn, args):
    remander=child_conn.recv() # unfortunately this step takes a long time
    percent=0  # This is the variable we send back which displays our progress
    status=q_status.get(True) #this blocks the process from running until all processes are launched
    if status=='Stop':
        q_results.put(None) # if the user presses stop, return None
    nTotal_pts, C, idxs, densities_jittered, C_idx, time_factor = args
    mt,mx,my=C.shape
    higher_pts=np.zeros((nTotal_pts,3)) #['Distance to next highest point, index of higher point, value of current point']
    nTotal=len(remander)
    nCompleted=0
    for r in np.arange(5,45,2):
        mask,center=getMask(r,r,r)
        oldremander=remander
        remander=[]
        percent=0
        for ii in oldremander:
            if not q_status.empty(): #check if the stop button has been pressed
                stop=q_status.get(False)
                q_results.put(None)
                return
            idx=idxs[ii]
            density=densities_jittered[ii]
            t,x,y=idx
            center2=np.copy(center)
            t0=t-center[0]
            tf=t+center[0]+1
            x0=x-center[1]
            xf=x+center[1]+1
            y0=y-center[2]
            yf=y+center[2]+1
            mask2=np.copy(mask)
            if t0<0:
                mask2=mask2[center2[0]-t:,:,:]
                center2[0]=t
                t0=0
            if tf>mt-1:
                mask2=mask2[:-(tf-mt+1),:,:]
                tf=mt-1
            if x0<0:
                mask2=mask2[:,center2[1]-x:,:]
                center2[1]=x
                x0=0
            if xf>mx-1:
                mask2=mask2[:,:-(xf-mx+1),:]
                xf=mx-1
            if y0<0:
                mask2=mask2[:,:,center2[2]-y:]
                center2[2]=y
                y0=0
            if yf>my-1:
                mask2=mask2[:,:,:-(yf-my+1)]
                yf=my-1
                
            positions=np.array(np.where(mask2*C[t0:tf,x0:xf,y0:yf]>density)).astype(float).T-center2
            if len(positions)==0:
                remander.append(ii)
            else:
                distances=np.sqrt((positions[:,0]/time_factor)**2+positions[:,1]**2+positions[:,2]**2)
                higher_pt=positions[np.argmin(distances)].astype(np.int)+np.array([t0,x0,y0])+center2
                higher_pt=C_idx[higher_pt[0],higher_pt[1],higher_pt[2]]
                higher_pt=[np.min(distances), higher_pt, density]
                higher_pts[ii]=higher_pt
                nCompleted+=1
            if percent<int(100*nCompleted/nTotal):
                percent=int(100*nCompleted/nTotal)
                q_progress.put(percent)
        #if percent>=99:
        #    break
    q_results.put(higher_pts)

def getHigherPointSingleProcess(args, remander):
    progressBar1 = g.m.puffAnalyzer.algorithm_gui.higherPtsProgress1
    progressBar2 = g.m.puffAnalyzer.algorithm_gui.higherPtsProgress2
    progressBar1.setValue(0)
    progressBar2.setValue(0); qApp.processEvents()
    nTotal_pts, C, idxs, densities_jittered, C_idx, time_factor=args
    mt,mx,my=C.shape
    higher_pts=np.zeros((nTotal_pts,3)) #['Distance to next highest point, index of higher point, value of current point']
    for r in np.arange(3,45,2):
        print(r)
        progressBar2.setValue(100*r/45); qApp.processEvents()
        mask,center=getMask(r,r,r)
        oldremander=remander
        remander=[]
        percent=0
        tic=time.time()
        for ii in oldremander:
            if r==3:
                if percent<int(100*ii/len(oldremander)):
                    percent=int(100*ii/len(oldremander))
                    progressBar1.setValue(percent); qApp.processEvents()
                    toc=time.time()-tic
                    tic=time.time()
                    print('Calculating Higher Points Radius {}.  {}%  {}s'.format(r,percent, toc))
            else:
                progressBar1.setValue(100); qApp.processEvents()
            idx=idxs[ii]
            density=densities_jittered[ii]
            posi=idx-center
            posf=idx+center+1
            offset=idx
            try:
                positions=np.array(np.where(mask*C[posi[0]:posf[0], posi[1]:posf[1], posi[2]:posf[2]]>density)).astype(float).T-center
            except ValueError:
                t,x,y=idx
                t0,x0,y0=posi
                tf,xf,yf=posf
                center2=np.copy(center)
                mask2=np.copy(mask)
                if t0<0:
                    mask2=mask2[center2[0]-t:,:,:]
                    center2[0]=t
                    t0=0
                if tf>mt-1:
                    mask2=mask2[:-(tf-mt+1),:,:]
                    tf=mt-1
                if x0<0:
                    mask2=mask2[:,center2[1]-x:,:]
                    center2[1]=x
                    x0=0
                if xf>mx-1:
                    mask2=mask2[:,:-(xf-mx+1),:]
                    xf=mx-1
                if y0<0:
                    mask2=mask2[:,:,center2[2]-y:]
                    center2[2]=y
                    y0=0
                if yf>my-1:
                    mask2=mask2[:,:,:-(yf-my+1)]
                    yf=my-1
                positions=np.array(np.where(mask2*C[t0:tf,x0:xf,y0:yf]>density)).astype(float).T-center2
                posi=np.array([t0,x0,y0])
                offset=posi+center2
            
            if len(positions)==0:
                remander.append(ii)
            else:
                distances=np.sqrt((positions[:,0]/time_factor)**2+positions[:,1]**2+positions[:,2]**2)
                higher_pt=positions[np.argmin(distances)].astype(np.int)+offset
                higher_pt=C_idx[higher_pt[0],higher_pt[1],higher_pt[2]]
                higher_pt=[np.min(distances), higher_pt, density]
                higher_pts[ii]=higher_pt
    progressBar2.setValue(100); qApp.processEvents()
    return higher_pts

