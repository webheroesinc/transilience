# -*- mode: ruby -*-
Vagrant.configure("2") do |config|
  config.vm.box				= "jessie64"
  config.vm.provision "shell" do |s|
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
