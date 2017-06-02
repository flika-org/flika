# -*- coding: utf-8 -*-
import sys, time
from qtpy import QtCore, QtGui, QtWidgets
from multiprocessing import Process, Queue, cpu_count, Pipe
import os
import numpy as np

__all__ = []

tic=time.time()

class ProcessLauncher(QtCore.QThread):
    status_update=QtCore.Signal(str)
    def __init__(self,parent):
        QtCore.QThread.__init__(self)
        self.parent=parent
        self.nCores=parent.nCores
    def __del__(self):
        self.wait()
    def run(self):
        p=self.parent
        nCores=self.nCores

        for i in range(nCores):
            self.status_update.emit('Creating process {}/{}'.format(i+1,nCores))
            q_result=Queue()
            q_progress=Queue()
            q_status=Queue()
            parent_conn, child_conn=Pipe()
            p.q_results.append(q_result)
            p.q_progress.append(q_progress)
            p.q_status.append(q_status)
            p.pipes.append(parent_conn)
            p.processes.append(Process(target=p.outerfunc, args=(q_result, q_progress, q_status, child_conn, p.args )))

        started=[False for i in range(nCores)]
        for i in range(nCores):
            if p.stopPressed:
                break
            self.status_update.emit('Initializing process {}/{}'.format(i+1,nCores))
            p.processes[i].start()
            started[i]=True
        for i in range(nCores):
            if started[i]:
                if not p.stopPressed:
                    self.status_update.emit('Sending data to process {}/{}'.format(i+1,nCores))
                    tic=time.time()
                    p.pipes[i].send(p.data[i])
                    #print('Time it took to send data: {}'.format(time.time()-tic))
        for i in range(nCores):
            if started[i]:
                if not p.stopPressed:
                    self.status_update.emit('Starting process {}/{}'.format(i+1,nCores))
                    p.q_status[i].put('Start')
                else:
                    p.q_status[i].put('Stop')
            else: #if the the process was never started
                p.process_finished[i]=True
        self.status_update.emit(p.msg)
        
        

        
    
class ProgressBar(QtWidgets.QWidget):
    finished_sig=QtCore.Signal()
    def __init__(self, outerfunc, data, args, nCores, msg='Performing Operations', parent=None ):
        super(ProgressBar, self).__init__(parent)
        self.outerfunc=outerfunc
        self.data=data
        self.args=args
        self.nCores=nCores
        self.msg=msg
        
        # GUI
        self.label=QtWidgets.QLabel(msg)
        #self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.progress_bars=[]
        self.button = QtWidgets.QPushButton('Stop')
        self.button.clicked.connect(self.handleButton)
        main_layout = QtWidgets.QGridLayout()
        main_layout.addWidget(self.label,0,0)
        main_layout.addWidget(self.button, 0, 1)
        for i in range(nCores):
            bar=QtWidgets.QProgressBar()
            bar.setMinimum(1)
            bar.setMaximum(100)
            main_layout.addWidget(bar, 1+i, 0)
            self.progress_bars.append(bar)
        self.setLayout(main_layout)
        self.setWindowTitle(msg)
        self.stopPressed = False
        self.show()
        QtWidgets.qApp.processEvents()
        
        self.results=[None for i in range(nCores)]
        self.process_finished=[False for i in range(nCores)]
        self.q_results=[]
        self.q_progress=[]
        self.q_status=[]
        self.pipes=[]
        self.processes=[]
        self.processLauncher=ProcessLauncher(self)
        self.processLauncher.status_update.connect(self.status_updated)
        self.processLauncher.start()
        
        self.timer=QtCore.QTimer()
        self.timer.timeout.connect(self.check_if_finished)
        self.timer.start(50)
        
        self.loop = QtCore.QEventLoop()
        self.finished=False
        self.finished_sig.connect(self.loop.quit)
        self.finished_sig.connect(self.update_finished_status)
        self.loop.exec_() # This blocks until the "finished" signal is emitted
        
        while self.finished is False: #the exec_() loop doesn't wait for loop.quit when running in spyder for some reason.  This is the workaround
            time.sleep(.01)
            QtWidgets.qApp.processEvents()
        self.close()
        
    def check_if_finished(self):
        for i in range(len(self.q_progress)):
            if not self.q_progress[i].empty():
                while not self.q_progress[i].empty():
                    percent=self.q_progress[i].get()
                self.progress_bars[i].setValue(percent)
            if not self.q_results[i].empty():
                self.progress_bars[i].setValue(100)
                self.results[i]=self.q_results[i].get()
                self.process_finished[i]=True
                self.processes[i].join(1)
        QtWidgets.qApp.processEvents()
        if all(self.process_finished):
            if any(r is None for r in self.results):
                self.results=None
            self.timer.timeout.disconnect()
            self.finished_sig.emit()
        if self.stopPressed:
            #print('STOPPPPP')
            for i in range(self.nCores):
                self.q_status[i].put('Stop')

    def handleButton(self):
        self.stopPressed=True
    
    def status_updated(self,msg):
        self.label.setText(msg)
    def update_finished_status(self):
        self.finished=True

    def clear_memory(self):
        for child in self.children():
            child.deleteLater()
        for attr in dir(self):
            try:
                delattr(self, attr)
            except Exception:
                pass
        
    def clear_memory(self):
        for child in self.children():
            child.deleteLater()
        for attr in dir(self):
            try:
                delattr(self, attr)
            except Exception:
                pass
        
