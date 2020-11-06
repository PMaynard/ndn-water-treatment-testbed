# NDN Water Treatment Testbed

A Named Data Networking and Modbus-TCP water treatment testbed. This code base is part of an upcoming academic paper.

# Software Overview

0. Vagrant
	- Creates and provisions a local virtual machine which can be used to run the testbed.
	- `vagrant up; vagrant ssh -- -X;`
	- `multitail /tmp/aqua/logs/{*nlsr,*nfd}.log` and `/vagrant/example/logs/*.log`
1. Simulator
	- Service running on a UNIX socket. Available for all mininet nodes.
	- Defines the Process control (e.g. A municipal water system).
2. Mininet
	- Brings up the network and nodes.
3. Node services
	- PLC
		- Registers with the simulator service (e.g Get or set simulator values)
		- Respond to network quires (e.g. Modbus-TCP or NDN)
	- HMI
		- Query PLC over network (e.g. Modbus-TCP or NDN)
		- Records the value and latency of the response from PLCs.
		
# Software Dependencies

	# MiniNDN - https://github.com/named-data/mini-ndn
	# ubuntu/xenial64 - 16.04
    add-apt-repository ppa:named-data/ppa
    apt-get update -y
    apt-get upgrade -y
    apt-get install -y tmux fping python2.7 python-pip mininet xterm openvswitch-testcontroller socat quagga multitail ndn-tools nfd nlsr
    pip install --upgrade pip
    pip install -r requirements.txt
    # Fix old name.
    cp /usr/bin/ovs-testcontroller /usr/bin/ovs-controller

# Run

Begin by starting the water process simulator, then as root, start either the Modbus-TCP or ICN network. Make sure to run these commands within `cd exmaples/` 

	[host]$ vagrant up --provision
	[host]$ vagrant ssh
	[vm]$ cd /vagrant/examples
	[vm]$ sh start-sim.sh municipal-water-system.yml
	[vm]# sudo python modbus-tcp.py 

or

	[vm]# minindn examples/ndn.conf --experiment=aqua-complex

Logs are stored at `/tmp/aqua/*.log.` A good tool to monitor these logs is `multitail`.

# Example

	$ sim-start.sh [YAML config]
	INFO:root:[e660148d][reservoir][reservoir1]: Initialized
	INFO:root:[0efd0900][valve][valve1]: Initialized
	INFO:root:[db91f04a][pump][pump1]: Initialized
	INFO:root:[1d81d76b][valve][valve2]: Initialized
	INFO:root:[f41bb0d9][tank][tank1]: Initialized
	INFO:root:[0efd0900][valve][valve1]: Added input <- [e660148d][reservoir][reservoir1]
	INFO:root:[e660148d][reservoir][reservoir1]: Added output -> [0efd0900][valve][valve1]
	INFO:root:[db91f04a][pump][pump1]: Added input <- [0efd0900][valve][valve1]
	INFO:root:[0efd0900][valve][valve1]: Added output -> [db91f04a][pump][pump1]
	INFO:root:[f41bb0d9][tank][tank1]: Added input <- [1d81d76b][valve][valve2]
	INFO:root:[1d81d76b][valve][valve2]: Added output -> [f41bb0d9][tank][tank1]
	INFO:root:[1d81d76b][valve][valve2]: Added input <- [db91f04a][pump][pump1]
	INFO:root:[db91f04a][pump][pump1]: Added output -> [1d81d76b][valve][valve2]
	INFO:root:[1d81d76b][valve][valve2]: Active
	INFO:root:[f41bb0d9][tank][tank1]: Active
	INFO:root:[0efd0900][valve][valve1]: Active
	INFO:root:[e660148d][reservoir][reservoir1]: Active
	INFO:root:[db91f04a][pump][pump1]: Active
	>>> sim.devices
	{'valve2': [1d81d76b][valve][valve2], 'tank1': [f41bb0d9][tank][tank1], 'valve1': [0efd0900][valve][valve1], 'reservoir1': [e660148d][reservoir][reservoir1], 'pump1': [db91f04a][pump][pump1]}
	>>> sim.settings
	{'speed': 1}
	>>> sim.devices['tank1'].volume
	79
	>>> sim.devices['pump1'].turn_off()
	>>> sim.devices['tank1'].volume
	103
	>>> sim.devices['tank1'].volume
	103
	>>> sim.pause()
	INFO:root:[dd153bbb][valve][valve2]: Inactive
	INFO:root:[16960a58][tank][tank1]: Inactive
	INFO:root:[d4d9302d][valve][valve1]: Inactive
	INFO:root:[a2f02e65][reservoir][reservoir1]: Inactive
	INFO:root:[f1afd77b][pump][pump1]: Inactive
	>>> sim.start()
	INFO:root:[dd153bbb][valve][valve2]: Active
	INFO:root:[16960a58][tank][tank1]: Active
	INFO:root:[d4d9302d][valve][valve1]: Active
	INFO:root:[a2f02e65][reservoir][reservoir1]: Active
	INFO:root:[f1afd77b][pump][pump1]: Active
	>>> sim.stop() # or ^C
	$


# TroubleShooting  

- **Exception: Error creating interface pair (hmi-eth0,s3-eth2): RTNETLINK answers: File exists**
- Delete any links that might remain from a previous experiment. 
	- ip link delete s{1,2,3}-eth{1,2,3}
- **Something is not quite right about background processes**
- Make sure you are running ubuntu/xenial64 16.04

## NDNPING

Return values:

- 2 Connection Refused - Can't talk to NFD.
- 1 NACK'ed can't find name - No Route
- 0 OK - PING Returned good.

## [optional] improve xterm readability  

Place the following in your host's `~/.Xresources` file to improve xterms font and colors.
To load the setting run `xrdb .Xresources`. 

	!Font and size
	XTerm.vt100.faceName: Liberation Mono:size=11 
	XTerm.vt100.font: 7x13

	! Dracula colour palette
	*.foreground: #F8F8F2
	*.background: #282A36
	*.color0:     #000000
	*.color8:     #4D4D4D
	*.color1:     #FF5555
	*.color9:     #FF6E67
	*.color2:     #50FA7B
	*.color10:    #5AF78E
	*.color3:     #F1FA8C
	*.color11:    #F4F99D
	*.color4:     #BD93F9
	*.color12:    #CAA9FA
	*.color5:     #FF79C6
	*.color13:    #FF92D0
	*.color6:     #8BE9FD
	*.color14:    #9AEDFE
	*.color7:     #BFBFBF
	*.color15:    #E6E6E6

# Thanks

This project expands on the water simulation testbed by Craig Koroscil. <http://github.com/sintax1>

# License

MIT License

Copyright (c) 2019 Peter Maynard

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
