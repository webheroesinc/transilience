#!/bin/bash

# Try connecting 10 times
for i in $(seq 30); do
    echo "$i: Trying to connect...";
    mysql -uroot -p${1} < /mysql/build.db 2> /dev/null;
    if [[ $? == 0 ]]; then
	break;
    else
	sleep 1;
    fi;
done;
