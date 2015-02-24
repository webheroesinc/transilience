
import sys, os, time
import subprocess, signal
import requests

from mongrel2		import handler
from utils.discovery	import get_docker_ip

import zmq

def websocket_send(msg, opcode=1):
    return handler.websocket_response(msg, opcode=opcode)

def test_api_running():
    mg2_ip	= get_docker_ip('mg2')
    url		= 'http://{0}/api/ping?text=b5b44d95-2e33-4af9-95fe-1cade9cd86ef'.format(mg2_ip)
    req		= requests.get(url, timeout=4)
    assert req.text == "b5b44d95-2e33-4af9-95fe-1cade9cd86ef"

def test_api_websocket_handling():
    
    """
    GET /chat HTTP/1.1
    Host: server.example.com
    Upgrade: websocket
    Connection: Upgrade
    Sec-WebSocket-Key: x3JJHMbDL1EzLkh9GBhXDw==
    Sec-WebSocket-Version: 13
    Origin: http://example.com
    """
    mg2_ip	= get_docker_ip('mg2')
    url		= 'http://{0}/api'.format(mg2_ip)
    resp	= requests.get(url, timeout=4, headers={
        'Upgrade':			'websocket',
        'Connection':			'Upgrade',
        'Sec-WebSocket-Key':		'x3JJHMbDL1EzLkh9GBhXDw==',
        'Sec-WebSocket-Version':	'13',
    })
    assert resp.headers.get('sec-websocket-accept') == 'HSmrc0sMlYUkAGmm5OPpG2HaGWk='

    print resp.request
    print dir(resp.request)
    assert False
