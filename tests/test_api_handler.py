
import sys, os, time
import subprocess, signal
import requests

from utils.discovery	import get_docker_ip
from utils.transceiver	import Transceiver, Server, Client, Connector

import zmq

server		= Server(sender="test_api_handler")

def test_api_running():
    mg2_ip		= get_docker_ip('mg2')
    url			= 'http://{0}/api/ping?text=b5b44d95-2e33-4af9-95fe-1cade9cd86ef'.format(mg2_ip)
    req			= requests.get(url, timeout=4)
    assert req.text == "b5b44d95-2e33-4af9-95fe-1cade9cd86ef"

def test_api_req_sock_connect():
    global server
    api_ip		= get_docker_ip('api')
    with Connector( api_ip, server=server ) as conn:
        assert conn.ping()

def test_api_new_server_connection():
    global server
    api_ip		= get_docker_ip('api')
    with Client( connect=api_ip, server=server ) as client:
        client.send('/api/ping', headers={'QUERY':'text=b5b44d95-2e33-4af9-95fe-1cade9cd86ef'})
        resp		= client.recv()
        assert resp.startswith(client.server.sender)
