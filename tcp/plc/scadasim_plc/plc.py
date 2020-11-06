from plcrpcservice import PLCRPCClient

from pymodbus.server.async import StartTcpServer
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext

import threading
import socket
import time

import sys

import logging
from Queue import Queue

from multiprocessing import Queue, Process
logging.basicConfig()
log = logging.getLogger('scadasim')
log.setLevel(logging.DEBUG)


class CallbackModbusSlaveContext(ModbusSlaveContext):

    def __init__(self, queue, **kwargs):
        self.queue = queue
        super(CallbackModbusSlaveContext, self).__init__(**kwargs)

    def setValues(self, fx, address, values):
        super(CallbackModbusSlaveContext, self).setValues(fx, address, values)
        self.queue.put((fx, address, values))


class PLC(object):

    def __init__(self, name=None):
        self.connected_sensors = {}
        self.slaveid = 0x00
        self.name = name
        if not name:
            self.name = socket.gethostname()
        self.plcrpcclient = PLCRPCClient(
            rpc_server="0.0.0.0", rpc_port=8000, plc=self.name)
        self.registered = False

        identity = ModbusDeviceIdentification()
        identity.VendorName = 'scadasim'
        identity.ProductCode = 'PLC'
        identity.VendorUrl = 'https://github.com/sintax1/scadasim-plc'
        identity.ProductName = 'scadasim-PLC'
        identity.ModelName = 'SimPLC'
        identity.MajorMinorRevision = '1.0'
        self.identity = identity
        self.speed = 0.2
        self.queue = Queue()
        self.context = None

    def _initialize_store(self, max_register_size=100):
        store = {}

        store[self.slaveid] = CallbackModbusSlaveContext(
            self.queue,
            di=ModbusSequentialDataBlock(0, [False] * 100),
            co=ModbusSequentialDataBlock(0, [False] * 100),
            hr=ModbusSequentialDataBlock(0, [0] * 100),
            ir=ModbusSequentialDataBlock(0, [0] * 100))
        self.context = ModbusServerContext(slaves=store, single=False)

    def _get_sensor_data(self):

        sensor_data = self.plcrpcclient.readSensors()

        for sensor in sensor_data:
            register = sensor_data[sensor]['register_type']

            address = int(sensor_data[sensor]['data_address'])

            if register in ['c', 'd']:
                value = bool(sensor_data[sensor]['value'])
            elif register in ['h', 'i']:
                value = int(sensor_data[sensor]['value'])

            address = address + 1  # section 4.4 of specification
            self.context[self.slaveid].store[register].setValues(address, [
                value])

    def _registerPLC(self):
        self.slaveid = self.plcrpcclient.registerPLC()
        self.registered = True
        self._initialize_store()
        log.debug("[PLC][%s] Registered on scadasim rpc" % self.name)
        return True

    def update(self):
        log.debug("[PLC][%s] Updating PLC values with sensor values" % self)

        while not self.queue.empty():
            # Update scadasim with any new values from Master
            fx, address, values = self.queue.get()
            log.debug("[PLC][%s] setting fx: %s register:%s to value:%s" %
                      (self.name, fx, address, values))
            self.plcrpcclient.setValues(fx=fx, address=address, values=values)

        self._get_sensor_data()

        delay = (-time.time() % self.speed)
        t = threading.Timer(delay, self.update, ())
        t.daemon = True
        t.start()

    def set_speed(self, speed):
        self.speed = speed

    def __repr__(self):
        return "%s" % self.name

    def main(self):

        log.debug("[PLC][%s] Initialized" % self.name)
        while not self.registered:
            log.debug(
                "[PLC][%s] Trying to register with scadasim rpc" % self.name)
            try:
                self._registerPLC()
            except KeyError:
                log.warn(
                    """[PLC][%s] PLC not found within scadasim. Verify Docker
                     Compose container names match list of plcs in scadasim
                     config""")

            time.sleep(1)

        log.debug("[PLC][%s] Starting update service" % self.name)
        self.update()

        log.debug("[PLC][%s] Starting MODBUS Server" % self.name)
        StartTcpServer(self.context, identity=self.identity,
                       address=("0.0.0.0", 502))


if __name__ == '__main__':
    plc = PLC(sys.argv[1])
    plc.main()

"""

'di' - Discrete Inputs initializer 'co' - Coils initializer 'hr' - Holding Register initializer 'ir' - Input Registers iniatializer

    Coil/Register Numbers   Data Addresses  Type        Table Name                          Use
    1-9999                  0000 to 270E    Read-Write  Discrete Output Coils               on/off read/write   co
    10001-19999             0000 to 270E    Read-Only   Discrete Input Contacts             on/off readonly     di
    30001-39999             0000 to 270E    Read-Only   Analog Input Registers              analog readonly     ir
    40001-49999             0000 to 270E    Read-Write  Analog Output Holding Registers     analog read/write   hr

    Each coil or contact is 1 bit and assigned a data address between 0000 and 270E.
    Each register is 1 word = 16 bits = 2 bytes
"""
