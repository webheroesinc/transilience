
.PHONY:		FORCE all
.SILENT:	

all:
	@echo ""
	@echo "Running tests:"
	@echo ""
	@echo "	 test-suite-1	-- Run test suite 1"
	@echo ""

FORCE:

mg2_s		= ../var/run/mongrel2_server.pid
api_d		= ../var/run/api_handler.pid

$(mg2_s):
	make -C ../mongrel2 start-main
	touch mongrel2.started
$(api_d):
	make -C ../handlers start-api
	touch api.started

stop-mongrel2:
	make -C ../mongrel2 stop-main
	rm -f mongrel2.started
stop-api:
	make -C ../handlers stop-api
	rm -f api.started


test-suite-1:		$(mg2_s) $(api_d) .SILENT
	docker rm $@			2> /dev/null	|| true
	rm -f ../var/run/$@.pid		2> /dev/null	|| true
	docker run -d --name $@				\
		-v $$(pwd)/..:/host			\
		-w /host/tests/				\
		webheroes/handler			\
		py.test			> ../var/run/$@.pid
	docker logs -f $@
	nohup docker logs -f $@		> ../var/log/$@.log 2>&1 &
	for f in $$(ls *.started 2> /dev/null); do	\
	    make stop-$${f%.started};			\
	done;
