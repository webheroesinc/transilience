
.PHONY:			FORCE all start-% stop kill
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

start-api:
	docker run -d --name api --link mg2:web -v $$(pwd):/host -w /host webheroes/mongrel2 python api_handler.py > api_handler.pid
	nohup docker logs -f $$(cat api_handler.pid) > api_docker.log 2>&1 &
	@echo "Logging docker logs to api_docker.log"

%.pid:
	@printf "[ error ] Docker '$*' is not running\n\n" && exit 1

stop-api:	api_handler.pid
	docker kill --signal="TERM" $$(cat $<)	\
	&& rm $<
