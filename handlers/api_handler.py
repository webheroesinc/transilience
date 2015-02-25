
from utils.transceiver	import Transceiver

import os, sys, time
import logging, traceback

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
    mg2_ip		= None
    with open("../var/addr/mg2.ip", 'r') as f:
        mg2_ip		= f.read().rstrip()
    logging.warn("Using address %s for mg2 connection", mg2_ip)

    api_transceiver	= Transceiver(pull_ip=mg2_ip, pub_ip=mg2_ip)
    
    for sid, req in api_transceiver.recv():
        try:
            if req is not None:
                headers		= req.headers
                method		= headers.get('METHOD', '').lower()
                query		= headers.get('QUERY', {})
                
                logging.debug("Request headers: %s", headers)
                if method == "json":
                    logging.debug("JSON body: %s", req.body)
                    
                elif method == "websocket":
                    logging.debug("Message: %s", req.body)
                    Transceiver.respond_websocket(req, "Making friends, after school!  Behind the bus, I'm breakin fools...")
                    
                elif method in ['get','post','put','delete']:
                    # this is where the node.py forward will be.  For now reply...
                    logging.info("[ temp ] Sending templorary reply")
                    Transceiver.respond_http(req, "Forwarding to node...(psych)")
                    
                else:
                    logging.debug("Unrecognized method: %s\n%s", method, req.body)
            else:
                pass
        except Exception, e:
            logging.error("[ error ] Handling request broke with error: %s", e)
            logging.debug("[ stacktrace ] %s", traceback.format_exc())

    
if __name__ == "__main__":
    setup_logging()
    main()
