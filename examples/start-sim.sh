#!/bin/bash

set -e

if [ ! -d /tmp/aqua ]; then
	mkdir /tmp/aqua
fi

if [ ! -S /tmp/aqua/sim ]; then 
	echo " -|- Forward 127.0.0.1:8000<->/tmp/sim"
	socat UNIX-LISTEN:/tmp/aqua/sim,fork TCP4:127.0.0.1:8000&
else
	echo " -|- Simulator forwarder running "
fi

echo " -|- Starting interactive aqua simulator"
python -i ../sim/run.py -c $1 
