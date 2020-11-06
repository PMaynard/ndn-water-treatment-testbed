import sys
import time
import signal
import threading
import concurrent.futures
from time import gmtime, strftime

import numpy as np
import pandas as pd

from pyndn import Name
from pyndn import Face
from pyndn import Interest

import logging
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.DEBUG)

class ProccessControlMonitor(object):
	def __init__(self): 
		e = Engine()

		# PLC1
		e.addInstrument("/ndn/plc1-site/plc1/reservoirsensor")
		e.addInstrument("/ndn/plc1-site/plc1/pump1sensor")
		e.addInstrument("/ndn/plc1-site/plc1/valve1sensor")

		# PLC2
		e.addInstrument("/ndn/plc2-site/plc2/valve2sensor")
		e.addInstrument("/ndn/plc2-site/plc2/pump2sensor")

		# PLC3
		e.addInstrument("/ndn/plc3-site/plc3/valve3sensor")
		e.addInstrument("/ndn/plc3-site/plc3/pump3sensor")
		e.addInstrument("/ndn/plc3-site/plc3/municipaltanksensor")

		# PLC4 
		e.addInstrument("/ndn/plc4-site/plc4/chlorinetanksensor")
		e.addInstrument("/ndn/plc4-site/plc4/chlorinevalvesensor")
		e.addInstrument("/ndn/plc4-site/plc4/chlorinepumpsensor")
		e.addInstrument("/ndn/plc4-site/plc4/chlorinatorsensor")

		e.start()

		# Query the Engine every 2s to get the latest statuses.
		while True:
			time.sleep(2)
			for instrument in e.getInstruments():
				log.info("{}, {}, {}".format(instrument.name, instrument.data, instrument.last))
			print ""

class MeasuredInstrumnet(object):
	def __init__(self, name):
		self.name = name
		self.device = self.name.split('/')[3]
		self.data = None
		self.last = None

	def __str__(self):
		return "Name: {} Value: '{}' Last: {}".format(self.name, self.data, self.last)

	def getName(self):
		return self.name

	def setData(self, data):
		self.last = strftime("%Y-%m-%d %H:%M:%S", gmtime())
		self.data = data

class Engine(object):
	def __init__(self, tick = 1 ):
		signal.signal(signal.SIGINT, self.sigHandler)
		signal.signal(signal.SIGHUP , self.sigHandler)

		self.running = True
		self.measured_instruments = []
		self.tick = tick
		self.measurements = []
	
	def sigHandler(self, num, frame):
		self.stop()

	def start(self):
		for measured_instrument in self.measured_instruments:
			engine_thread = threading.Thread(target=self.run, args=(measured_instrument,))
			engine_thread.daemon = True 
			engine_thread.start()

		# Every 30 write out a trace file.
		write_thread = threading.Thread(target=self.writeMeasurements)
		write_thread.daemon = True
		write_thread.start()

	def run(self, measured_instrument):
		while self.running:
			c = Connection(self, measured_instrument)
			c.face.expressInterest(c.name, c.onData, c.onTimeout, c.onNetworkNack)
			while c._callbackCount < 1:
				c.face.processEvents()
				time.sleep(0.01)
			if not c._callbackTimeout == 0:
				log.debug("Connection requested timeout of {}s".format(c._callbackTimeout))
				time.sleep(c._callbackTimeout)

		log.debug("Tick: {}s".format(self.tick))
		time.sleep(self.tick) 

	def stop(self):
		self.running = False
		log.info("Shutting down....")
		time.sleep(20) # Wait for all connections
		self.flush()
		# TODO: Track all faces and shut then down.
		# log.debug("Down: {}".format(self.face)
		sys.exit(0)

	def addInstrument(self, name):
		self.measured_instruments.append(MeasuredInstrumnet(name))

	def addMeasurement(self, datetime, device, name, latency, status):
		self.measurements.append((datetime, device, name, latency, status))

	def getInstruments(self):
		return self.measured_instruments

	def flush(self): 
		log.debug("Flushing measurements")
		pd.DataFrame(self.measurements, columns=['datetime', 'device', 'name', 'latency', 'status']).to_csv("/tmp/aqua/measurements-ndn-{}.csv".format(sys.argv[1]))

	def writeMeasurements(self): 
		while self.running:
			self.flush()
			time.sleep(30)

class Connection(object):
	def __init__(self, engine, measured_instrument):
		Interest.setDefaultCanBePrefix(True)
		
		self.engine = engine
		self.measured_instrument = measured_instrument
		self.name = Name(measured_instrument.getName())
		self.face = Face()
		self._callbackCount = 0
		self._callbackTimeout = 0
		self.value = None
		self.last = None
		self.time_start = time.time()
	
	def __str__(self):
		return "{} Name: {} Value: '{}'/{} at {}".format(self.face, self.name, self.value, self._callbackCount, self.last)

	def onData(self, interest, data):
		self._callbackCount += 1
		self.engine.addMeasurement(time.time(), self.measured_instrument.device, self.measured_instrument.name, ((time.time() - self.time_start)*1000), 1)
		self.value = data.getContent().toRawStr()
		self.last = strftime("%Y-%m-%d %H:%M:%S", gmtime())
		# log.debug(self)
		# log.debug("OnData: {} {}".format(data.getName().toUri(), data.getContent().toRawStr()))
		self.measured_instrument.setData(data.getContent().toRawStr())

	def onTimeout(self, interest):
		self._callbackCount += 1
		self._callbackTimeout = 10
		self.engine.addMeasurement(time.time(), self.measured_instrument.device, self.measured_instrument.name, ((time.time() - self.time_start)*1000), -1)
		# log.debug(self)
		log.debug("Time out for interest".format(interest.getName().toUri()))

	def onNetworkNack(self, interest, networkNack):
		self._callbackCount += 1
		self._callbackTimeout = 10
		self.engine.addMeasurement(time.time(), self.measured_instrument.device, self.measured_instrument.name, ((time.time() - self.time_start)*1000), -2)
		# log.debug(self)
		log.debug("NACK\n\tInterest: '{}'\n\tReason: '{}'".format(interest.getName().toUri(), networkNack.getOtherReasonCode()))

if __name__ == '__main__':
	if len(sys.argv) != 2:
		sys.exit("Mode required e.g. {} [normal|lossy20]".format(sys.argv[0]))
	ProccessControlMonitor()
