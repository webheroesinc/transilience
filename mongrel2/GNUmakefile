
.PHONY:			FORCE all

all:
	@echo ""
	@echo "Managing mongrel2 server:"
	@echo ""
	@echo "	 start-%	-- Start the Mongrel2 server that is named %"
	@echo ""
	@echo "	 stop-%		-- Stop the Mongrel2 server that is named %"
	@echo ""

FORCE:

mongrel2.conf:
	@printf "Create and configure a mongrel2.conf\n\
  (example: https://github.com/zedshaw/mongrel2/blob/master/examples/configs/multi_handler.conf)\n" && exit 1

config.sqlite:		mongrel2.conf
	docker run --name mg2_conf -p 80:80 -v $$(pwd):/mg2 -w /mg2 webheroes/mongrel2 m2sh load -db config.sqlite --config mongrel2.conf
	docker rm mg2_conf

start-%:		config.sqlite
	docker rm mg2 2> /dev/null				|| true
	rm -f ../var/run/mongrel2_server.pid 2> /dev/null	|| true
	docker run -d --name mg2 -p 80:80 -v $$(pwd)/..:/host -v $$(pwd):/mg2 -w /mg2 webheroes/mongrel2 ./start.sh $* > ../var/run/mg2.pid
	docker inspect --format '{{ .NetworkSettings.IPAddress }}' mg2 > ../var/addr/mg2.ip

../var/run/mongrel2_server.pid:
	@printf "[ error ] Mongrel2 server is not running\n\n" && exit 1
../var/run/mg2.pid:
	@printf "[ error ] Docker is not running\n\n" && exit 1
../var/addr/mg2.ip:
	@printf "[ error ] Docker IP file does not exist\n\n" && exit 1

stop-%:			../var/run/mg2.pid		\
			../var/addr/mg2.ip		\
			../var/run/mongrel2_server.pid
	docker exec $$(cat $<) m2sh stop -name $*	\
	&& rm $<					\
	&& rm ../var/addr/mg2.ip

join:
	docker exec -it mg2 bash
