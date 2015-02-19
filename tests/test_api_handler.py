
import sys, os, time
import subprocess, signal
import requests

from testutils	import subp_helper

def get_docker_ip(dname):
    fname	= "../var/addr/{0}.ip".format(dname)
    if os.path.isfile(fname):
        with open(fname, "r") as f:
            return f.read().rstrip()
    else:
        raise Exception("No file exists at {0}".format(fname))

def test_mg2_running():
    mg2_ip	= get_docker_ip('mg2')
    url		= 'http://{0}/test.txt'.format(mg2_ip)
    r		= requests.get(url)
    assert r.text == "server is up and running..."

def test_start_api_handler():
    handler	= None
    mg2_ip	= get_docker_ip('mg2')
    try:
        handler		= subprocess.Popen("cd /host/handlers; python api_handler.py", shell=True )
        url		= 'http://{0}/api/test'.format(mg2_ip)
        r = requests.get(url, timeout=5)
        assert r.text == "I'm so happy that this worked!"
    except Exception, e:
        print e
        raise
    finally:
        if handler:
            subp_helper.kill_ppid(handler.pid, signal.SIGTERM)
            handler.terminate()
            handler.wait()
