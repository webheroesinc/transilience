
import sys, os
import transceiver
import logging

scriptname		= os.path.splitext( os.path.basename( sys.argv[0] ) )[0]
logging.basicConfig(
    filename		= '{0}.log'.format(scriptname),
    level		= logging.ERROR,
    datefmt		= '%Y-%m-%d %H:%M:%S',
    format		= '%(asctime)s.%(msecs).03d [ %(threadName)10.10s ] %(name)-15.15s : %(funcName)-15.15s %(levelname)-8.8s %(message)s',
)
