# -*- mode: conf -*-

FROM		webheroes/mongrel2
MAINTAINER	Matthew Brisebois "matthew@webheroes.ca"

RUN		apt-get update #2015-03-17
RUN		apt-get -y install python-pip libmysqlclient-dev	\
		  && apt-get clean
RUN		pip install pytest psutil netifaces
RUN		pip install mysql-python simplejson

COPY		./mongrel2-transceiver	/tmp/mongrel2-transceiver
RUN		cd /tmp/mongrel2-transceiver; python setup.py install