
from mongrel2_transceiver	import Transceiver
from utils.discovery		import get_docker_ip
from utils			import logging

import signal, traceback
import zmq

shutdown		= False

def term_signalled(*args):
    global shutdown
    log.debug("[ shutdown ] Shutdown has been signalled")
    shutdown		= True

def main(**args):
    global shutdown
    log.debug("Getting mg2 address")
    mg2_ip		= get_docker_ip('mg2')
    log.warn("Using address %s for mg2 connection", mg2_ip)

    CTX			= zmq.Context()
    push		= CTX.socket(zmq.PUSH)
    pub			= CTX.socket(zmq.PUB)
    push.bind('tcp://*:9999')
    pub.bind('tcp://*:19999')
    
    with Transceiver('rune', pull_addr=(mg2_ip, 9999), pub_addr=(mg2_ip, 9998), log_level=logging.DEBUG) as trans:
        for sid,conn,req in trans.recv():
            try:
                if req is not None:
                    headers	= req.headers
                    method	= headers.get('METHOD', '').lower()
                    query	= headers.get('QUERY', {})
                    
                    if method == "websocket":
                        log.debug("Message: %s", req.body)
                        if push.poll(timeout=.1, flags=zmq.POLLOUT):
                            req.forward(push)
                        else:
                            conn.reply_websocket(req, "Failed to process request")
                        
                    elif method in ['get','post','put','delete']:
                        conn.reply_http(req, "HTTP is gay! Use WebSockets champ...")
                        
                    elif method == "mongrel2":
                        pass
                    elif method == "json":
                        log.debug("Doing nothing with JSON message: %s", req.body)
                    else:
                        log.debug("Unrecognized method %s: %s", method.upper(), req.path)

                if shutdown:
                    log.debug("Exiting trans.recv() loop...")
                    break
            except Exception, e:
                log.error("[ error ] Handling request broke with error: %s", e)
                log.debug("[ stacktrace ] %s", traceback.format_exc())
        CTX.destroy(linger=0)
    
if __name__ == "__main__":
    log			= logging.getLogger('api')
    log.setLevel(logging.DEBUG)
    
    log.debug("Registering SIGTERM interrupt")
    signal.signal( signal.SIGTERM, term_signalled)
    
    main()

