import sys
import time
import signal
import threading
import concurrent.futures
from time import gmtime, strftime

from pyndn import Name
from pyndn import Face
from pyndn import Interest

import logging
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.DEBUG)

class Connection(object):
	def __init__(self, name, face):
		Interest.setDefaultCanBePrefix(True)
		
		self.name = Name(name)
		self.face = face
		self._callbackCount = 0
		self.value = None
		self.last = None
	
	def __str__(self):
		return "{} Name: {} Value: '{}'/{} at {}".format(self.face, self.name, self.value, self._callbackCount, self.last)

	def onData(self, interest, data):
		self._callbackCount += 1
		self.value = data.getContent().toRawStr()
		self.last = strftime("%Y-%m-%d %H:%M:%S", gmtime())
		log.debug(self)
		log.debug("OnData: {} {}".format(data.getName().toUri(), data.getContent().toRawStr()))

	def onTimeout(self, interest):
		self._callbackCount += 1
		log.debug(self)
		log.debug("Time out for interest".format(interest.getName().toUri()))

	def onNetworkNack(self, interest, networkNack):
		self._callbackCount += 1
		log.debug(self)
		log.debug("NACK\n\tInterest: '{}'\n\tReason: '{}'".format(interest.getName().toUri(), networkNack.getOtherReasonCode()))

face = Face()
while True:
	c = Connection('/ndn/industrial/qub/water/reservoirsensor', face)
	c.face.expressInterest(c.name, c.onData, c.onTimeout, c.onNetworkNack)

	while c._callbackCount < 1:
		c.face.processEvents()
		time.sleep(0.01)

	time.sleep(1)

