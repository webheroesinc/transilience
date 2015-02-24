
import sys, os, time
import subprocess, signal
import requests

from mongrel2		import handler
from utils.discovery	import get_docker_ip

def websocket_send(msg):
    return handler.websocket_response(msg)

def test_api_running():
    mg2_ip	= get_docker_ip('mg2')
    url		= 'http://{0}/api/ping?text=b5b44d95-2e33-4af9-95fe-1cade9cd86ef'.format(mg2_ip)
    req		= requests.get(url, timeout=4)
    assert req.text == "b5b44d95-2e33-4af9-95fe-1cade9cd86ef"

def test_api_running():
    mg2_ip	= get_docker_ip('mg2')
    url		= 'http://{0}/api/ping?text=b5b44d95-2e33-4af9-95fe-1cade9cd86ef'.format(mg2_ip)
    req		= requests.get(url, timeout=4)
    assert req.text == "b5b44d95-2e33-4af9-95fe-1cade9cd86ef"

