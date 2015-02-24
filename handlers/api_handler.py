
from mongrel2.handler import Connection

import os, sys, signal, time
import uuid, logging, traceback
import zmq

shutdown_signalled	= False
timer			= time.time

def setup_logging():
    scriptname		= os.path.basename( sys.argv[0] )
    logging.basicConfig(
        filename	= '{0}.log'.format(scriptname),
        level		= logging.DEBUG,
        datefmt		= '%Y-%m-%d %H:%M:%S',
        format		= '%(asctime)s.%(msecs).03d %(threadName)10.10s %(name)-15.15s %(funcName)-15.15s %(levelname)-8.8s %(message)s',
    )

    
def main(**args):
    logging.debug("Getting mg2 address")
    web_addr		= None
    with open("../var/addr/mg2.ip", 'r') as f:
        web_addr	= f.read().rstrip()
    if not web_addr:
        logging.error("[ exiting ] Could not determine Mongrel2 server IP, ../var/addr/mg2.ip not found")
        sys.exit()
    logging.warn("Using address %s for mg2 connection", web_addr)

    logging.debug("Setting up connection object on pull:tcp://{0}:9999 and pub:tcp://{0}:9998".format(web_addr))
    conn		= Connection( sender_id=str(uuid.uuid1()),
                                  sub_addr="tcp://{0}:9999".format(web_addr),
                                  pub_addr="tcp://{0}:9998".format(web_addr) )
    
    logging.debug("Setting up poller")
    poller		= zmq.Poller()
    poller.register(conn.reqs, zmq.POLLIN)

    OP_TEXT		= 0x1
    OP_BINARY		= 0x2
    OP_CLOSE		= 0x8
    OP_PING		= 0x9
    OP_PONG		= 0xA

    sessions_active	= {}
    sessions_ponged	= {}
    ping_timeout	= 30
    session_timeout	= timer() + 30
    
    logging.debug("Entering infinite while")
    while not shutdown_signalled:
        try:
            now		= timer()

            if now >= session_timeout:
                sessions_active	= sessions_ponged
                sessions_ponged	= {}
                session_timeout	= now + ping_timeout
                logging.debug("Reset session_timeout to: %s", session_timeout)
                for sid,req in sessions_active.items():
                    logging.debug("Sending PING to session ID: %s", sid)
                    conn.reply_websocket(req, "", OP_PING)
            
            socks	= dict(poller.poll(50))
            if conn.reqs in socks and socks[conn.reqs] == zmq.POLLIN:
                now		= timer()
                req		= conn.recv()
                sid		= (req.sender,req.conn_id)
                headers		= req.headers
                method		= headers.get('METHOD', '').lower()
                flags		= headers.get('FLAGS')
                opcode		= OP_TEXT if flags is None else (int(flags, 16) & 0xf)

                if opcode != OP_TEXT:
                    logging.info("Processing opcode: %s", hex(opcode))
                    if opcode	== OP_PONG:
                        sessions_ponged[sid]	= req
                    elif opcode	== OP_PING:
                        conn.reply_websocket(req, req.body, OP_PONG)
                    elif opcode	== OP_CLOSE:
                        sessions_active.pop( sid, None )
                        sessions_ponged.pop( sid, None )
                        conn.reply_websocket(req, "", OP_CLOSE)
                    elif opcode	== OP_BINARY:
                        pass # What the hell do I do with binary?
                    continue

                logging.debug("Request headers: %s", headers)
                if method == "json":
                    logging.debug("JSON body: %s", req.body)
                elif method == "websocket":
                    logging.debug("Message: %s", req.body)
                    conn.reply_websocket(req, "Making friends, after school!  Behind the bus, I'm breakin fools...")
                elif method == "websocket_handshake":
                    sessions_active[sid]	= req
                    sessions_ponged[sid]	= req
                    conn.reply(req,
                               '\r\n'.join([
                                   "HTTP/1.1 101 Switching Protocols",
                                   "Upgrade: websocket",
                                   "Connection: Upgrade",
                                   "Sec-WebSocket-Accept: %s\r\n\r\n"]) % req.body)
                elif method in ['get','post','put','delete']:
                    conn.reply_http(req, "b5b44d95-2e33-4af9-95fe-1cade9cd86ef")
                    logging.info("Sent reply to %s", headers.get('REMOTE_ADDR'))
                else:
                    logging.debug("Unrecognized method: %s\n%s", method, req.body)
        except zmq.ZMQError:
            if str(e) == "Interrupted system call":
                pass
            else:
                logging.error("[ error ] Infinite loop broke with error: %s", e)
                logging.debug("[ stacktrace ] %s", traceback.format_exc())
        except Exception, e:
            logging.error("[ error ] Infinite loop broke with error: %s", e)
            logging.debug("[ stacktrace ] %s", traceback.format_exc())
    
    logging.debug("Exited infinite loop")

    
if __name__ == "__main__":
    setup_logging()

    def shutdown_request( signum, frame ):
        global shutdown_signalled
        logging.warn("[ terminating process ] Shutdown has been signalled")
        shutdown_signalled	= True

    logging.debug("Registering SIGTERM interrupt")
    signal.signal( signal.SIGTERM, shutdown_request )
    
    main()
