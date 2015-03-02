
.PHONY:			FORCE all
SHELL		= /bin/bash
USERNAME	= "pitch"
USERPASS	= "WHpwec15"
USERHOME	= "/home/$(USERNAME)"

all:
	@echo ""
	@echo "Globally useful project command:"
	@echo ""
	@echo "	 ph-server-setup	-- Run this if you are setting up a physical server to:"
	@echo "				     o Run server-setup"
	@echo "				     o Run .gitconfig setup"
	@echo ""
	@echo "	 vm-server-setup	-- Run this if you are setting up a virtual server to:"
	@echo "				     o Run server-setup"
	@echo "				     o Copy host ssh key into users authorized_keys file"
	@echo ""
	@echo "				server-setup (configuration steps):"
	@echo "				     o Create project user"
	@echo "				     o Install common apt packages"
	@echo "				     o Upgrade linux headers"
	@echo "				     o Add created user to docker group"
	@echo ""
	@echo "	 list-files		-- find all files that are not .vagrant or .git files"
	@echo "	 list-dirty-files	-- from list-files result, find files with dirty extensions (*~, *.pid, *.log)"
	@echo "	 load-scripts		-- Add project helper scripts to /usr/bin"
	@echo "	 remove-containers	-- Get all container IDs and docker rm them"
	@echo ""

FORCE:

$(USERHOME):
	adduser --quiet --disabled-password --gecos $(USERNAME) $(USERNAME)
	echo $(USERNAME):$(USERPASS) | chpasswd
	addgroup $(USERNAME) sudo
	addgroup $(USERNAME) staff

$(USERHOME)/.ssh:	$(USERHOME)
	sudo -u $(USERNAME) bash -c "					\
	    mkdir -p $@							\
	 && chmod 0700 $@						\
"

%/.gitconfig:
	@if [ ! -f $@ ]; then echo "Copy in your personal ~/.gitconfig, or enter:"; fi
	@if ! grep -q 'autosetupmerge[[:space:]=]\+true' $@; then git config --global branch.autosetupmerge true; fi
	@if ! grep -q 'name[[:space:]=]\+'   $@; then read -p "Your full name: " && git config --global user.name   "$$REPLY"; fi
	@if ! grep -q 'email[[:space:]=]\+'  $@; then read -p "Your email: "     && git config --global user.email  "$$REPLY"; fi
	@if ! grep -q 'editor[[:space:]=]\+' $@; then read -p "Your editor: "    && git config --global core.editor "$$REPLY"; fi

update-apt-sources:
	@echo -e "deb	ftp://ftp.ca.debian.org/debian	jessie		main contrib non-free"		>  /etc/apt/sources.list
	@echo -e "deb	ftp://ftp.ca.debian.org/debian	jessie-updates	main contrib non-free"		>> /etc/apt/sources.list
	@echo -e "deb	http://security.debian.org/	jessie/updates	main contrib non-free\n"	>> /etc/apt/sources.list

server-setup:		update-apt-sources $(USERHOME)/.ssh
	DEBIAN_FRONTEND=noninteractive						\
	apt-get update								\
	&& apt-get -u -y dist-upgrade						\
	&& apt-get install -y							\
	       apt-show-versions python-pip python-dev				\
	       lxc wget bsdtar curl git						\
	       emacs24-nox emacs24-el screen					\
	       multitail aspell zip docker.io					\
	&& apt-get install -y							\
	       $$( apt-show-versions -a						\
		    | sed -ne 's/^linux-image-\(\w\+\):\w*[[:space:]].*installed$$/linux-headers-\1/p' ) \
	&& echo "Installing docker utilities..."				\
	&& addgroup $(USERNAME) docker						\

ph-server-setup:	server-setup $(USERHOME)/.gitconfig
	@echo "Done server setup..."

vm-server-setup:	server-setup
	rsync --chown=$(USERNAME):$(USERNAME) -va /host_ssh/id_*sa* $(USERHOME)/.ssh
	@sudo -u $(USERNAME) bash -c "						\
            cat $(USERHOME)/.ssh/id_*sa.pub > $(USERHOME)/.ssh/authorized_keys	\
         && chmod 0600 $(USERHOME)/.ssh/authorized_keys				\
         && mkdir -p ~/src							\
        "
	@echo "Run 'make $(USERHOME)/.gitconfig' to set up git config"

login:
	@printf "Waiting for vagrant IP address... ";				\
	if ip=$$( config=$$(vagrant ssh-config 2> /dev/null | grep HostName)	\
		&& ip=$${config##*HostName }					\
		&& echo $$ip ); then						\
	    port=$$( config=$$(vagrant ssh-config 2> /dev/null | grep Port)	\
		&& port=$${config##*Port }					\
		&& echo $$port );						\
	    printf "\n  ssh -p $$port -tC $(USERNAME)@$$ip\n";			\
	    ssh -p $$port -tC $(USERNAME)@$$ip;					\
	else									\
	    printf "[ failed ]\n\
  Could not determine vagrant ip\n\
  - checking machine status ";							\
	    status=$$( status=$$(vagrant status | grep default)			\
		       && status=$${status#default }				\
		       && echo $${status% *} );					\
	    if [ "$$status" != "running" ]; then				\
		printf "[ $$status ]\n\
  Error: machine is not running\n";						\
	    fi;									\
	fi;

list-files:
	find . -type d \( -path ./.vagrant -o -path ./.git \) -prune -o -print

list-dirty-files:
	@find . -type d \( -path ./.vagrant -o -path ./.git \) -prune -o \( -name '*~' -o -name '*.log' -o -name '*.pid' \) -print

/usr/bin/docker-ip:		usr/bin/docker-ip
	sudo rsync -va --chmod="0755" usr/bin/docker-ip $@

load-scripts:		/usr/bin/docker-ip

start:
	make -C ./mongrel2 start-main	|| true
	make -C ./handlers start-api	|| true

stop-containers:
	make -C ./mongrel2 stop-main	|| true
	make -C ./handlers stop-api	|| true

remove-containers:
	docker rm $$(docker ps -aq)

stop:		stop-containers remove-containers

interactive:
	docker run -it -v $$(pwd):/host -w /host webheroes/handler bash

mongrel2-transceiver/documentation.zip:		mongrel2-transceiver/README.html
	cd mongrel2-transceiver;		\
	cp README.html index.html;		\
	zip documentation.zip index.html;

upload-mongrel2-transceiver:
	cd mongrel2-transceiver; python setup.py sdist upload
	cd mongrel2-transceiver; python setup.py sdist upload -r pypi-test
