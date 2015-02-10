# -*- mode: conf -*-

FROM		cpppo/base
MAINTAINER	Matthew Brisebois "matthew@webheroes.ca"

RUN		apt-get update
RUN		apt-get -y install git libtool libtool-bin autoconf	\
			automake python-dev uuid-dev			\
			sqlite3 libsqlite3-dev build-essential		\
		  && apt-get clean
RUN		git clone --branch master				\
			https://github.com/zeromq/zeromq4-x.git		\
			src/zeromq4-x					\
		  && cd src/zeromq4-x					\
		  && ./autogen.sh					\
		  && ./configure					\
		  && make V=1						\
		  && make install					\
		  && ldconfig						\
		  && cd / && rm -rf src/zeromq4-x
RUN		git clone --branch 0.18					\
			https://github.com/cython/cython.git		\
			src/cython					\
		  && cd src/cython					\
		  && python setup.py install				\
		  && cd / && rm -rf src/cython
RUN		git clone --branch v14.1.1				\
			https://github.com/zeromq/pyzmq.git		\
			src/pyzmq					\
		  && cd src/pyzmq					\
		  && python setup.py configure --zmq=/usr/local		\
		  && python setup.py install				\
		  && cd / && rm -rf src/pyzmq
RUN		git clone --branch fix/polarssl				\
			https://github.com/pjkundert/mongrel2.git	\
			src/mongrel2					\
		  && cd src/mongrel2					\
		  && sed -i -e 's/url = git:/url = http:/' .gitmodules	\
		  && make all install					\
		  && cd examples/python					\
		  && python setup.py install				\
		  && cd / && rm -rf src/mongrel2

EXPOSE		80