#    def closeEvent(self, event):
#        for child in self.findChildren(QtGui.QDialog):
#            if child is not widget:
#                child.deleteLater()
#                    
#        if self.closed:
#            print('This window was already closed')
#            event.accept()
#        else:
#            self.closeSignal.emit()
#            if hasattr(self,'image'):
#                del self.image
#            self.imageview.setImage(np.zeros((2,2))) #clear the memory
#            self.imageview.close()
#            del self.imageview
#            g.m.setWindowTitle("flika")
#            if g.win==self:
#                g.win=None
#            if self in g.windows:
#                g.windows.remove(self)
#            self.closed=True
#            event.accept() # let the window close
        
        
        
'''
When using the Progress Bar, you need to write two functions:
    1) An outer function that takes an object like a numpy array, breaks it into blocks, and creates the ProgressBar object.
    2) An inner function that receives the chunks, performs the processing, and returns the results.

If you are using a progress bar in a plugin, make sure to write it in its own python file, or the threads may crash. 
The first function should look something like this:  
'''
def outer_func():
    # get original data and arguments that the inner function will receive
    original_data=np.random.random((1000,200,200))
    args=(1,)
    
    #break data into blocks
    nCores = cpu_count()
    
    block_ends = np.linspace(0,len(original_data),nCores+1).astype(np.int)
    data_blocks=[original_data[block_ends[i]:block_ends[i+1]] for  i in np.arange(nCores)] # each thread will get one element of this list.
    
    # create the ProgressBar object
    progress = ProgressBar(inner_func, data_blocks, args, nCores, msg='Performing my cool inner function')
    
    # Once the ProgressBar object finishes running, the results of all the 
    # inner function's computations will be stored in progress.results in a 
    # list.  You will have to merge the list. If the user presses the Stop
    # button, the progress.results will be set to None
    if progress.results is None or any(r is None for r in progress.results):
        result=None
    else:
        result=np.concatenate(progress.results,axis=0)
    return result
'''
The inner function will actually do the heavy lifting.  
Each process will be running the inner function.  Each inner function must 
take the same 5 arguments.  
'''
def inner_func(q_results, q_progress, q_status, child_conn, args):
    data=child_conn.recv() # unfortunately this step takes a long time
    percent=0  # This is the variable we send back which displays our progress
    status=q_status.get(True) #this blocks the process from running until all processes are launched
    if status=='Stop':
        q_results.put(None) # if the user presses stop, return None
    
    
    # Here is the meat of the inner_func.
    val,=args #unpack all the variables inside the args tuple
    result=np.zeros(data.shape)
    ii,jj,kk=data.shape
    for i in np.arange(ii):
        for j in np.arange(jj):
            for k in np.arange(kk):
                result[i,j,k]=data[i,j,k]+val
            
        if not q_status.empty(): #check if the stop button has been pressed
            stop=q_status.get(False)
            q_results.put(None)
            return
        if percent<int(100*i/ii):
            percent=int(100*i/ii)
            q_progress.put(percent)
                    
    # finally, when we've finished with our calculation, we send back the result
    q_results.put(result)
    
    
    

        
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    result=outer_func()
    print(result)





