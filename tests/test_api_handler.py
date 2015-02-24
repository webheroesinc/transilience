
import sys, os, time
import subprocess, signal
import requests

# from mongrel2		import handler
from utils.discovery	import get_docker_ip
from utils		import Transceiver

import zmq

# def websocket_send(msg, opcode=1):
#     return handler.websocket_response(msg, opcode=opcode)

def test_api_running():
    mg2_ip	= get_docker_ip('mg2')
    url		= 'http://{0}/api/ping?text=b5b44d95-2e33-4af9-95fe-1cade9cd86ef'.format(mg2_ip)
    req		= requests.get(url, timeout=4)
    assert req.text == "b5b44d95-2e33-4af9-95fe-1cade9cd86ef"

def test_api_req_sock_connect():
    api_ip	= get_docker_ip('api')
    CTX		= zmq.Context()
    
    req_sock	= CTX.socket(zmq.REQ)
    req_sock.connect('tcp://{0}:{1}'.format(api_ip, Transceiver.REP_PORT))
    req_sock.send('CONNECT')
    
    poller	= zmq.Poller()
    poller.register(req_sock, zmq.POLLIN)
    
    socks	= dict(poller.poll(1000))
    if req_sock in socks and socks[req_sock] == zmq.POLLIN:
        resp	= req_sock.recv()
        assert resp == "ACCEPT"
    else:
        assert False
