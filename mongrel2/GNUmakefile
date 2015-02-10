
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
	docker run -p 80:80 -v $$(pwd):/host webheroes/mongrel2 bash -c "cd host; m2sh load -db config.sqlite --config mongrel2.conf"

start-%:		config.sqlite
	docker run -d -p 80:80 -v $$(pwd):/host webheroes/mongrel2 bash -c "cd host; ./start.sh $*" > var/run/docker.pid

var/run/mongrel2.pid:
	@printf "Mongrel2 server is not running"
var/run/docker.pid:
	@printf "Docker is not running"

stop-%:			var/run/docker.pid		\
			var/run/mongrel2.pid
	docker exec $$(cat $<) bash -c "cd host; m2sh stop -name $*"		\
	&& docker rm $$(cat $<)							\
	&& rm $<
