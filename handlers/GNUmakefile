
all:
	@echo ""
	@echo "Managing python handlers:"
	@echo ""
	@echo "	 start-%	-- Start the Mongrel2 server that is named %"
	@echo ""
	@echo "	 stop-%		-- Stop the Mongrel2 server that is named %"
	@echo ""

FORCE:

api_dlog	= ../var/log/api_docker.log
api_dpid	= ../var/run/api_handler.pid
api_ip		= ../var/addr/api.ip

node_dlog	= ../var/log/node_docker.log
node_dpid	= ../var/run/node_handler.pid
node_ip		= ../var/addr/node.ip

build-%:		FORCE
	make -C ../docker webheroes/$*

start-api:		build-handler
	docker kill	api	|| true
	docker rm	api	|| true
	docker run -d --name api			\
		-v $$(pwd)/..:/host			\
		-w /host/handlers			\
		webheroes/handler			\
		python api_handler.py	> $(api_dpid)
	docker inspect --format '{{ .NetworkSettings.IPAddress }}' api > $(api_ip)
	nohup docker logs -f api	> $(api_dlog) 2>&1 &
	@echo "Logging docker logs to $(api_dlog)"

start-node:		build-handler
	docker kill	node	|| true
	docker rm	node	|| true
	docker run -d --name node			\
		-v $$(pwd)/..:/host			\
		-w /host/handlers			\
		webheroes/handler			\
		python node.py		> $(node_dpid)
	docker inspect --format '{{ .NetworkSettings.IPAddress }}' node > $(node_ip)
	nohup docker logs -f node	> $(node_dlog) 2>&1 &
	@echo "Logging docker logs to $(node_dlog)"

../var/run/%.pid:
	@printf "[ error ] Docker '$*' is not running\n\n" && exit 1

stop-api:	$(api_dpid)
	docker kill --signal="TERM" api			\
	&& rm $(api_dpid)
stop-node:	$(node_dpid)
	docker kill --signal="TERM" node		\
	&& rm $(node_dpid)

restart-%:		stop-% start-%
	@echo "Restarted $* docker..."
