# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/xenial64"
  config.vm.synced_folder "./", "/vagrant"
  config.vm.provision "shell", inline: <<-SHELL
    cd /vagrant
    add-apt-repository ppa:named-data/ppa
    apt-get update -y
    apt-get upgrade -y
    apt-get install -y tmux fping python2.7 python-pip mininet xterm openvswitch-testcontroller socat quagga multitail ndn-tools nfd nlsr
    pip install --upgrade pip
    pip install -r requirements.txt
    # Fix old name.
    cp /usr/bin/ovs-testcontroller /usr/bin/ovs-controller
  SHELL
end
