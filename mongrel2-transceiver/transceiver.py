"""
utils.transceiver

    ,---,
    |   |
    | M | SUB (bind)
    | G |o < - - - - - - - - - - , < - - - - - - - - - - - - - - - - - - - - - - - - - -,
    | 2 |                        ,                                                      ,
    |   |                        ,                                                      ,
    | S |                        ,                                                      ,                                 .--------,
    | V |o - - - - - ,           , PUB (conn)                                           , PUB (conn)                     {          }
    | R | PUSH       ,   ,-------o-------API------------, PUB (bind)      SUB (conn) ---o-----Node-------------,         |'--------'|
    |   | (bind)     - > o-,     '-------< + .send(msg) o - - - - - - - - - - > o-,     '-------< + .send(msg) |         |          |
    '---'            PULL' | transceiver   |            |                       | | transceiver   |            | - - - - |    DB    |
                    (conn) '-------------> + .recv()    o - - - - - - - - - - > o-'-------------> + .recv()    |         |          |
                         '-----o------------------------' PUSH (bind)      PULL '-----o------------------------'         '-________-'
                               ^ REP (bind)                                (conn)       REP (bind)
                               '_ _ _ _ _ _ _ _ _ _ _
                                                     v REQ (conn)
                                         ,-----------o----------,
                                         |                      |
                                         o        tests         o
                                    PUSH |                      | SUB
                                   (bind)'----------------------' (conn)


Usage:
 >>> from mongrel2_transceiver	import Transceiver
 >>> from utils.discovery	import get_docker_ip
 >>>
 >>> mg2_ip = get_docker_ip('mg2')
 >>> with Transceiver( 'rune',
 ...                   pull_addr	= (mg2_ip, 9999),
 ...                   pub_addr		= (mg2_ip, 9998) ) as trans:
 ...     for sid,conn,req in trans.recv():
 ...         try:
 ...             if req is not None:
 ...                 headers	= req.headers
 ...                 method	= headers.get('METHOD')
 ...                 query	= headers.get('QUERY', {})
"""

from mongrel2		import tnetstrings
from mongrel2.handler	import Connection
from mongrel2.request	import Request
from mongrel2		import handler

import logging
import os, sys, signal, time
import uuid, traceback
import zmq, uuid, json
import urlparse, re
import netifaces

timer			= time.time

__all__			= ["Transceiver","Server","Connector","Client",
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

    
class Transceiver(object):
    OP_TEXT		= 0x1
    OP_BINARY		= 0x2
    OP_CLOSE		= 0x8
    OP_PING		= 0x9
    OP_PONG		= 0xA
    PUSH_PORT		= 9999
    SUB_PORT		= 9998
    REP_PORT		= 9997
    SOCKET_TYPES	= {
        zmq.PUB:	'PUB',
        zmq.SUB:	'SUB',
        zmq.PUSH:	'PUSH',
        zmq.PULL:	'PULL',
        zmq.REQ:	'REQ',
        zmq.REP:	'REP',
    }

    def __init__(self, sender, pull_addr, pub_addr, ping_timeout=30, log_level=logging.ERROR):
        self.log		= logging.getLogger('transceiver')
        self.sender		= sender
        self.pull_addr		= pull_addr
        self.pub_addr		= pub_addr
        self._with		= False
        self.done		= False
        
        self.incoming		= []
        self.outgoing		= []
        self.sender_map		= {}
        self.conn_map		= {}
        
        self.sessions_active	= {}
        self.sessions_ponged	= {}
        self.ping_timeout	= ping_timeout
        self.session_timeout	= timer() + self.ping_timeout

        self.log.setLevel(log_level)

        self.log.debug("Registering SIGTERM interrupt")
        signal.signal( signal.SIGTERM, self.stop )

    # control methods
    def stop(self, *args):
        self.done		= True

    def __enter__(self):
        self._with		= True
        self.poller		= zmq.Poller()
        self.conn		= self.add_connection(self.sender, self.pull_addr, self.pub_addr)

        self.log.debug("Setting up REP socket on port %d", self.REP_PORT)
        self.CTX		= zmq.Context()
        self.rep		= self.CTX.socket(zmq.REP)
        self.rep.bind('tcp://*:{0}'.format(self.REP_PORT))
        self.add_incoming(self.rep)
        return self

    def __exit__(self, type, value, traceback):
        self._with		= False
        handler.CTX.destroy(linger=0)
        # for sock in self.incoming+self.outgoing:
        #     sock.setsockopt(zmq.LINGER, 0)
        #     sock.close()
        self.CTX.destroy(linger=0)

    def _check_with(self):
        if hasattr(self, '_with') and not self._with:
            raise Exception("Connector() must be run using the 'with' statement")

    def add_incoming(self, socket):
        self.incoming.append(socket)
        self.poller.register(socket, zmq.POLLIN)

    def add_outgoing(self, socket):
        self.outgoing.append(socket)
        
    def add_connection(self, sender, push_addr, sub_addr):
        self._check_with()
        pull_addr		= "tcp://{0}:{1}".format(*push_addr)
        pub_addr		= "tcp://{0}:{1}".format(*sub_addr)
        self.log.debug("Setting up connection object on pull:{0} and pub:{1}".format(pull_addr, pub_addr))
        conn		= Connection( sender_id=sender,
                                      sub_addr=pull_addr,
                                      pub_addr=pub_addr )
        
        self.log.debug("Adding sender ID to sender_map: %s", sender)
        self.sender_map[sender]	= conn
        self.conn_map[conn]	= sender
            
        self.add_incoming(conn.reqs)
        self.add_outgoing(conn.resp)
        return conn

    def send_pings(self):
        self._check_with()
        now			= timer()
        self.sessions_active	= self.sessions_ponged
        self.sessions_ponged	= {}
        self.session_timeout	= now + self.ping_timeout
        
        self.log.debug("Reset session_timeout to: %s", self.session_timeout)
        conn_ids		= [req.conn_id for req in self.sessions_active.values()]
        sender			= self.conn_map[self.conn]
        if conn_ids:
            self.log.debug("Sending PING to conn IDs: %s", conn_ids)
            self.conn.deliver_websocket(sender, conn_ids, "", self.OP_PING)
        else:
            self.log.debug("No connections to PING")

    # poller method
    def poll(self, timeout=50):
        self._check_with()
        now			= timer()
        reply			= 'RECEIVED'
        conn,req		= (None, None)
        
        if now >= self.session_timeout:
            self.send_pings()
            
        socks			= dict(self.poller.poll(timeout))
        for sock in self.incoming:
            if sock in socks:
                try:
                    msg		= sock.recv()
                    self.log.debug("Received message: %-40.40s   (socket_type: %s)",
                                  msg[:37]+'...' if len(msg) >= 40 else msg,
                                  self.SOCKET_TYPES.get(sock.socket_type, sock.socket_type))
                    
                    if msg.lower() == 'ping':
                        self.log.debug("REP socket sending PONG")
                        reply	= 'PONG'
                    else:
                        req	= Request.parse(msg)
                        conn	= self.sender_map.get(req.sender)
                except Exception as e:
                    self.log.debug("Error: %s", e)
                finally:
                    if sock.socket_type == zmq.REP:
                        sock.send(reply)

        return conn,req

    # recv loop
    def recv(self):
        self._check_with()
        self.log.debug("Entering infinite while")
        while not self.done:
            try:
                conn,req	= self.poll()
                now		= timer()
                sid		= None
                reply		= None
                reply_opcode	= None

                if req is not None:
                    req_handled	= False
                    sid		= (req.sender,req.conn_id)
                    headers	= req.headers
                    path	= req.path
                    body	= req.body
                    method	= headers.get('METHOD', '').lower()
                    query	= dict( urlparse.parse_qsl(headers.get('QUERY', '').encode('ascii')) )

                    self.log.debug("Processing request from: %s", sid)
                    if query:
                        headers['QUERY_STR']	= headers['QUERY']
                        headers['QUERY']	= query

                    if headers.get('FLAGS') is not None:
                        flags	= headers.get('FLAGS')
                        opcode	= (int(flags, 16) & 0xf)
                        
                        self.log.info("Processing opcode: %s", hex(opcode))
                        if opcode	== self.OP_PONG:
                            self.sessions_ponged[sid]	= req
                            req_handled		= True
                        elif opcode	== self.OP_PING:
                            reply		= req.body
                            reply_opcode	= self.OP_PONG
                        elif opcode	== self.OP_CLOSE:
                            self.sessions_active.pop( sid, None )
                            self.sessions_ponged.pop( sid, None )
                            # reply		= ''
                            # reply_opcode	= self.OP_CLOSE
                        elif opcode	== self.OP_BINARY:
                            pass
    
                    self.log.debug("Request headers: %s", {k:headers[k] for k in ['METHOD','REMOTE_ADDR','QUERY','PATH','VERSION','FLAGS'] if k in headers})
                    
                    if path.endswith('__add_connection__'):
                        self.log.debug("Adding connection with data: %s", req.data)
                        conn			= self.add_connection( req.sender,
                                                                       push_addr=req.data.get('push'),
                                                                       sub_addr	=req.data.get('sub') )
                    elif path.endswith('__ping__'):
                        reply			= query.get('text', '')
                        self.log.debug("Responding to ping: %s", reply)
                    elif method == "websocket_handshake":
                        reply			= True

                    if req_handled or (req.data.get('type') and req.is_disconnect()):
                        sid,conn,req		= None,None,None
                    
                    
                if reply is not None:
                    if conn is None:
                        raise Exception("Can't reply through conn None, req.sender: {0}".format(req.sender))

                    self.log.debug('Reply through sender: %s', req.sender)
                    if method == 'mongrel2':
                        conn.reply(req, reply)
                    elif method == "websocket_handshake":
                        self.sessions_active[sid]	= req
                        self.sessions_ponged[sid]	= req
                        conn.reply(req, '\r\n'.join([ "HTTP/1.1 101 Switching Protocols",
                                                      "Upgrade: websocket",
                                                      "Connection: Upgrade",
                                                      "Sec-WebSocket-Accept: %s\r\n\r\n"]) % req.body)
                        headers['METHOD']	= "WEBSOCKET_CONNECT"
                    elif method == 'websocket':
                        conn.reply_websocket(req, reply, reply_opcode)
                    else:
                        conn.reply_http(req, reply)
                        # HTTP can only send one response.
                        sid,conn,req		= None,None,None

                yield sid,conn,req
            except zmq.ZMQError as e:
                if str(e) == "Interrupted system call":
                    pass
                else:
                    self.log.error("[ error ] Infinite loop broke with error: %s", e)
                    self.log.debug("[ stacktrace ] %s", traceback.format_exc())
            except Exception, e:
                self.log.error("[ error ] Infinite loop broke with error: %s", e)
                self.log.debug("[ stacktrace ] %s", traceback.format_exc())
        
        self.log.debug("Exited infinite loop")
        conn_ids		= [req.conn_id for req in self.sessions_active.values()]
        if conn_ids:
            sender		= self.conn_map[self.conn]
            self.log.debug("Closing open websockets: %s", conn_ids)
            self.conn.deliver_websocket(sender, conn_ids, "", self.OP_CLOSE)
        else:
            self.log.debug("No connections to CLOSE")
        


class Server(object):

    def __init__(self, sender=None, connect=None, ip=None, push_port=Transceiver.PUSH_PORT, sub_port=Transceiver.SUB_PORT):
        self.conn_count		= 0
        self._with		= False

        if ip is None:
            self.sip		= netifaces.ifaddresses('eth0')[2][0]['addr']
        else:
            self.sip		= ip

        self.push_addr		= (self.sip, push_port)
        self.sub_addr		= (self.sip, sub_port)

        self.sender		= str(sender or uuid.uuid4())
        self.unconnected	= connect
        self.connected		= {}
        self.setup		= {}

        # set up default connections
        
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
        self._with		= False
        self.CTX.destroy(linger=0)

    def enforce_with(self):
        if not self._with:
            raise Exception("Server() must be run using the 'with' statement")

    def conn_id(self):
        self.conn_count	       += 1
        return str(self.conn_count)

    def connect(self, ip):
        self.enforce_with()
        if ip in self.connected:
            raise Exception("Duplicate connect request: already connected to IP address %s", ip)
        with Connector(ip, self) as conn:
            conn.setup()
            if conn.verify_connectivity(timeout=2000):
                self.connected[ip]	= conn
                return True
            
    def client(self, protocol="mongrel2"):
        self.enforce_with()
        for ip in self.unconnected:
            if self.connect(ip):
                self.unconnected.remove(ip)
        return Client(self, protocol)

    def recv(self, timeout=1000):
        self.enforce_with()
        socks		= dict( self.sub_poller.poll(timeout) )
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

    def __init__(self, ip, server=None):
        self.ip			= ip
        self.server		= server
        self._with		= False

    def __enter__(self):
        self._with		= True
        self.CTX		= zmq.Context()
        
        self.req		= self.CTX.socket(zmq.REQ)
        self.req.connect( 'tcp://{0}:{1}'.format(self.ip, Transceiver.REP_PORT))
        
        self.poller		= zmq.Poller()
        self.poller.register(self.req, zmq.POLLIN)
        
        return self

    def __exit__(self, type, value, traceback):
        self._with		= False
        self.CTX.destroy(linger=0)

    def enforce_with(self):
        if not self._with:
            raise Exception("Connector() must be run using the 'with' statement")
        
    def recv(self, timeout=1000):
        self.enforce_with()
        socks			= dict( self.poller.poll(timeout) )
        if self.req in socks and socks[self.req] == zmq.POLLIN:
            return self.req.recv()
        else:
            raise Exception("Connectorion to {0} timed out.  Did not receive pong reply".format(self.ip))

    def ping(self):
        self.enforce_with()
        self.req.send('PING')
        resp			= self.recv()
        return resp.lower() == "pong"

    def setup(self):
        self.enforce_with()
        if self.server is None:
            raise Exception("Cannot setup without a server: server={0}".format(self.server))

        req			= Request( self.server.sender, '-1',
                                           '/__add_connection__',
                                           { 'METHOD': 'JSON' },
                                           json.dumps({
                                               "push": self.server.push_addr,
                                               "sub": self.server.sub_addr,
                                           }) )
        self.req.send(req.encode())
        resp			= self.recv()
        assert resp.lower() == "received"

    def verify_connectivity(self, timeout=1000):
        self.enforce_with()
        if self.server is None:
            raise Exception("Cannot setup without a server: server={0}".format(self.server))
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

    def __init__(self, server, protocol="mongrel2"):
        self.server		= server
        self.protocol		= protocol
        self.conn_id		= self.server.conn_id()

    def recv(self, timeout=1000):
        resp			= self.server.recv(timeout)
        if resp is not None:
            if self.protocol == 'mongrel2':
                resp		= Response.parse(resp)
            elif self.protocol == 'http':
                pass
            elif self.protocol == 'websocket':
                resp		= WebSocket_response.parse(resp)
        return resp

    def send(self, path, headers=None, body=""):
        headers			= self.build_headers(path, headers)
        req			= Request(self.server.sender, self.conn_id, path, headers, body)
        self.server.send(req.encode())
                 
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
            
