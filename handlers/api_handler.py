
from mongrel2_transceiver	import Transceiver
from utils.discovery		import get_docker_ip
from utils			import logging

import signal, traceback

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
    with Transceiver('rune', pull_addr=(mg2_ip, 9999), pub_addr=(mg2_ip, 9998), log_level=logging.DEBUG) as trans:
        
        for sid,conn,req in trans.recv():
            try:
                if req is not None:
                    headers	= req.headers
                    method	= headers.get('METHOD', '').lower()
                    query	= headers.get('QUERY', {})
                    
                    if method == "websocket":
                        log.debug("Message: %s", req.body)
                        conn.reply_websocket(req, "Making friends, after school!  Behind the bus, I'm breakin fools...")
                        
                    elif method in ['get','post','put','delete']:
                        # this is where the node.py forward will be.  For now reply...
                        log.info("[ temp ] Sending templorary reply")
                        conn.reply_http(req, "Forwarding to node...(psych)")
                        
                    elif method == "mongrel2":
                        pass
                    else:
                        log.debug("Unrecognized method %s: %s", method.upper(), req.path)
                else:
                    pass

                if shutdown:
                    log.debug("Exiting trans.recv() loop...")
                    break
            except Exception, e:
                log.error("[ error ] Handling request broke with error: %s", e)
                log.debug("[ stacktrace ] %s", traceback.format_exc())

    
if __name__ == "__main__":
    log			= logging.getLogger('api')
    log.setLevel(logging.DEBUG)
    
    log.debug("Registering SIGTERM interrupt")
    signal.signal( signal.SIGTERM, term_signalled)
    
    main()
