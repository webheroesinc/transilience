
#
# Mongrel2-Transceiver -- Communication Protocol Python Parser and Originator
#
# Copyright (c) 2015, Web Heroes Inc..
#
# Mongrel2-Transceiver is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later version.  See
# the LICENSE file at the top of the source tree.
#
# Mongrel2-Transceiver is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE.  See the GNU General Public License for more details.
#

from mongrel2		import tnetstrings
from mongrel2.request	import Request
from .transceiver	import Transceiver

import os, sys, time, traceback
import zmq, uuid, json
import netifaces
import logging

timer			= time.time

__author__                      = "Matthew Brisebois"
__email__                       = "matthew@webheroes.ca"
__copyright__                   = "Copyright (c) 2015 Web Heroes Inc."
__license__                     = "Dual License: GPLv3 (or later) and Commercial (see LICENSE)"

__all__			= ["Server","Connector","Client",
                           "Request","Response","WebSocket_response"]

class Response(object):

    def __init__(self, sender, conn_ids, body):
        self.sender	= sender
        self.conn_ids	= conn_ids
        self.body	= body

    @staticmethod
    def parse( resp ):
        """Decode the given msg as a Mongrel2 handler "client" protocol, returning the sender_id (this
        should be our sender_id), an iterable of connection ids (connections to which this message is
        destined), and the message payload.  This is a message format such as would be produced by
        mongrel2.handler Connection.send().
        
        """
        s_id, c_ids_tns, msg        = resp.split( ' ', 2 )
        c_ids, _                    = tnetstrings.parse( c_ids_tns )
        assert not _ and type( c_ids ) is str, "Invalid Mongrel2 Handler connection ids: %r" % c_ids
        return Response(s_id, c_ids.split( ' ' ), msg)
    
class WebSocket_response(object):

    def __init__(self, data, opcode=1, rsvd=0):
        self.data		= data
        self.opcode		= opcode
        self.rsvd		= rsvd
    
    @staticmethod
    def parse(msg):
        """Parse the given 'req' as a WebSockets protocol message.  This is the expected message protocol
        for all incoming messages on a WebSocket, after initial negotiation is completed.  Returns
        fin,rsvd,opcode,msglen,msg.  If the request is not valid (doesn't have the correct WebSocket
        protocol headers), will raise an Exception.  This is a message format such as would be
        produced by mongrel2.handler websocket_response().

        See http://tools.ietf.org/html/rfc6455#page-28 for a description of the WebSockets Base
        Framing Protocol encoding.

        """
        _flg,msg                    = ord( msg[0] ),msg[1:]
        fin,rsvd,opcode             = _flg >> 7 & 0x01, _flg >> 4 & 0x07, _flg & 0x0f
        msglen,msg                  = ord( msg[0] ),msg[1:]
        msk,msglen                  = msglen >> 7 & 0x01, msglen & 0x7f
        if msglen >= 126:
            # 16-bit or 64-bit length
            _shift                  = 16 if msglen == 126 else 64
            msglen                  = 0
            while _shift > 0:
                _shift             -= 8
                msglen             += ord( msg[0] ) << _shift
                msg                 = msg[1:]
        msk,msg                     = (msg[:4],msg[4:]) if msk else ('',msg)
        return Websocket_response(msg,opcode,rsvd)

    def encode():
        header=''
        header+=chr(0x80|self.opcode|self.rsvd<<4)
        realLength=len(self.data)
        if realLength < 126:
            dummyLength=realLength
        elif realLength < 2**16:
            dummyLength = 126
        else:
            dummyLength=127
            header+=chr(dummyLength)
        if dummyLength == 127:
            header += chr(realLength >> 56 &0xff)
            header += chr(realLength >> 48 &0xff)
            header += chr(realLength >> 40 &0xff)
            header += chr(realLength >> 32 &0xff)
            header += chr(realLength >> 24 & 0xff)
            header += chr(realLength >> 16 & 0xff)
        if dummyLength == 126 or dummyLength == 127:
            header += chr(realLength >> 8 & 0xff)
            header += chr(realLength & 0xff)
        return header+self.data

    
