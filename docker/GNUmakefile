

all:
	@echo ""
	@echo "Building docker container"
	@echo ""
	@echo "	 build-%		-- Will build the docker container at the location given in the %"
	@echo ""


webheroes/%:	FORCE
	docker build --no-cache -t $@ $@

FORCE:
