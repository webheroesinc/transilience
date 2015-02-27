
import sys, os, time
import subprocess, signal
import requests

from utils.discovery	import get_docker_ip

def test_mg2_running():
    mg2_ip	= get_docker_ip('mg2')
    url		= 'http://{0}/test.txt'.format(mg2_ip)
    req		= requests.get(url, timeout=1)
    assert req.text == "server is up and running..."

