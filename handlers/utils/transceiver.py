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
 >>> from utils import Transceiver
 >>> api_mau = Transceiver(pull_ip="172.17.0.171", pub_ip="172.17.0.171")
 >>> for req in api_mau.recv():
 ...     if req is not None:
 ...         # handle request...
"""

from mongrel2.handler	import Connection
from mongrel2.request	import Request
from .			import discovery

import os, sys, signal, time
import uuid, logging, traceback
import zmq, uuid
import urlparse, re

timer			= time.time

class Transceiver(object):
    OP_TEXT		= 0x1
    OP_BINARY		= 0x2
    OP_CLOSE		= 0x8
    OP_PING		= 0x9
    OP_PONG		= 0xA
    PUSH_PORT		= 9999
    SUB_PORT		= 9998
    REP_PORT		= 9997

    def __init__(self, pull_ip, pub_ip):
        self.pull_addr		= "tcp://{0}:{1}".format(pull_ip, self.PUSH_PORT)
        self.pub_addr		= "tcp://{0}:{1}".format(pub_ip,  self.SUB_PORT)
        self._with		= False
        self.done		= False
        self.connections	= []
        self.sender_map		= {}
        
        self.sessions_active	= {}
        self.sessions_ponged	= {}
        self.ping_timeout	= 30
        self.session_timeout	= timer() + self.ping_timeout

        logging.debug("Registering SIGTERM interrupt")
        signal.signal( signal.SIGTERM, self.stop )

    # control methods
    def stop(self, *args):
        self.done		= True

    def __enter__(self):
        self._with		= True
        self.poller		= zmq.Poller()
        self.conn		= self.add_connection(self.pull_addr, self.pub_addr)

        logging.debug("Setting up REP socket on port %d", self.REP_PORT)
        self.CTX		= zmq.Context()
        self.rep		= self.CTX.socket(zmq.REP)
        self.rep.bind('tcp://*:{0}'.format(self.REP_PORT))
        self.poller.register(self.rep, zmq.POLLIN)

        return self

    def __exit__(self, type, value, traceback):
        self._with		= False
        self.CTX.destroy(linger=0)

    def _check_with(self):
        if hasattr(self, '_with') and not self._with:
            raise Exception("Connector() must be run using the 'with' statement")

    def add_connection(self, pull_addr, pub_addr):
        self._check_with()
        logging.debug("Setting up connection object on pull:{0} and pub:{1}".format(pull_addr, pub_addr))
        conn		= Connection( sender_id=str(uuid.uuid1()),
                                      sub_addr=pull_addr,
                                      pub_addr=pub_addr )

        self.connections.append(conn)
        self.poller.register(conn.reqs, zmq.POLLIN)
        return conn

    def add_sender(self, sender_id, conn):
        self._check_with()
        if sender_id not in self.sender_map:
            logging.debug("Adding sender ID to sender_map: %s", sender_id)
            self.sender_map[sender_id] = conn
        return self.sender_map

    def get_sender_conn(self, sender_id):
        self._check_with()
        return self.sender_map.get(sender_id)

    def send_pings(self):
        self._check_with()
        now			= timer()
        self.sessions_active	= self.sessions_ponged
        self.sessions_ponged	= {}
        self.session_timeout	= now + self.ping_timeout
        
        logging.debug("Reset session_timeout to: %s", self.session_timeout)
        for sid,req in self.sessions_active.items():
            logging.debug("Sending PING to session ID: %s", sid)
            self.respond_websocket(req, "", self.OP_PING)

    # handler methods
    def parse_req_message(self, msg):
        self._check_with()
        cmd,args		= re.search('(.*)\((.*)\)', msg).groups()
        parsed_args		= dict( map(lambda x: tuple(x.split('=')), args.split(',')) )
        return cmd,parsed_args
    
    def handle_rep_request(self, msg):
        self._check_with()
        logging.debug("Received msg on REP socket: %s", msg)
        if msg.lower() == 'ping':
            logging.debug("Sending pong to out rep socket")
            self.rep.send('PONG')
        else:
            cmd,args		= self.parse_req_message(msg)
            if cmd == 'setup':
                conn		= self.add_connection( pull_addr=args['push'],
                                                       pub_addr	=args['sub'])
                self.add_sender(args['sender'], conn)
                self.rep.send('connected')
            elif cmd == 'broadcast':
                conn		= self.get_sender_conn(args['sender'])
                if conn:
                    conn.resp.send('{0} {1}'.format(args['sender'], args['ping']))
                    self.rep.send('pinged')
                else:
                    self.rep.send('no sender')
            else:
                self.rep.send('Unknown command: {0}'.format(cmd))

    def handle_opcode(self, opcode, req):
        self._check_with()
        sid			= (req.sender,req.conn_id)
        
        logging.info("Processing opcode: %s", hex(opcode))
        if opcode	== self.OP_PONG:
            self.sessions_ponged[sid]	= req
            
        elif opcode	== self.OP_PING:
            self.respond_websocket(req, req.body, self.OP_PONG)
            
        elif opcode	== self.OP_CLOSE:
            self.sessions_active.pop( sid, None )
            self.sessions_ponged.pop( sid, None )
            self.respond_websocket(req, "", self.OP_CLOSE)
            
        elif opcode	== self.OP_BINARY:
            pass

    # poller method
    def poll(self, timeout=50):
        self._check_with()
        now			= timer()
        if now >= self.session_timeout:
            self.send_pings()
            
        socks			= dict(self.poller.poll(timeout))
                
        if self.rep in socks and socks[self.rep] == zmq.POLLIN:
            msg			= self.rep.recv()
            self.handle_rep_request(msg)
        
        for conn in self.connections:
            if conn.reqs in socks and socks[conn.reqs] == zmq.POLLIN:
                req			= conn.recv()
                self.add_sender(req.sender, conn)
                return conn, req
        return None, None

    # recv loop
    def recv(self):
        self._check_with()
        logging.debug("Entering infinite while")
        while not self.done:
            try:
                conn,req	= self.poll()
                now		= timer()

                if req:
                    sid		= (req.sender,req.conn_id)
                    logging.debug("Processing request from: %s", sid)
                    headers	= req.headers
                    path	= req.path
                    body	= req.body
                    method	= headers.get('METHOD', '').lower()
                    query	= dict( urlparse.parse_qsl(headers.get('QUERY', '').encode('ascii')) )
                    flags	= headers.get('FLAGS')
                    opcode	= self.OP_TEXT if flags is None else (int(flags, 16) & 0xf)

                    if opcode != self.OP_TEXT:
                        self.handle_opcode(opcode, req)
                        continue
    
                    logging.debug("Request headers: %s", headers)
                    if method == "websocket_handshake":
                        self.sessions_active[sid]	= req
                        self.sessions_ponged[sid]	= req
                        self.reply_websocket_accept(req)
                    elif path.endswith('ping'):
                        text	= query.get('text')
                        logging.debug("Sending pong with body: %s", text)
                        self.respond_http(req, text)
                        logging.info("Sent pong to %s", headers.get('REMOTE_ADDR'))
                        continue
                    else:
                        if query:
                            headers['QUERY_STR']	= headers['QUERY']
                            headers['QUERY']		= query
                        yield (sid,req)
                else:
                    yield (None, None)
            except zmq.ZMQError as e:
                if str(e) == "Interrupted system call":
                    pass
                else:
                    logging.error("[ error ] Infinite loop broke with error: %s", e)
                    logging.debug("[ stacktrace ] %s", traceback.format_exc())
            except Exception, e:
                logging.error("[ error ] Infinite loop broke with error: %s", e)
                logging.debug("[ stacktrace ] %s", traceback.format_exc())
        
        logging.debug("Exited infinite loop")

        
    # responding methods
    def respond_http(self, req, *args, **kwargs):
        self._check_with()
        self.respond('_http', req, *args, **kwargs)

    def respond_websocket(self, req, *args, **kwargs):
        self._check_with()
        self.respond('_websocket', req, *args, **kwargs)
        
    def respond(self, response_type, req, *args, **kwargs):
        self._check_with()
        conn			= self.get_sender_conn(req.sender)
        if conn is not None:
            getattr(conn, "reply"+response_type)(req, *args, **kwargs)
        else:
            raise Exception("Could not respond to request with sender ID: %s", req.sender)

    def reply_websocket_accept(self, req):
        self._check_with()
        self.respond('', req, '\r\n'.join([
            "HTTP/1.1 101 Switching Protocols",
            "Upgrade: websocket",
            "Connection: Upgrade",
            "Sec-WebSocket-Accept: %s\r\n\r\n"]) % req.body)


class Server(object):
    CONN_COUNT		= 0 

    def __init__(self, sender=None, connect=None):
        Server.CONN_COUNT      += 1
        self.conn_id		= str(Server.CONN_COUNT)
        self._with		= False

        self.sip		= discovery.get_docker_ip()
        self.push_addr		= (self.sip, Transceiver.PUSH_PORT)
        self.sub_addr		= (self.sip, Transceiver.SUB_PORT)

        self.sender		= str(sender or uuid.uuid4())
        self.unconnected	= connect
        self.connected		= {}
        self.setup		= {}

        # set up default connections
        
    def __enter__(self):
        self._with		= True
        self.CTX		= zmq.Context()
        
        self.push		= self.CTX.socket(zmq.PUSH)
        self.push.bind('tcp://*:{0}'.format(Transceiver.PUSH_PORT))
        
        self.push_poller	= zmq.Poller()
        self.push_poller.register(self.push, zmq.POLLOUT)

        self.sub		= self.CTX.socket(zmq.SUB)
        self.sub.bind('tcp://*:{0}'.format(Transceiver.SUB_PORT))
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

    def connect(self, ip):
        self.enforce_with()
        if ip in self.connected:
            raise Exception("Duplicate connect request: already connected to IP address %s", ip)
        with Connector(ip, self) as conn:
            conn.setup()
            if conn.verify_connectivity(timeout=2000):
                self.connected[ip]	= conn
                return True
            
    def client(self):
        self.enforce_with()
        for ip in self.unconnected:
            if self.connect(ip):
                self.unconnected.remove(ip)
        return Client(self)

    def recv(self, timeout=1000):
        self.enforce_with()
        socks		= dict( self.sub_poller.poll(timeout) )
        if self.sub in socks and socks[self.sub] == zmq.POLLIN:
            return self.sub.recv()
        
    def send(self, path, headers=None, body="", timeout=1000):
        self.enforce_with()
        query			= headers.get('QUERY', None)
        all_headers		= {
            'PATH':		path,
            'URI':		"{0}{1}".format(path, ('?{0}'.format(query) if query else '')),
            'METHOD':		'GET',
            'REMOTE_ADDR':	self.sip,
        }
        all_headers.update(headers or {})
        req			= Request(self.sender, self.conn_id, path=path, headers=all_headers, body=body)
        msg			= req.encode()
        
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
        
        self.req.send( 'setup(sender={0},push=tcp://{1}:{2},sub=tcp://{3}:{4})'.format(
            self.server.sender, *(self.server.push_addr+self.server.sub_addr)
        ))
        resp			= self.recv()
        assert resp.lower() == "connected"

    def verify_connectivity(self, timeout=1000):
        self.enforce_with()
        if self.server is None:
            raise Exception("Cannot setup without a server: server={0}".format(self.server))
        now			= timer()
        timeout			= now + (timeout/1000)
        while now < timeout:
            self.req.send('broadcast(sender={0},ping={1})'.format(self.server.sender, 'b5b44d95-2e33-4af9-95fe-1cade9cd86ef'))
            print self.req.recv()
            resp		= self.server.recv(timeout=100)
            if resp is not None:
                return True
            now			= timer()
        raise Exception("Verifying connection {0} timed out".format(self.ip))

class Client(object):

    def __init__(self, server):
        self.server		= server

    def recv(self, timeout=1000):
        return self.server.recv(timeout)

    def send(self, *args, **kwargs):
        self.server.send(*args, **kwargs)
