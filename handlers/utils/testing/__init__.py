
import subp_helper
import zmq, uuid

from ..			import Transceiver
from ..			import discovery
from mongrel2.request	import Request

class Request_connection(object):

    def __init__(self, transceiver_ip):
        self.tip		= transceiver_ip
        self.sip		= discovery.get_docker_ip()
        self.push_addr		= (self.sip, Transceiver.PUSH_PORT)
        self.sub_addr		= (self.sip, Transceiver.SUB_PORT)
        self.conn_id		= str(1)
        self.CTX		= zmq.Context()

        if not hasattr(Request_connection, 'push'):
            Request_connection.push	= self.CTX.socket(zmq.PUSH)
            self.push.bind( 'tcp://*:{0}'.format(Transceiver.PUSH_PORT))
            
        if not hasattr(Request_connection, 'sub'):
            Request_connection.sub	= self.CTX.socket(zmq.SUB)
            Request_connection.sender	= str(uuid.uuid4())
            self.sub.bind(  'tcp://*:{0}'.format(Transceiver.SUB_PORT))
            self.sub.setsockopt(zmq.SUBSCRIBE, self.sender)
        
        if not hasattr(Request_connection, 'req'):
            Request_connection.req	= self.CTX.socket(zmq.REQ)
            self.req.connect( 'tcp://{0}:{1}'.format(self.tip, Transceiver.REP_PORT))
        
        self.req_poller		= zmq.Poller()
        self.req_poller.register(self.req, zmq.POLLIN)
        
        self.sub_poller		= zmq.Poller()
        self.sub_poller.register(self.sub, zmq.POLLIN)
        
        self.push_poller	= zmq.Poller()
        self.push_poller.register(self.push, zmq.POLLOUT)

    # pollers
    def req_recv(self, timeout=1000):
        socks		= dict( self.req_poller.poll(timeout) )
        if self.req in socks and socks[self.req] == zmq.POLLIN:
            return self.req.recv()
        else:
            raise Exception("Connection to {0} timed out.  Did not receive pong reply".format(self.tip))

    def recv(self, timeout=1000):
        socks		= dict( self.sub_poller.poll(timeout) )
        if self.sub in socks and socks[self.sub] == zmq.POLLIN:
            return self.sub.recv()

    def send(self, path, headers=None, body="", timeout=1000):
        if headers is None:
            headers		= {}
        if not headers.get('METHOD'):
            headers['METHOD']	= 'GET'
        req			= Request(self.sender, self.conn_id, path=path, headers=headers, body=body)
        msg			= req.encode()
        
        socks		= dict( self.push_poller.poll(timeout) )
        if self.push in socks and socks[self.push] == zmq.POLLOUT:
            self.push.send(msg)
        else:
            raise Exception("Failed trying to send message over push socket timed out")

    # req socket methods
    def ping(self):
        self.req.send('PING')
        resp		= self.req_recv()
        assert resp.lower() == "pong"

    def setup(self, server_ip=None):
        self.req.send('setup(push=tcp://{0}:{1},sub=tcp://{2}:{3})'.format(*self.push_addr+self.sub_addr))
        resp		= self.req_recv()
        assert resp.lower() == "connected"
        
