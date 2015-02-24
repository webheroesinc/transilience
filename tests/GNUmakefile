
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
run-slow-subscriber:	prep-slow-subscriber $(mg2_s)
	docker run -d --name $@				\
		-v $$(pwd)/..:/host			\
		-w /host/tests/				\
		webheroes/handler			\
		py.test -v slow_subscriber_test.py
	sleep 3 && make $(api_d)

run-api-handler:	prep-api-handler $(mg2_s) $(api_d)
	docker run -d --name $@				\
		-v $$(pwd)/..:/host			\
		-w /host/tests/				\
		webheroes/handler			\
		py.test -v test_api_handler.py

pre-prep-%:
	@echo "Prepping for test $*..."
prep-%:			pre-prep-%
	@docker rm run-$*		2> /dev/null	|| true
run-%:			prep-%
	docker run -d --name $@				\
		-v $$(pwd)/..:/host			\
		-w /host/tests/				\
		webheroes/handler			\
		py.test -v test_mongrel2.py
test-%:			run-%
	docker logs -f run-$*		2> /dev/null	|| true
	@nohup docker logs -f run-$*	> ../var/log/run-$*.log 2>&1 &
	@for f in $$(ls *.started 2> /dev/null); do	\
	    echo "Running: make stop-$${f%.started}";	\
	    make stop-$${f%.started};			\
	done;
