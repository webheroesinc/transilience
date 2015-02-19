#!/bin/bash

m2sh start -name ${1}

# Wait until mongrel2 has started up
while ! [ -f /host/var/run/mongrel2_server.pid ]; do
    sleep 1;
done

# Mongrel2 will remove it's PID when it has been shutdown.  This loop
# will detect that Mongrel2 has removed its PID file and exit the
# bash.
while [ -f /host/var/run/mongrel2_server.pid ]; do
    sleep 1;
done
