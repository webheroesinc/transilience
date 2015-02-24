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
import urlparse

timer			= time.time

class Transceiver(object):
    OP_TEXT		= 0x1
    OP_BINARY		= 0x2
    OP_CLOSE		= 0x8
    OP_PING		= 0x9
    OP_PONG		= 0xA
    PULL_PORT		= 9999
    PUB_PORT		= 9998
    REP_PORT		= 9997

    def __init__(self, pull_ip, pub_ip):
        self.pull_addr		= "tcp://{0}:{1}".format(pull_ip, self.PULL_PORT)
        self.pub_addr		= "tcp://{0}:{1}".format(pub_ip,  self.PUB_PORT)
        self.done		= False
        self.poller		= zmq.Poller()
        self.connections	= []

        # set up primary connection
        self.conn		= self.add_connection(self.pull_addr, self.pub_addr)

        logging.debug("Registering SIGTERM interrupt")
        signal.signal( signal.SIGTERM, self.stop )

    def add_connection(self, pull_addr, pub_addr):
        logging.debug("Setting up connection object on pull:{0} and pub:{1}".format(pull_addr, pub_addr))
        conn		= Connection( sender_id=str(uuid.uuid1()),
                                      sub_addr=pull_addr,
                                      pub_addr=pub_addr )

        self.connections.append(conn)
        self.poller.register(conn.reqs, zmq.POLLIN)
        return conn

    def stop(self, *args):
        self.done		= True
    
    def recv(self):
        sessions_active		= {}
        sessions_ponged		= {}
        ping_timeout		= 30
        session_timeout		= timer() + ping_timeout
        
        logging.debug("Entering infinite while")
        while not self.done:
            try:
                now		= timer()
            
                if now >= session_timeout:
                    sessions_active	= sessions_ponged
                    sessions_ponged	= {}
                    session_timeout	= now + ping_timeout
                    logging.debug("Reset session_timeout to: %s", session_timeout)
                    for sid,req in sessions_active.items():
                        logging.debug("Sending PING to session ID: %s", sid)
                        self.conn.reply_websocket(req, "", self.OP_PING)
            
                socks		= dict(self.poller.poll(50))
                now		= timer()
                req		= None
                for conn in self.connections:
                    if conn.reqs in socks and socks[conn.reqs] == zmq.POLLIN:
                        req	= conn.recv()
                        break
                if req:
                    sid		= (req.sender,req.conn_id)
                    headers	= req.headers
                    path	= req.path
                    body	= req.body
                    method	= headers.get('METHOD', '').lower()
                    query	= dict( urlparse.parse_qsl(headers.get('QUERY', '').encode('ascii')) )
                    flags	= headers.get('FLAGS')
                    opcode	= self.OP_TEXT if flags is None else (int(flags, 16) & 0xf)
    
                    if opcode != self.OP_TEXT:
                        logging.info("Processing opcode: %s", hex(opcode))
                        if opcode	== self.OP_PONG:
                            sessions_ponged[sid]	= req
                        elif opcode	== self.OP_PING:
                            conn.reply_websocket(req, req.body, self.OP_PONG)
                        elif opcode	== self.OP_CLOSE:
                            sessions_active.pop( sid, None )
                            sessions_ponged.pop( sid, None )
                            conn.reply_websocket(req, "", self.OP_CLOSE)
                        elif opcode	== self.OP_BINARY:
                            pass
                        continue
    
                    logging.debug("Request headers: %s", headers)
                    if method == "websocket_handshake":
                        sessions_active[sid]	= req
                        sessions_ponged[sid]	= req
                        conn.reply(req,
                                   '\r\n'.join([
                                       "HTTP/1.1 101 Switching Protocols",
                                       "Upgrade: websocket",
                                       "Connection: Upgrade",
                                       "Sec-WebSocket-Accept: %s\r\n\r\n"]) % req.body)
                    elif path.endswith('ping'):
                        text	= query.get('text')
                        logging.debug("Sending pong with body: %s", text)
                        self.conn.reply_http(req, text)
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
                    
