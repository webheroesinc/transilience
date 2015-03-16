
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

mg2_s		= ../var/run/mongrel2_server.pid
mg2_d		= ../var/run/mg2.pid
mg2_ip		= ../var/addr/mg2.ip
mg2_dlog	= ../var/log/mg2.log

mongrel2.conf:
	@printf "Create and configure a mongrel2.conf\n\
  (example: https://github.com/zedshaw/mongrel2/blob/master/examples/configs/multi_handler.conf)\n" && exit 1

config.sqlite:		mongrel2.conf
	docker run --name mg2_conf -p 80:80		\
		-v $$(pwd):/mg2				\
		-w /mg2					\
		webheroes/mongrel2			\
		m2sh load -db config.sqlite --config mongrel2.conf
	docker rm mg2_conf

start-%:		config.sqlite
	docker rm mg2	2> /dev/null	|| true
	rm -f $(mg2_s)	2> /dev/null	|| true
	docker run -d --name mg2 -p 80:80		\
		-v $$(pwd)/..:/host			\
		-w /host/mongrel2			\
		webheroes/mongrel2			\
		./start.sh $*		> $(mg2_d)
	docker inspect --format '{{ .NetworkSettings.IPAddress }}' mg2 > $(mg2_ip)
	nohup docker logs -f api	> $(mg2_dlog) 2>&1 &
	@echo "Logging docker logs to $(mg2_dlog)"

$(mg2_s):
	@printf "[ error ] Mongrel2 server is not running\n\n" && exit 1
$(mg2_d):
	@printf "[ error ] Docker is not running\n\n" && exit 1
$(mg2_ip):
	@printf "[ error ] Docker IP file does not exist\n\n" && exit 1

stop-%:			$(mg2_d)			\
			$(mg2_ip)
	docker exec $$(cat $(mg2_d)) m2sh stop -name $*	\
	&& rm $(mg2_d)					\
	&& rm $(mg2_ip)

join:
	docker exec -it mg2 bash
