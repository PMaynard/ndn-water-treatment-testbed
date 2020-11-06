#!/usr/bin/python

import time

from ndn.experiments.experiment import Experiment

# sudo sh -c ". dev_env/bin/activate ; python bin/minindn /vagrant/examples/ndn.conf --experiment=aqua-complex"
# By default output would be stored
# at /tmp/minindn/host/status.txt

class AquaComplex(Experiment):
	def __init__(self, args):
		Experiment.__init__(self, args)

	def setup(self):
		# print("Setting UNIX Socket forwawrding for simulator clients")
		for host in self.net.hosts:
			host_str = str(host).lower()

			if host_str.startswith("plc"):
				host.cmd( 'socat TCP4-LISTEN:8000,fork,reuseaddr UNIX-CONNECT:/tmp/aqua/sim &' )
				res_socat = host.cmd('printf $!')
				host.cmd( 'python /vagrant/icn/plc/main.py {0} > /tmp/aqua/ndn-{0}.log 2>&1 &'.format(host_str) )

				print "Host '{}' SOCAT PID '{}' PLC PID '{}'".format(host_str, res_socat, host.cmd('printf $!'))

			if host_str.startswith("hmi"):
				host.cmd( 'python /vagrant/icn/hmi/main.py {1} > /tmp/aqua/ndn-{0}.log 2>&1 &'.format(host_str, "normal") )
				print "Host '{}' HMI PID '{}'".format(host_str, host.cmd('printf $!'))

	def run(self):
		for host in self.net.hosts:
			host.cmd("nfdc status report > status.txt")

Experiment.register("aqua-complex", AquaComplex)
