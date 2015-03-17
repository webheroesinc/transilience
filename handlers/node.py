
from mongrel2_transceiver	import Transceiver
from utils.discovery		import get_docker_ip
from utils			import logging

import signal, traceback
import zmq, decimal
import simplejson	as json
import MySQLdb		as mysqldb
import MySQLdb.cursors	as mysql_cursors

shutdown		= False

def term_signalled(*args):
    global shutdown
    log.debug("[ shutdown ] Shutdown has been signalled")
    shutdown		= True

def main(**args):
    global shutdown
    log.debug("Getting mg2 address")
    mg2_ip		= get_docker_ip('mg2')
    api_ip		= get_docker_ip('api')
    mysql_ip		= get_docker_ip('mysql')
    log.warn("Using address %s for mg2 connection", mg2_ip)
    log.warn("Using address %s for api connection", api_ip)
    log.warn("Using address %s for mysql connection", mysql_ip)

    CTX			= zmq.Context()
    sub			= CTX.socket(zmq.SUB)
    sub.connect('tcp://{0}:19999'.format(api_ip))
    sub.setsockopt(zmq.SUBSCRIBE, '')

    db			= mysqldb.connect( host		= mysql_ip,
                                           user		= "root",
                                           passwd	= "tesla",
                                           db		= "transilience",
                                           cursorclass	= mysql_cursors.DictCursor )
    curs		= db.cursor()
    
    with Transceiver('rune', pull_addr=(api_ip, 9999), pub_addr=(mg2_ip, 9998), log_level=logging.DEBUG) as trans:
        trans.add_incoming(sub)
        for sid,conn,req in trans.recv():
            try:
                if req is not None:
                    headers	= req.headers
                    method	= headers.get('METHOD', '').lower()
                    query	= headers.get('QUERY', {})
                    
                    if method == "websocket":
                        log.debug("Message: %s", req.body)
                        curs.execute("""select * from movies""")
                        movies	= curs.fetchall()
                        conn.reply_websocket(req, json.dumps(movies))
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
    log			= logging.getLogger('node1')
    log.setLevel(logging.DEBUG)
    
    log.debug("Registering SIGTERM interrupt")
    signal.signal( signal.SIGTERM, term_signalled)
    
    main()

