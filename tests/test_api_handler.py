
import sys, os, time
import subprocess, signal
import requests

from utils.discovery	import get_docker_ip
from utils		import Transceiver, testing

import zmq

def test_api_running():
    mg2_ip	= get_docker_ip('mg2')
    url		= 'http://{0}/api/ping?text=b5b44d95-2e33-4af9-95fe-1cade9cd86ef'.format(mg2_ip)
    req		= requests.get(url, timeout=4)
    assert req.text == "b5b44d95-2e33-4af9-95fe-1cade9cd86ef"

def test_api_req_sock_connect():
    api_ip	= get_docker_ip('api')
    conn	= testing.Request_connection( transceiver_ip=api_ip )
    conn.ping()

def test_api_new_server_connection():
    api_ip	= get_docker_ip('api')
    conn	= testing.Request_connection( transceiver_ip=api_ip )
    conn.setup()
    conn.send('/api/ping', headers={'QUERY':'text=b5b44d95-2e33-4af9-95fe-1cade9cd86ef'})
    resp	= conn.recv()
    assert resp.startswith(conn.sender)
