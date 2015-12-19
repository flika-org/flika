import sys, time
from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import QThread
from PyQt4.QtCore import pyqtSignal as Signal
from multiprocessing import Process, Queue, cpu_count, Pipe
import os


tic=time.time()

class ProcessLauncher(QThread):
    status_update=Signal(str)
    def __init__(self,parent):
        QThread.__init__(self)
        self.parent=parent
        self.nThreads=parent.nThreads
    def __del__(self):
        self.wait()
    def run(self):
        p=self.parent
        nThreads=self.nThreads

        for i in range(nThreads):
            self.status_update.emit('Creating process {}/{}'.format(i+1,nThreads))
            q_result=Queue()
            q_progress=Queue()
            q_status=Queue()
            parent_conn, child_conn=Pipe()
            p.q_results.append(q_result)
            p.q_progress.append(q_progress)
            p.q_status.append(q_status)
            p.pipes.append(parent_conn)
            p.processes.append(Process(target=p.outerfunc, args=(q_result, q_progress, q_status, child_conn, p.args )))

        started=[False for i in range(nThreads)]
        for i in range(nThreads):
            if p.stopPressed:
                break
            self.status_update.emit('Initializing process {}/{}'.format(i+1,nThreads))
            p.processes[i].start()
            started[i]=True
        for i in range(nThreads):
            if started[i]:
                if not p.stopPressed:
                    self.status_update.emit('Sending data to process {}/{}'.format(i+1,nThreads))
                    tic=time.time()
                    p.pipes[i].send(p.data[i])
                    print('Time it took to send data: {}'.format(time.time()-tic))
        for i in range(nThreads):
            if started[i]:
                if not p.stopPressed:
                    self.status_update.emit('Starting process {}/{}'.format(i+1,nThreads))
                    p.q_status[i].put('Start')
                else:
                    p.q_status[i].put('Stop')
            else: #if the the process was never started
                p.process_finished[i]=True
        self.status_update.emit(p.msg)
        
        

        
    
class ProgressBar(QtGui.QWidget):
    finished_sig=Signal()
    def __init__(self, outerfunc, data, args, nThreads, msg='Performing Operations', parent=None ):
        super(ProgressBar, self).__init__(parent)
        self.outerfunc=outerfunc
        self.data=data
        self.args=args
        self.nThreads=nThreads
        self.msg=msg
        
        # GUI
        self.setWindowIcon(QtGui.QIcon('images/favicon.png'))
        self.label=QtGui.QLabel(msg)
        self.progress_bars=[]
        self.button = QtGui.QPushButton('Stop')
        self.button.clicked.connect(self.handleButton)
        main_layout = QtGui.QGridLayout()
        main_layout.addWidget(self.label,0,0)
        main_layout.addWidget(self.button, 0, 1)
        for i in range(nThreads):
            bar=QtGui.QProgressBar()
            bar.setMinimum(1)
            bar.setMaximum(100)
            main_layout.addWidget(bar, 1+i, 0)
            self.progress_bars.append(bar)
        self.setLayout(main_layout)
        self.setWindowTitle('Progress')
        self.stopPressed = False
        self.show()
        QtGui.qApp.processEvents()
        
        self.results=[None for i in range(nThreads)]
        self.process_finished=[False for i in range(nThreads)]
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
            QtGui.qApp.processEvents()
        self.close()
        
    def check_if_finished(self):
        for i in range(len(self.q_progress)):
            if not self.q_progress[i].empty():
                while not self.q_progress[i].empty():
                    percent=self.q_progress[i].get()
                self.progress_bars[i].setValue(percent)
            if not self.q_results[i].empty():
                self.results[i]=self.q_results[i].get()
                self.process_finished[i]=True
                self.processes[i].join()
        QtGui.qApp.processEvents()
        if all(self.process_finished):
            if any(r is None for r in self.results):
                self.results=None
            self.timer.timeout.disconnect()
            self.finished_sig.emit()
        if self.stopPressed:
            #print('STOPPPPP')
            for i in range(self.nThreads):
                self.q_status[i].put('Stop')

    def handleButton(self):
        self.stopPressed=True
    
    def status_updated(self,msg):
        self.label.setText(msg)
    def update_finished_status(self):
        self.finished=True
        





from scipy.signal import butter, filtfilt
import numpy as np    
def butterworth_filter_multi_outer(q_results, q_progress, q_status, child_conn, args):
    status=q_status.get(True) #this blocks the process from running until all processes are launched
    if status=='Stop':
        q_results.put(None)
        
    data=child_conn.recv()
    def makeButterFilter(filter_order,low,high):
        padlen=0
        if high==1: 
            if low==0: #if there is no temporal filter at all,
                return None,None,None
            else: #if only high pass temporal filter
                [b,a]= butter(filter_order,low,btype='highpass')
                padlen=3
        else:
            if low==0:
                [b,a]= butter(filter_order,high,btype='lowpass')
            else:
                [b,a]=butter(filter_order,[low,high], btype='bandpass')
            padlen=6
        return b,a,padlen
        
    filter_order,low,high = args
    b,a,padlen=makeButterFilter(filter_order,low,high)
    mt,mx,my=data.shape
    result=np.zeros(data.shape)
    nPixels=mx*my
    pixel=0
    percent=0
    for x in np.arange(mx):
        for y in np.arange(my):
            if not q_status.empty():
                stop=q_status.get(False)
                q_results.put(None)
                return
            pixel+=1
            if percent<int(100*pixel/nPixels):
                percent=int(100*pixel/nPixels)
                q_progress.put(percent)
            result[:, x, y]=filtfilt(b,a, data[:, x, y], padlen=padlen)
    q_results.put(result)
    
    
def butterworth_filter_multi(filter_order,low,high,tif):
    nThreads= 4 #cpu_count()
    mt,mx,my=tif.shape
    block_ends=np.linspace(0,mx,nThreads+1).astype(np.int)
    data=[tif[:, block_ends[i]:block_ends[i+1],:] for i in np.arange(nThreads)] #split up data along x axis. each thread will get one.
    
    args=(filter_order,low,high)
    
    progress = ProgressBar(butterworth_filter_multi_outer, data, args, nThreads, msg='Performing Butterworth Filter')
    if progress.results is None:
        result=progress.results
    else:
        result=np.concatenate(progress.results,axis=1)
    return result
        
if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    
    tif=np.random.random((1100,512,512))
    tic=time.time()
    result=butterworth_filter_multi(1,.5,.5,tif)
    del tif





