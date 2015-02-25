
import sys, os, netifaces

def get_docker_ip(dname=None):
    if dname is None:
        return netifaces.ifaddresses('eth0')[2][0]['addr']
    else:
        fname	= "../var/addr/{0}.ip".format(dname)
    if os.path.isfile(fname):
        with open(fname, "r") as f:
            return f.read().rstrip()
    else:
        raise Exception("No file exists at {0}".format(fname))
