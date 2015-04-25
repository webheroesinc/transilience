# -*- mode: conf -*-

FROM		webheroes/mongrel2
MAINTAINER	Matthew Brisebois "matthew@webheroes.ca"

RUN		apt-get update
RUN		apt-get -y install python-pip		\
		  && apt-get clean
#RUN		pip install mongrel2-transceiver

COPY            ./mongrel2-transceiver  /tmp/mongrel2-transceiver
RUN             cd /tmp/mongrel2-transceiver; python setup.py install