class Server(object):

    def __init__(self, sender=None, connect=None, ip=None, push_port=None, sub_port=None, log_level=logging.ERROR):
        self.log		= logging.getLogger('server')
        self.log.setLevel(log_level)
        self.conn_count		= 0
        self._with		= False

        if ip is None:
            self.sip		= netifaces.ifaddresses('eth0')[2][0]['addr']
        else:
            self.sip		= ip

        self.push_addr		= (self.sip, push_port or Transceiver.PUSH_PORT)
        self.sub_addr		= (self.sip, sub_port  or Transceiver.SUB_PORT)

        self.sender		= str(sender or uuid.uuid4())
        self.unconnected	= dict.fromkeys(connect)
        self.connected		= {}
        
    def __enter__(self):
        self._with		= True
        self.CTX		= zmq.Context()
        
        self.push		= self.CTX.socket(zmq.PUSH)
        self.push.bind('tcp://*:{0}'.format(self.push_addr[1]))
        
        self.push_poller	= zmq.Poller()
        self.push_poller.register(self.push, zmq.POLLOUT)

        self.sub		= self.CTX.socket(zmq.SUB)
        self.sub.bind('tcp://*:{0}'.format(self.sub_addr[1]))
        self.sub.setsockopt(zmq.SUBSCRIBE, self.sender)
            
        self.sub_poller		= zmq.Poller()
        self.sub_poller.register(self.sub, zmq.POLLIN)

        return self
    
    def __exit__(self, type, value, traceback):
        for addr in self.connected.copy():
            try:
                if self.disconnect(addr):
                    self.log.debug("Successfully unconnected to address %s, removing from unconnected", addr)
            except Exception as e:
                self.log.warn("Error in disconnect: %s", e)
        
        self.CTX.destroy(linger=0)
        self._with		= False

    def enforce_with(self):
        if not self._with:
            raise Exception("Server() must be run using the 'with' statement")

    def conn_id(self):
        self.conn_count	       += 1
        return str(self.conn_count)

    def connect(self, addr, log_level=None):
        self.enforce_with()
        log_level		= self.log.getEffectiveLevel() if log_level is None else log_level
        
        if addr in self.connected:
            raise Exception("Duplicate connect request: already connected to address {0}".format(addr))
        
        self.log.debug('Attempting to connect to address %s', addr)
        with Connector(addr, self, log_level=log_level) as conn:
            conn.connect()
            if conn.verify_connect(timeout=2000):
                self.connected[addr] = conn
                del self.unconnected[addr]
                return True
            
    def disconnect(self, addr, log_level=None):
        self.enforce_with()
        log_level		= self.log.getEffectiveLevel() if log_level is None else log_level
        
        if addr in self.unconnected:
            raise Exception("Duplicate disconnect request: already unconnected to address {0}".format(addr))
        
        self.log.debug('Attempting to unconnect to address %s', addr)
        with Connector(addr, self, log_level=log_level) as conn:
            conn.disconnect()
            if conn.verify_disconnect(timeout=2000):
                self.unconnected[addr] = None
                del self.connected[addr]
                return True
            
    def client(self, protocol="mongrel2", log_level=None):
        self.enforce_with()
        log_level		= self.log.getEffectiveLevel() if log_level is None else log_level
        
        for addr in self.unconnected.copy():
            if self.connect(addr, log_level):
                self.log.debug('Successfully connected to address %s, removing from unconnected', addr)
            else:
                raise Exception("Unable to connect to handler at address {0}".format(addr))
            
        return Client(self, protocol, log_level=log_level)

    def recv(self, timeout=1000):
        self.enforce_with()
        socks			= dict( self.sub_poller.poll(timeout) )
        if self.sub in socks and socks[self.sub] == zmq.POLLIN:
            return self.sub.recv()
        
    def send(self, msg, timeout=1000):
        self.enforce_with()
        
        socks			= dict( self.push_poller.poll(timeout) )
        if self.push in socks and socks[self.push] == zmq.POLLOUT:
            self.push.send(msg)
        else:
            raise Exception("Failed trying to send message, push socket timed out")

        
