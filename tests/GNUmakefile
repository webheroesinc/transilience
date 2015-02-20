
.PHONY:		FORCE all run-% test-% prep-% pre-prep-%

all:
	@echo ""
	@echo "Running tests:"
	@echo ""
	@echo "	 run-main		-- Run py.test for matching glob (test_*.py)"
	@echo "	 run-slow-subscriber	-- Test that we can force slow subscriber to occur and then fix it"
	@echo ""

FORCE:

mg2_s		= ../var/run/mongrel2_server.pid
api_d		= ../var/run/api_handler.pid

$(mg2_s):
	make -s -C ../mongrel2 start-main
	@touch mongrel2.started
$(api_d):
	make -s -C ../handlers start-api
	@touch api.started

stop-mongrel2:
	make -s -C ../mongrel2 stop-main
	@rm -f mongrel2.started
stop-api:
	make -s -C ../handlers stop-api
	@rm -f api.started


pre-prep-slow-subscriber:
	@if [ -f $(api_d) ]; then			\
	    echo "[ error ] You must shutdown the currently running api docker (make stop-api)";\
	    exit 1;					\
	fi;
test-slow-subscriber:	prep-slow-subscriber $(mg2_s)
	docker run -d --name $@				\
		-v $$(pwd)/..:/host			\
		-w /host/tests/				\
		webheroes/handler			\
		py.test -v slow_subscriber_test.py
	sleep 3 && make $(api_d)

pre-prep-main:
prep-%:			pre-prep-%
	@docker rm test-$*		2> /dev/null	|| true
test-%:			prep-%
	docker run -d --name $@				\
		-v $$(pwd)/..:/host			\
		-w /host/tests/				\
		webheroes/handler			\
		py.test -v test_*.py
run-%:			test-%
	docker logs -f test-$*		2> /dev/null	|| true
	@nohup docker logs -f test-$*	> ../var/log/test-$*.log 2>&1 &
	@for f in $$(ls *.started 2> /dev/null); do	\
	    make stop-$${f%.started};			\
	done;
