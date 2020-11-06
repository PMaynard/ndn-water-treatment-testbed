#!/usr/bin/python

from mininet.net import Mininet
from mininet.topo import Topo
from mininet.node import Controller, RemoteController, OVSController
from mininet.node import CPULimitedHost, Host, Node
from mininet.node import OVSKernelSwitch, UserSwitch
from mininet.node import IVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink, Intf
from subprocess import call

import os, time

# Make sure a /run/quagga exists and has the permissions of 'chown quagga:quagga' and 'chmod ug+rw' (TODO: Automate)
# Same goes for the config file and log file.

class LinuxRouter( Node ):
	"A Node with IP forwarding enabled."

	def config( self, **params ):
		super( LinuxRouter, self).config( **params )
		
		self.password = "123"
		self.enable_password = "en"

		self.ospfd_networks = ""
		self.ospfd_interfaces = ""
		self.ospfd_log_file = "log/tcp-{0}-ospfd.log".format(self.name)
		self.ospfd_conf_file = "conf/tcp-{0}-ospfd.conf".format(self.name)

		self.zebra_interfaces = ""
		self.zebra_log_file = "log/tcp-{0}-zebra.log".format(self.name)
		self.zebra_conf_file = "conf/tcp-{0}-zebra.conf".format(self.name)

		# Parse parameters
		for key, val in params.items():

			if key == "ip": 
				self.ospfd_router_id = val.split('/')[0]

			if key == "ospfd_networks":
				for n in val:
					self.ospfd_networks = "{}  network {} area {}\n".format(self.ospfd_networks, n, 0)

		# Get interface settigns.
		for i in self.intfList():
			# Ignore any which are not set.
			if not self.IP(i):
				continue

			self.zebra_interfaces = "{0}\ninterface {1}\n   ip address {2}/24\n".format(self.zebra_interfaces, i, self.IP(i))
			self.ospfd_interfaces = "{0}\ninterface {1}\n".format(self.ospfd_interfaces, i)

		# Create the zebra config.
		res = """
! -*- zebra -*-
hostname {0}
password {1}
enable password {2}

interface lo
   ip address 127.0.0.1/8
{3}

log file /vagrant/examples/{4}
EOF
""".format(self.name, self.password, self.enable_password, self.zebra_interfaces, self.zebra_log_file)
		# print res

		self.cmd( 'cat > {1} <<EOF\n{0}'.format(res, self.zebra_conf_file) )
		self.waitOutput()

		os.system( 'sudo touch ' + self.zebra_log_file)
		os.system( 'sudo chown quagga:quagga {} {}'.format(self.zebra_conf_file, self.zebra_log_file))
		os.system( 'sudo chmod ug+rw {} {}'.format(self.zebra_conf_file, self.zebra_log_file))

		# Create the ospfd config.
		res = """hostname {0}
password {1}
enable password {2}

{6}

router ospf
  ospf router-id {3}
  redistribute connected
{4}
debug ospf event
log file /vagrant/examples/{5}
EOF
""".format(self.name, self.password, self.enable_password, self.ospfd_router_id, self.ospfd_networks, self.ospfd_log_file, self.ospfd_interfaces)
		
		# print res
		self.cmd( 'cat > {1} <<EOF\n{0}'.format(res, self.ospfd_conf_file) )
		self.waitOutput()

		os.system( 'sudo touch ' + self.ospfd_log_file)
		os.system( 'sudo chown quagga:quagga {} {}'.format(self.ospfd_conf_file, self.ospfd_log_file))
		os.system( 'sudo chmod ug+rw {} {}'.format(self.ospfd_conf_file, self.ospfd_log_file))

		# Otherwise they will not run.
		os.system( 'sudo mkdir /run/quagga' )
		os.system( 'sudo chown quagga:quagga /run/quagga')

		# Enable forwarding on the router
		self.cmd( 'sysctl -w net.ipv4.ip_forward=1' )

	def terminate( self ):
		self.cmd( 'sysctl net.ipv4.ip_forward=0' )
		os.system( 'sudo rm {} {}'.format(self.ospfd_conf_file, self.zebra_conf_file))
		os.system( 'pkill zebra' ) 
		os.system( 'pkill ospfd' ) 
		os.system( 'sudo rm /run/quagga/tcp-{0}-zebra.pid'.format(self.name))
		os.system( 'sudo rm /run/quagga/tcp-{0}-ospfd.pid'.format(self.name))
		super( LinuxRouter, self ).terminate()