class Connector(object):

    def __init__(self, addr, server=None, log_level=logging.ERROR):
        self.ip,_,port		= addr.partition(':')
        self.port		= port or Transceiver.REP_PORT
        self.server		= server
        self._with		= False
        self.log		= logging.getLogger('connector({0})'.format(self.ip))
        self.log.setLevel(log_level)

    def __enter__(self):
        self._with		= True
        self.CTX		= zmq.Context()
        
        self.req		= self.CTX.socket(zmq.REQ)
        self.req.connect( 'tcp://{0}:{1}'.format(self.ip, self.port))
        
        return self

    def __exit__(self, type, value, traceback):
        self._with		= False
        self.CTX.destroy(linger=0)

    def enforce_with(self):
        if not self._with:
            raise Exception("Connector() must be run using the 'with' statement")
        
    def recv(self, timeout=1000):
        self.enforce_with()
        if self.req.poll(timeout) == zmq.POLLIN:
            return self.req.recv()
        else:
            raise Exception("Connectorion to {0} timed out.  Did not receive pong reply".format(self.ip))

    def ping(self):
        self.enforce_with()
        self.req.send('PING')
        resp			= self.recv()
        return resp.lower() == "pong"

    def connect(self):
        self.enforce_with()
        if self.server is None:
            raise Exception("Cannot connect without a server: server={0}".format(self.server))

        req			= Request( self.server.sender, '-1', '/__add_connection__',
                                           { 'METHOD': 'JSON' }, json.dumps({
                                               "push": self.server.push_addr,
                                               "sub": self.server.sub_addr,
                                           }) )
        self.req.send(req.encode())
        resp			= self.recv()
        assert resp.lower() == "received"

    def disconnect(self):
        self.enforce_with()
        if self.server is None:
            raise Exception("Cannot disconnect without a server: server={0}".format(self.server))

        req			= Request( self.server.sender, '-1', '/__remove_connection__', { 'METHOD': 'JSON' }, '{}' )
        self.req.send(req.encode())
        resp			= self.recv()
        assert resp.lower() == "received"

    def verify_disconnect(self, timeout=1000):
        self.enforce_with()
        now			= timer()
        timeout			= now + (timeout/1000)
        msg			= Request( self.server.sender, '-1', '/__disconnect_ping__', { 'METHOD': 'MONGREL2' }, '' ).encode()
        while now < timeout:
            self.req.send(msg)
            self.req.recv()
            resp		= self.server.recv(timeout=100)
            print resp
            if resp is None:
                return True
            now			= timer()
        raise Exception("Verifying disconnection {0} timed out".format(self.ip))

    def verify_connect(self, timeout=1000):
        self.enforce_with()
        now			= timer()
        timeout			= now + (timeout/1000)
        guid			= str(uuid.uuid4())
        msg			= Request( self.server.sender, '-1', '/__ping__', {
            'METHOD': 'MONGREL2',
            'QUERY': 'text={0}'.format(guid),
        }, '' ).encode()
        while now < timeout:
            self.req.send(msg)
            self.req.recv()
            resp		= self.server.recv(timeout=100)
            print resp
            if resp is not None:
                assert Response.parse(resp).body == guid
                return True
            now			= timer()
        raise Exception("Verifying connection {0} timed out".format(self.ip))

    
class Client(object):

    def __init__(self, server, protocol="mongrel2", log_level=logging.ERROR):
        self.server		= server
        self.protocol		= protocol
        self.conn_id		= self.server.conn_id()
        self.log		= logging.getLogger('client({0})'.format(self.conn_id))
        self.log.setLevel(log_level)

    def recv(self, timeout=1000):
        resp			= self.server.recv(timeout)
        if resp is not None:
            if self.protocol == 'mongrel2':
                resp		= Response.parse(resp)
            elif self.protocol == 'http':
                pass
            elif self.protocol == 'websocket':
                resp		= WebSocket_response.parse(resp)
                
        self.log.debug("Received message: %-100.100s...", resp)
        return resp

    def send(self, path, headers=None, body=""):
        headers			= self.build_headers(path, headers)
        req			= Request(self.server.sender, self.conn_id, path, headers, body)
        msg			= req.encode()
        self.log.debug("Sending message: %-40.40s...", msg)
        self.server.send(msg)
                 
    def build_headers(self, path, headers):
        base_headers		= {}
        if self.protocol == 'http':
            query		= headers.get('QUERY', None)
            base_headers.update({
                'PATH':		path,
                'URI':		"{0}{1}".format(path, ('?{0}'.format(query) if query else '')),
                'METHOD':	'GET',
                'REMOTE_ADDR':	self.sip,
            })
        elif self.protocol == 'websocket':
            base_headers.update({
                'METHOD':	'WEBSOCKET',
            })
        elif self.protocol == 'mongrel2':
            base_headers.update({
                'METHOD':	'MONGREL2',
            })
            
        base_headers.update(headers or {})
        return base_headers
            
