
from mongrel2.handler import Connection

import os, sys, signal, time
import uuid, logging
import zmq

logging.basicConfig(filename='api_handler.log', level=logging.DEBUG)

shutdown_signalled	= False

def shutdown_request( signum, frame ):
    global shutdown_signalled
    logging.warn("[ terminating process ] Shutdown has been signalled")
    shutdown_signalled	= True

logging.debug("Registering SIGTERM interrupt")
signal.signal( signal.SIGTERM, shutdown_request )

logging.debug("Getting mg2 address")
web_addr	= os.environ.get('WEB_PORT', '').rsplit(':', 1)[0]
if not web_addr:
    logging.error("[ exiting ] No WEB_PORT environment variable")
    sys.exit()
logging.warn("Using address %s for mg2 connection", web_addr)

logging.debug("Setting up connection object")
conn		= Connection( sender_id=str(uuid.uuid1()),
                              sub_addr="{0}:9999".format(web_addr),
                              pub_addr="{0}:9998".format(web_addr) )

logging.debug("Setting up poller")
poller		= zmq.Poller()
poller.register(conn.reqs, zmq.POLLIN)

logging.debug("Entering infinite while")
while not shutdown_signalled:
    try:
        socks	= dict(poller.poll(50))
        if conn.reqs in socks and socks[conn.reqs] == zmq.POLLIN:
            req	= conn.recv()
            logging.debug("Request headers: %s", req.headers)
            conn.reply_http(req, "I'm so happy that this worked!")
    except Exception, e:
        logging.error("[ error ] Infinite loop broke with error: %s", e)

logging.debug("Exited infinite loop")
