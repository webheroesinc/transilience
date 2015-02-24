
all:
	@echo ""
	@echo "Managing python handlers:"
	@echo ""
	@echo "	 start-%	-- Start the Mongrel2 server that is named %"
	@echo ""
	@echo "	 stop-%		-- Stop the Mongrel2 server that is named %"
	@echo ""

api_dlog	= ../var/log/api_docker.log
api_dpid	= ../var/run/api_handler.pid
api_ip		= ../var/addr/api.ip

start-api:
	docker rm api	2> /dev/null	|| true
	docker run -d --name api			\
		-v $$(pwd)/..:/host			\
		-w /host/handlers			\
		webheroes/mongrel2			\
		python api_handler.py	> $(api_dpid)
	docker inspect --format '{{ .NetworkSettings.IPAddress }}' api > $(api_ip)
	nohup docker logs -f api	> $(api_dlog) 2>&1 &
	@echo "Logging docker logs to $(api_dlog)"

../var/run/%.pid:
	@printf "[ error ] Docker '$*' is not running\n\n" && exit 1

stop-api:	$(api_dpid)
	docker kill --signal="TERM" api			\
	&& rm $(api_dpid)

restart-%:		stop-% start-%
	@echo "Restarted api docker..."