class NetworkTopo( Topo ):
	"A LinuxRouter connecting three IP subnets"

	def build( self, **_opts ): 
		info( '*** Add switches\n')
		s1 = self.addSwitch('s1', cls=OVSKernelSwitch, failMode='standalone')
		s2 = self.addSwitch('s2', cls=OVSKernelSwitch, failMode='standalone')
		s3 = self.addSwitch('s3', cls=OVSKernelSwitch, failMode='standalone')
		
		info( '*** Add routers\n')    
		r6 = self.addNode('r6', cls=LinuxRouter, ip='10.6.0.254/24', ospfd_networks=['10.10.3.0/24', '10.10.1.0/24', '10.6.0.0/24'])
		r7 = self.addNode('r7', cls=LinuxRouter, ip='10.7.0.254/24', ospfd_networks=['10.10.2.0/24', '10.10.3.0/24', '10.7.0.0/24'])
		r8 = self.addNode('r8', cls=LinuxRouter, ip='10.8.0.254/24', ospfd_networks=['10.10.1.0/24', '10.10.2.0/24', '10.8.0.0/24'])

		info( '*** Add hosts\n')
		plc1 = self.addHost('plc1', cls=Host, ip='10.6.0.1/24', defaultRoute='via 10.6.0.254')
		plc2 = self.addHost('plc2', cls=Host, ip='10.6.0.2/24', defaultRoute='via 10.6.0.254')
		
		plc3 = self.addHost('plc3', cls=Host, ip='10.7.0.3/24', defaultRoute='via 10.7.0.254')
		plc4 = self.addHost('plc4', cls=Host, ip='10.7.0.4/24', defaultRoute='via 10.7.0.254')

		hmi = self.addHost('hmi', cls=Host, ip='10.8.0.1/24', defaultRoute='via 10.8.0.254')

		info( '*** Add links\n')
		for h, s in [ (plc1, s1), (plc2, s1), (plc3, s2), (plc4, s2), (s1, r6), (s2, r7), (r8, s3), (hmi, s3) ]:
			self.addLink( h, s)

		# Need to setup some IP address for the routes 'internal' network.

		# 10 Mbps, 5ms delay, 2% loss, 1000 packet queue
		# self.addLink( host, switch, bw=10, delay='5ms', loss=2, max_queue_size=1000, use_htb=True )
		optz = []
		for key, val in _opts.items():
			if key == "mode":
				if val == "normal" or val.startswith("x"):
					self.addLink(r6, r8, intfName1='r6-eth1', params1={ 'ip' : '10.10.1.10/24'}, intfName2='r8-eth1', params2={ 'ip' : '10.10.1.11/24'})
					self.addLink(r8, r7, intfName1='r8-eth2', params1={ 'ip' : '10.10.2.12/24'}, intfName2='r7-eth2', params2={ 'ip' : '10.10.2.13/24'})
					self.addLink(r7, r6, intfName1='r7-eth1', params1={ 'ip' : '10.10.3.14/24'}, intfName2='r6-eth2', params2={ 'ip' : '10.10.3.15/24'})
				if val == "lossy20":
					self.addLink(r6, r8, intfName1='r6-eth1', params1={ 'ip' : '10.10.1.10/24'}, intfName2='r8-eth1', params2={ 'ip' : '10.10.1.11/24'}, loss=20)
					self.addLink(r8, r7, intfName1='r8-eth2', params1={ 'ip' : '10.10.2.12/24'}, intfName2='r7-eth2', params2={ 'ip' : '10.10.2.13/24'}, loss=20)
					self.addLink(r7, r6, intfName1='r7-eth1', params1={ 'ip' : '10.10.3.14/24'}, intfName2='r6-eth2', params2={ 'ip' : '10.10.3.15/24'}, loss=20)
				if val == "lossy40":
					self.addLink(r6, r8, intfName1='r6-eth1', params1={ 'ip' : '10.10.1.10/24'}, intfName2='r8-eth1', params2={ 'ip' : '10.10.1.11/24'}, loss=40)
					self.addLink(r8, r7, intfName1='r8-eth2', params1={ 'ip' : '10.10.2.12/24'}, intfName2='r7-eth2', params2={ 'ip' : '10.10.2.13/24'}, loss=40)
					self.addLink(r7, r6, intfName1='r7-eth1', params1={ 'ip' : '10.10.3.14/24'}, intfName2='r6-eth2', params2={ 'ip' : '10.10.3.15/24'}, loss=40)
				if val == "lossy70":
					self.addLink(r6, r8, intfName1='r6-eth1', params1={ 'ip' : '10.10.1.10/24'}, intfName2='r8-eth1', params2={ 'ip' : '10.10.1.11/24'}, loss=70)
					self.addLink(r8, r7, intfName1='r8-eth2', params1={ 'ip' : '10.10.2.12/24'}, intfName2='r7-eth2', params2={ 'ip' : '10.10.2.13/24'}, loss=70)
					self.addLink(r7, r6, intfName1='r7-eth1', params1={ 'ip' : '10.10.3.14/24'}, intfName2='r6-eth2', params2={ 'ip' : '10.10.3.15/24'}, loss=70)
