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
import os, sys, signal, time
import uuid, logging, traceback
import zmq
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
        self.done		= False
        self.poller		= zmq.Poller()
        self.connections	= []
        self.sender_map		= {}
        
        self.sessions_active	= {}
        self.sessions_ponged	= {}
        self.ping_timeout	= 30
        self.session_timeout	= timer() + self.ping_timeout

        # set up primary connection
        self.conn		= self.add_connection(self.pull_addr, self.pub_addr)

        logging.debug("Setting up REP socket on port %d", self.REP_PORT)
        CTX			= zmq.Context()
        self.rep		= CTX.socket(zmq.REP)
        self.rep.bind('tcp://*:{0}'.format(self.REP_PORT))
        self.poller.register(self.rep, zmq.POLLIN)

        logging.debug("Registering SIGTERM interrupt")
        signal.signal( signal.SIGTERM, self.stop )

    # control methods
    def stop(self, *args):
        self.done		= True

    def add_connection(self, pull_addr, pub_addr):
        logging.debug("Setting up connection object on pull:{0} and pub:{1}".format(pull_addr, pub_addr))
        conn		= Connection( sender_id=str(uuid.uuid1()),
                                      sub_addr=pull_addr,
                                      pub_addr=pub_addr )

        self.connections.append(conn)
        self.poller.register(conn.reqs, zmq.POLLIN)
        return conn

    def add_sender(self, sender_id, conn):
        if sender_id not in self.sender_map:
            logging.debug("Adding sender ID to sender_map: %s", sender_id)
            self.sender_map[sender_id] = conn
        return self.sender_map

    def get_sender_conn(self, sender_id):
        return self.sender_map.get(sender_id)

    def send_pings(self):
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
        cmd,args		= re.search('(.*)\((.*)\)', msg).groups()
        parsed_args		= dict( map(lambda x: tuple(x.split('=')), args.split(',')) )
        return cmd,parsed_args
    
    def handle_rep_request(self, msg):
        logging.debug("Received msg on REP socket: %s", msg)
        if msg.lower() == 'ping':
            logging.debug("Sending pong to out rep socket")
            self.rep.send('PONG')
        else:
            cmd,args		= self.parse_req_message(msg)
            if cmd == 'setup':
                self.add_connection(pull_addr=args['push'], pub_addr=args['sub'])
                self.rep.send('connected')
            else:
                self.rep.send('unknown command: {0}'.format(cmd.keys()))

    def handle_opcode(self, opcode, req):
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
                        req.headers['QUERY']	= query
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
        self.respond('_http', req, *args, **kwargs)

    def respond_websocket(self, req, *args, **kwargs):
        self.respond('_websocket', req, *args, **kwargs)
        
    def respond(self, response_type, req, *args, **kwargs):
        conn			= self.get_sender_conn(req.sender)
        if conn is not None:
            getattr(conn, "reply"+response_type)(req, *args, **kwargs)
        else:
            raise Exception("Could not respond to request with sender ID: %s", req.sender)

    def reply_websocket_accept(self, req):
        self.respond('', req, '\r\n'.join([
            "HTTP/1.1 101 Switching Protocols",
            "Upgrade: websocket",
            "Connection: Upgrade",
            "Sec-WebSocket-Accept: %s\r\n\r\n"]) % req.body)
