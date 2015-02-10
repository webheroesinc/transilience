#!/bin/bash

m2sh start -name ${1}

while [ -f var/run/mongrel2.pid ]; do
    sleep 1;
done
