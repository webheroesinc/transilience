
from mongrel2_transceiver	import Transceiver
from utils.discovery		import get_docker_ip
from utils			import logging

import signal, traceback

shutdown		= False

def term_signalled(*args):
    global shutdown
    shutdown		= True

def main(**args):
    global shutdown

    log.debug("Getting mg2 address")
    mg2_ip		= get_docker_ip('mg2')

    log.info("Using address %s for mg2 connection", mg2_ip)
    with Transceiver( 'centaurus',
                      pull_addr	= (mg2_ip, 9999),
                      pub_addr	= (mg2_ip, 9998),
                      log_level	= logging.DEBUG ) as trans:
        
        for sid,conn,req in trans.recv():
            try:
                if req is not None:
                    headers	= req.headers
                    method	= headers.get('METHOD', '').lower()
                    query	= headers.get('QUERY', {})
                    remote_addr	= headers.get('REMOTE_ADDR')
                    flags	= headers.get('FLAGS', "0x1")
                    opcode	= (int(flags, 16) & 0xf)
                    
                    if method.startswith("websocket"):
                        message		= "[ %-15.15s | %s ] {0}\n" % (str(remote_addr),req.conn_id)
                        conn_ids	= [r.conn_id for r in trans.sessions_active.values()]
                        if opcode == trans.OP_CLOSE:
                            message	= message.format("Left chat")
                        elif method == "websocket_connect":
                            message	= message.format("Joined chat")
                        else:
                            message	= message.format(req.body)
                        conn.deliver_websocket(req.sender, conn_ids, message)
                        
                    elif method in ['get','post','put','delete']:
                        conn.reply_http(req, "<h1>HTTP is lame sauce, use WebSockets foo!</h1>")
                        
                    else:
                        log.warn("Dropping unrecognized method: %s", method)

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
