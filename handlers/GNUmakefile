
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

api_dlog	= ../var/log/api_docker.log
api_dpid	= ../var/run/api_handler.pid

log-rotate:
	mv $(api_dlog) $(api_dlog).1	|| true

start-api:		log-rotate
	docker rm api	2> /dev/null	|| true
	rm $(api_dpid)	2> /dev/null	|| true
	docker run -d --name api			\
		-v $$(pwd)/..:/host			\
		-w /host/handlers			\
		webheroes/mongrel2			\
		python api_handler.py	> $(api_dpid)
	nohup docker logs -f $$(cat $(api_dpid)) > $(api_dlog) 2>&1 &
	@echo "Logging docker logs to $(api_dlog)"

../var/run/%.pid:
	@printf "[ error ] Docker '$*' is not running\n\n" && exit 1

stop-api:	$(api_dpid)
	docker kill --signal="TERM" $$(cat $(api_dpid))	\
	&& rm $(api_dpid)