def run(mode):
	topo = NetworkTopo(mode=mode)
	net = Mininet( topo=topo, controller = OVSController)
	net.start()
	info( '*** Start Routing Services\n')
	for r in net.hosts:
		if str(r).startswith('r'):
			r.cmd("/usr/lib/quagga/zebra -f conf/tcp-{0}-zebra.conf -d -i /run/quagga/tcp-{0}-zebra.pid -z /run/quagga/zebra-{0}.sock -A 127.0.0.1 > log/tcp-{0}-zebra-stdout.log 2>&1".format(r))
			r.cmd("/usr/lib/quagga/ospfd -f conf/tcp-{0}-ospfd.conf -d -i /run/quagga/tcp-{0}-ospfd.pid -z /run/quagga/zebra-{0}.sock > log/tcp-{0}-ospfd-stdout.log 2>&1".format(r))
	
	# info( '*** Wait 60s for routing\n')
        time.sleep(60)

	info( '*** Start PLCs \n')
	for host in net.hosts:
		host_str = str(host).lower()

		if host_str.startswith("plc"):
			host.cmd( 'socat TCP4-LISTEN:8000,fork,reuseaddr UNIX-CONNECT:/tmp/aqua/sim &' )
			res_socat = host.cmd('printf $!')
			host.cmd( 'python /vagrant/tcp/plc/scadasim_plc/plc.py {0} > log/tcp-{0}-stdout.log 2> log/tcp-{0}-stderr.log  &'.format(host_str) )

			print "Host '{}' SOCAT PID '{}' PLC PID '{}'".format(host_str, res_socat, host.cmd('printf $!'))

		if host_str.startswith("hmi"):
			host.cmd( 'python /vagrant/tcp/hmi/main.py {1} > log/tcp-{0}-stdout.log 2> log/tcp-{0}-stderr.log  &'.format(host_str, mode) )
			print "Host '{}' HMI PID '{}'".format(host_str, host.cmd('printf $!'))
	
	info( '*** Running experiment for 5min\n')
	try:
                # Hack: this fixes the bit that stops tc from setting a delay
                # for r in net.hosts:
                #     if str(r).startswith('r'):
                #         if mode == "delay35": 
                #             r.cmd("tc qdisc add dev {0}-eth0 root netem gap 5 delay 15ms ".format(r))
                #             r.cmd("tc qdisc add dev {0}-eth1 root netem gap 5 delay 15ms ".format(r))
                #             r.cmd("tc qdisc add dev {0}-eth2 root netem gap 5 delay 15ms ".format(r))
                #         if mode == "delay15":
                #             r.cmd("tc qdisc add dev {0}-eth0 root netem gap 5 delay 10ms ".format(r))
                #             r.cmd("tc qdisc add dev {0}-eth1 root netem gap 5 delay 10ms ".format(r))
                #             r.cmd("tc qdisc add dev {0}-eth2 root netem gap 5 delay 10ms ".format(r))
                #         if mode == "delay5":
                #             r.cmd("tc qdisc add dev {0}-eth0 root netem corrupt 5% ".format(r))
                #             r.cmd("tc qdisc add dev {0}-eth1 root netem corrupt 5% ".format(r))
                #             r.cmd("tc qdisc add dev {0}-eth2 root netem corrupt 5% ".format(r))
                CLI( net )
        	# time.sleep(60)
        except:
			pass
	finally:
		# Clear up interfaces if killed during sleep.
		net.stop()

if __name__ == '__main__':
	setLogLevel( 'info' )
	for mode in ["x15"]:
		info("====== Run Mode - '{}' ======\n".format(mode))
		run(mode)

