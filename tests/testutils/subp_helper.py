
import os, sys
import psutil

def kill_ppid(ppid, sig):
    for p in psutil.process_iter():
        if p.ppid() == ppid:
            print "Killing PID: {0}".format(p.pid)
            os.kill(p.pid, sig)
        else:
            print "Ignoring PID {0} with PPID {1}".format(p.pid, p.ppid())
            
