

all:
	@echo ""
	@echo "Building docker container"
	@echo ""
	@echo "	 build-%		-- Will build the docker container at the location given in the %"
	@echo ""

FORCE:

mg2_transceiver		= webheroes/handler/mongrel2-transceiver

$(mg2_transceiver):	../mongrel2-transceiver/
	rsync -va $< $@

webheroes/handler:	$(mg2_transceiver) FORCE
	docker build -t $@ $@

# webheroes/%:		FORCE
# 	docker build -t $@ $@
