from pymodbus.client.sync import ModbusTcpClient

import sys

import time
from time import gmtime, strftime
import signal
import threading

import pandas as pd

import logging
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.INFO)

class ProccessControlMonitor(object):
	def __init__(self): 
		e = Engine()

		# IP, data_address, slaveid, type, name

		# PLC1
		e.addInstrument("10.6.0.1", 0, 1, "input_register", "reservoirsensor")
		e.addInstrument("10.6.0.1", 0, 1, "coil", "pump1sensor")
		e.addInstrument("10.6.0.1", 1, 1, "coil", "valve1sensor")

		# PLC2
		e.addInstrument("10.6.0.2", 0, 3, "coil", "valve2sensor")
		e.addInstrument("10.6.0.2", 1, 3, "coil", "pump2sensor")

		# PLC3
		e.addInstrument("10.7.0.3", 0, 4, "coil", "valve3sensor")
		e.addInstrument("10.7.0.3", 0, 4, "coil", "pump3sensor")
		e.addInstrument("10.7.0.3", 0, 4, "input_register", "municipaltanksensor")

		# # PLC4 
		e.addInstrument("10.7.0.4", 0, 2, "input_register", "chlorinetanksensor")
		e.addInstrument("10.7.0.4", 0, 2, "coil", "chlorinevalvesensor")
		e.addInstrument("10.7.0.4", 1, 2, "coil", "chlorinepumpsensor")
		e.addInstrument("10.7.0.4", 1, 2, "input_register", "chlorinatorsensor")

		e.start()

		# Query the Engine every 2s to get the latest statuses.
		while True:
			time.sleep(0.5)
			for instrument in e.getInstruments():
				log.info("{} \t {} \t {} \t {}".format(instrument.ip, instrument.data, instrument.name, instrument.last))
			print ""

class MeasuredInstrumnet(object):
	def __init__(self, ip, address, unit, type, name):
		self.ip = ip
		self.address = address
		self.unit = unit
		self.type = type 
		self.name = name
		self.data = None
		self.last = None

	def __str__(self):
		return "IP: {} Name: {} Value: '{}' Last: {}".format(self.ip, self.name, self.data, self.last)

	def setData(self, data):
		self.last = strftime("%Y-%m-%d %H:%M:%S", gmtime())
		self.data = data

class Engine(object):
	def __init__(self, tick = 1 ):
		signal.signal(signal.SIGINT , self.sigHandler)
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

		# Every 30s write out a trace file.
		write_thread = threading.Thread(target=self.writeMeasurements)
		write_thread.daemon = True
		write_thread.start()		

	def run(self, measured_instrument):
		while self.running:
			c = ModbusTcpClient(measured_instrument.ip)
			start = time.time()
			while not c.connect():
				log.debug("Can't connect, retry in 0.5s")
				self.measurements.append((time.time(), measured_instrument.ip, measured_instrument.name, ((time.time() - start)*1000), -2))
				time.sleep(0.5)

			if measured_instrument.type == "input_register":
				response = c.read_input_registers(measured_instrument.address, 1, unit=measured_instrument.unit)
				measured_instrument.setData(response.registers[0]) 

			if measured_instrument.type == "coil":
				response = c.read_coils(measured_instrument.address, 1, unit=measured_instrument.unit)
				measured_instrument.setData(response.bits[0])
			c.close()
			self.measurements.append((time.time(), measured_instrument.ip, measured_instrument.name, ((time.time() - start)*1000), 1))

			log.debug("Tick: {}".format(self.tick))
			time.sleep(self.tick)

	def stop(self):
		self.running = False
		log.info("Shutting down....")
		time.sleep(20) # Wait for all connections
		self.flush()
		# TODO: Close any modbus connections. 
		sys.exit(0)

	def addInstrument(self, ip, address, unit, type, name):
		self.measured_instruments.append(MeasuredInstrumnet(ip, address, unit, type, name))

	def getInstruments(self):
		return self.measured_instruments

	def flush(self):
		pd.DataFrame(self.measurements, columns=['datetime', 'ip', 'name', 'latency', 'status']).to_csv("log/measurements-tcp-{}.csv".format(sys.argv[1]))

	def writeMeasurements(self):
		while self.running:
			self.flush()
			time.sleep(30)

if __name__ == '__main__':
	if len(sys.argv) != 2:
		sys.exit("Needs a mode argument e.g. {} [normal|lossy20]".format(sys.argv[0]))
	ProccessControlMonitor()