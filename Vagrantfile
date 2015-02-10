# -*- mode: ruby -*-
# Download and configure a VMware instance of Debian 7 Jessie
# Configure it for Docker runtime and development of cpppo applications.
# Assumes that a jessie64 box has been added to vagrant.
#
# Instructions for creating a custom Vagrant Debian box for VMware or VirtualBox:
#  - http://www.skoblenick.com/vagrant/creating-a-custom-box-from-scratch/
#  
# Installing and using veewee to build and package a Vagrant Debian Jessie box:
#  - https://github.com/jedi4ever/veewee/blob/master/doc/installation.md
#  - https://github.com/Mayeu/vagrant-jessie-box
#  
# Docker-based configurations)
Vagrant.configure("2") do |config|
  config.vm.box				= "jessie64"
  config.vm.provision "shell" do |s|
    # The kernel may be different than the running kernel after the upgrade!  Ubuntu Raring requires
    # software-properties-common, Precise python-software-properties to supply apt-add-repository,
    # but these have a docker dpkg; Jessie now has a docker.io package (but executable is still
    # docker) The initiating Vagrantfile's directory (eg. ~/src/datasim/) is mounted on /vagrant/.
    s.inline 				= '				\
        make -C /vagrant vm-server-setup				\
        && echo "Login w/ vagrant ssh" || echo "VM setup failed"	\
    '
  end
  config.vm.synced_folder "~/.ssh", "/host_ssh"
  config.vm.network "public_network", :bridge => 'en0: Wi-Fi (AirPort)', :auto_config => false
  config.vm.provider "vmware_desktop" do |v|
    v.gui 				= true
    v.vmx["memsize"]			= "4096"
    v.vmx["numvcpus"]			= "4"
  end
  config.vm.provider "vmware_fusion" do |v|
    v.gui 				= true
    v.vmx["memsize"]			= "4096"
    v.vmx["numvcpus"]			= "4"
  end
  config.vm.provider "virtualbox" do |v|
    v.gui 				= true
    v.customize ["modifyvm", :id, "--memory", "4096"]
    v.customize ["modifyvm", :id, "--cpus", "2"]
  end
end
