
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

__author__                      = "Matthew Brisebois"
__email__                       = "matthew@webheroes.ca"
__copyright__                   = "Copyright (c) 2015 Web Heroes Inc."
__license__                     = "Dual License: GPLv3 (or later) and Commercial (see LICENSE)"

from mongrel2.handler	import Connection
from mongrel2.request	import Request

import os, sys, time, traceback
import zmq, json, urlparse
import logging

timer			= time.time

__all__			= ["Transceiver"]

    
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

    def __init__(self, sender, pull_addr, pub_addr, rep_port=None, ping_timeout=30, log_level=logging.ERROR):
        self.log		= logging.getLogger('transceiver')
        self.log.setLevel(log_level)
        self.sender		= sender
        self.pull_addr		= pull_addr
        self.pub_addr		= pub_addr
        self.rep_port		= rep_port or Transceiver.REP_PORT
        self._with		= False
        
        self.incoming		= []
        self.outgoing		= []
        self.sender_map		= {}
        self.conn_map		= {}
        
        self.sessions_active	= {}
        self.sessions_ponged	= {}
        self.ping_timeout	= ping_timeout
        self.session_timeout	= timer() + self.ping_timeout

    def __enter__(self):
        self._with		= True
        self.poller		= zmq.Poller()
        self.conn		= self.add_connection(self.sender, self.pull_addr, self.pub_addr)

        self.log.debug("Setting up REP socket on port %d", self.rep_port)
        self.CTX		= zmq.Context()
        self.rep		= self.CTX.socket(zmq.REP)
        self.rep.bind('tcp://*:{0}'.format(self.rep_port))
        self.add_incoming(self.rep)
        return self

    def __exit__(self, type, value, traceback):
        self._with		= False
        
        self.log.debug("Exiting with statement")
        conn_ids		= [req.conn_id for req in self.sessions_active.values()]
        if conn_ids:
            sender		= self.conn_map[self.conn]
            self.log.debug("Closing open websockets: %s", conn_ids)
            self.conn.deliver_websocket(sender, conn_ids, "", self.OP_CLOSE)
        else:
            self.log.debug("No connections to CLOSE")
            
        self.log.debug("Closing incoming and outgoing conn sockets & destorying Transceiver ZMQ context")
        for sock in self.incoming+self.outgoing:
            sock.setsockopt(zmq.LINGER, 0)
            sock.close()
        self.CTX.destroy(linger=0)

    def _check_with(self):
        if hasattr(self, '_with') and not self._with:
            raise Exception("Connector() must be run using the 'with' statement")

    def add_incoming(self, socket):
        self.incoming.append(socket)
        self.poller.register(socket, zmq.POLLIN)
    def remove_incoming(self, socket):
        self.incoming.pop(self.incoming.index(socket))
        self.poller.unregister(socket)

    def add_outgoing(self, socket):
        self.outgoing.append(socket)
    def remove_outgoing(self, socket):
        self.outgoing.pop(self.outgoing.index(socket))
        
    def add_connection(self, sender, push_addr, sub_addr):
        self._check_with()

        if sender in self.sender_map:
            conn		= self.sender_map[sender]
            raise Exception("Sender ID ({0}) already in use by connection Connection(pull_addr={1},pub_addr={2})".format(sender, conn.sub_addr, conn.pub_addr))
        
        pull_addr		= "tcp://{0}:{1}".format(*push_addr)
        pub_addr		= "tcp://{0}:{1}".format(*sub_addr)
        self.log.debug("Setting up connection object on pull:{0} and pub:{1}".format(pull_addr, pub_addr))
        conn		= Connection( sender_id=sender,
                                      sub_addr=pull_addr,
                                      pub_addr=pub_addr )
        
        self.log.debug("Adding sender ID to sender_map: %s", sender)
        self.sender_map[sender]		= conn
        self.conn_map[conn]		= sender
            
            
        self.add_incoming(conn.reqs)
        self.add_outgoing(conn.resp)
        return conn

    def remove_connection(self, sender):
        self._check_with()
        
        if sender not in self.sender_map:
            raise Exception("There is no Connection for sender ID {0}".format(sender))
        
        conn				= self.sender_map.pop(sender)
        self.conn_map.pop(conn)
        
        self.remove_incoming(conn.reqs)
        self.remove_outgoing(conn.resp)

        for sock in [conn.reqs, conn.resp]:
            sock.setsockopt(zmq.LINGER, 0)
            sock.close()

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
    def poll(self):
        self._check_with()
        now			= timer()
        conn,req		= (None, None)
        
        if now >= self.session_timeout:
            self.send_pings()
            
        remaining		= max(self.session_timeout - now, 0)		# seconds
        self.log.debug("ZMQ Poller timeout set to: %s seconds", remaining)
        socks			= dict(self.poller.poll(remaining*1000))	# milliseconds
        for sock in self.incoming:
            if sock in socks:
                reply		= 'RECEIVED'
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

        self.log.debug("[ returning ] %-46.46s ( %s, %s )", "conn,req", conn, req)
        return conn,req

    # recv loop
    def recv(self):
        self._check_with()
        self.log.debug("Entering infinite while")
        while True:
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
                                                                       push_addr= req.data.get('push'),
                                                                       sub_addr	= req.data.get('sub') )
                    elif path.endswith('__remove_connection__'):
                        self.log.debug("Removing connection with sender ID: %s", req.sender)
                        self.remove_connection( req.sender )
                    elif path.endswith('__ping__'):
                        reply			= query.get('text', '')
                        self.log.debug("Responding to ping: %s", reply)
                    elif path.endswith('__disconnect_ping__'):
                        reply			= "disconnect_ping"
                        self.log.debug("Responding to disconnect ping: %s", reply)
                    elif method == "websocket_handshake":
                        reply			= True

                    if req_handled or (req.data.get('type') and req.is_disconnect()):
                        sid,conn,req		= None,None,None
                    
                    
                if reply is not None and reply != "disconnect_ping":
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
                    yield (None,None,None)
                else:
                    self.log.error("[ error ] Infinite loop broke with error: %s", e)
                    self.log.debug("[ stacktrace ] %s", traceback.format_exc())
            except Exception, e:
                self.log.error("[ error ] Infinite loop broke with error: %s", e)
                self.log.debug("[ stacktrace ] %s", traceback.format_exc())
        

