
.PHONY:			FORCE all start-% stop kill log-rotate
.SILENT:		all	

all:
	echo ""
	echo "Managing python handlers:"
	echo ""
	echo "	 start-%	-- Start the Mongrel2 server that is named %"
	echo ""
	echo "	 stop-%		-- Stop the Mongrel2 server that is named %"
	echo ""

FORCE:

log-rotate:
	mv ../var/log/api_docker.log ../var/log/api_docker.log.1	|| true

start-api:		log-rotate
	docker rm api 2> /dev/null			|| true
	rm ../var/run/api_handler.pid 2> /dev/null	|| true
	docker run -d --name api -v $$(pwd)/..:/host -w /host/handlers webheroes/mongrel2 python api_handler.py > ../var/run/api_handler.pid
	nohup docker logs -f $$(cat ../var/run/api_handler.pid) > ../var/log/api_docker.log 2>&1 &
	@echo "Logging docker logs to ../var/log/api_docker.log"

../var/run/%.pid:
	@printf "[ error ] Docker '$*' is not running\n\n" && exit 1

stop-api:	../var/run/api_handler.pid
	docker kill --signal="TERM" $$(cat $<)	\
	&& rm $<
