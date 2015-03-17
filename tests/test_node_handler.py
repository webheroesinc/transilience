
import sys, os, time
import subprocess, signal
import requests

from utils.discovery		import get_docker_ip
from mongrel2_transceiver	import *
from utils			import logging

import zmq
import simplejson	as json

def test_node_running():
    node_ip		= get_docker_ip('node')
    with Connector( node_ip, log_level=logging.DEBUG ) as conn:
        assert conn.ping()

def test_node_response():
    node_ip		= get_docker_ip('node')
    with Server(sender="test_node_handler", connect=[node_ip], log_level=logging.DEBUG) as server:
        client		= server.client('websocket')
        client.send('/api')
        
        resp		= client.recv()

        data		= json.loads(resp.data)
        print json.dumps(data, indent=4)
        
        assert False
