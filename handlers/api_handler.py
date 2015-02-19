
from mongrel2.handler import Connection

import os, sys, signal, time, threading
import uuid, logging
import zmq

shutdown_signalled	= False

def setup_logging():
    scriptname		= os.path.basename( sys.argv[0] )
    logging.basicConfig(
        filename	= '{0}.log'.format(scriptname),
        level		= logging.DEBUG,
        datefmt		= '%y-%m-%d %H:%M:%S',
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
    
    logging.debug("Entering infinite while")
    while not shutdown_signalled:
        try:
            socks	= dict(poller.poll(50))
            if conn.reqs in socks and socks[conn.reqs] == zmq.POLLIN:
                req	= conn.recv()
                headers	= req.headers
                logging.debug("Request headers: %s", headers)
                conn.reply_http(req, "I'm so happy that this worked!")
                logging.info("Sent reply to %s", headers['REMOTE_ADDR'])
        except Exception, e:
            logging.error("[ error ] Infinite loop broke with error: %s", e)
    
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
