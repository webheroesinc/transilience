# -*- mode: conf -*-

FROM		webheroes/mongrel2
MAINTAINER	Matthew Brisebois "matthew@webheroes.ca"

RUN		apt-get update
RUN		apt-get -y install python-pip		\
		  && apt-get clean
RUN		pip install mongrel2-transceiver
