
all:
	@echo ""
	@echo "Managing python handlers:"
	@echo ""
	@echo "	 start-%	-- Start the Mongrel2 server that is named %"
	@echo ""
	@echo "	 stop-%		-- Stop the Mongrel2 server that is named %"
	@echo ""

FORCE:

mysql_dlog	= ../var/log/mysql_docker.log
mysql_dpid	= ../var/run/mysql_handler.pid
mysql_ip	= ../var/addr/mysql.ip

start-mysql:
	docker kill	mysql	|| true
	docker rm	mysql	|| true
	docker run --name mysql				\
		-e MYSQL_ROOT_PASSWORD=tesla		\
		-v $$(pwd):/mysql			\
		-v $$(pwd)/databases:/var/lib/mysql	\
		-d mysql	> $(mysql_dpid)
	docker inspect --format '{{ .NetworkSettings.IPAddress }}' mysql > $(mysql_ip)
	nohup docker logs -f mysql	> $(mysql_dlog) 2>&1 &
	@echo "Logging docker logs to $(mysql_dlog)"
load-db:	$(mysql_dpid)
	docker exec mysql /mysql/load_db.sh tesla

init-mysql:	start-mysql load-db

../var/run/%.pid:
	@printf "[ error ] Docker '$*' is not running\n\n" && exit 1

stop-mysql:	$(mysql_dpid)
	docker stop mysql

remove-mysql:	stop-mysql
	docker rm mysql		|| true

restart-%:		stop-% start-%
	@echo "Restarted mysql docker..."
