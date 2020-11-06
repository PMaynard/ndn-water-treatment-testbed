# from ui import UI
# from ui import UI_Element
import sys
import time
import threading
import socket

from plcrpcservice import PLCRPCClient

import pyndn

from pyndn import Name
from pyndn import Face
from pyndn import Interest
from pyndn.security import KeyChain
from pyndn.security.identity import IdentityManager
from pyndn.security import AesKeyParams
from pyndn import Data
from pyndn import MetaInfo
from pyndn.util.common import Common

import logging
logging.basicConfig()
log = logging.getLogger('PLC')
log.setLevel(logging.DEBUG)

class store(object):
    def __init__(self, slaveid, register, address, value):
        self.slaveid = slaveid
        self.register = register
        self.address = address
        self.value = value

    def __str__(self):
        return "{} {} {} {} {}".format(self.name, self.slaveid, self.register, self.address, self.value)

class PLC(object):

    def __init__(self, name=None):
        # PLC Simulation
        self.slaveid = 0x00
        self.name = name
        if not name:
            self.name = socket.gethostname()
        self.plcrpcclient = PLCRPCClient(rpc_server="0.0.0.0", rpc_port=8000, plc=self.name)
        self.registered = False
        self.speed = 0.2
        self.db = {}
        # NDN
        self._callbackCount = 0
        self.primary_prefix = "/example"
        self.names = []
        self.freshnessPeriod = 2000 # in milliseconds (2000 = 2s).
        
        self.identify_manager = IdentityManager()
        self.keyChain = KeyChain(self.identify_manager)
        
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
            self.db[sensor] = store(self.slaveid, address, register, value)

    def _registerPLC(self):
        self.slaveid = self.plcrpcclient.registerPLC()
        self.registered = True
        log.debug("[PLC][%s] Registered on scadasim rpc" % self.name)
        return True

    def update(self):
        # log.debug("[PLC][%s] Updating PLC values with sensor values" % self)
        # while not self.queue.empty():
        #     # Update scadasim with any new values from Master
        #     fx, address, values = self.queue.get()
        #     log.debug("[PLC][%s] setting fx: %s register:%s to value:%s" %
        #               (self.name, fx, address, values))
        #     self.plcrpcclient.setValues(fx=fx, address=address, values=values)

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

        log.debug("[PLC][%s] Starting NDN Producer" % self.name)
        

        #  TODO: Move this setup stuff into a function and make dynamic.
        log.info("Listening on: ")
        for n in self.db:
            # /ndn/plc2-site/plc2
            name = Name("{0}/{1}-site/{1}/{2}".format(self.primary_prefix, self.name, n))
            log.info("\t{}".format(name))

            name_identiy = self.keyChain.createIdentityAndCertificate(name, self.keyChain.getDefaultKeyParams())
            log.debug("Name Identify: {}".format(name_identiy))
            self.face.setCommandSigningInfo(self.keyChain, name_identiy)
            self.face.registerPrefix(name, self.onInterest, self.onRegisterFailed)

            # log.debug("Registered Prefix: {} {}", str(self.primary_prefix), str(n))
        # END LOOP

        # Keep Running unless error.
        while self._callbackCount < 1:
            self.face.processEvents()
            time.sleep(0.01)

        self.face.shutdown()

    # NDN Stuff
    def ndnInit(self): 
        Interest.setDefaultCanBePrefix(True)
        # TODO: Bug? Does not auto retry TCP if unix socket fails as says in docs. 
        # self.face = Face("localhost", 6363)
        self.face = Face()
        self.primary_prefix = "/ndn"

    def onInterest(self, prefix, interest, face, interestFilterId, filter):
        self._callbackCount = 0
        
        # log.debug("prefix: '{}'".format(prefix))
        # log.debug("interest: '{}'".format(interest))
        # log.debug("face: '{}'".format(face))
        # log.debug("interestFilterId: '{}'".format(interestFilterId))
        # log.debug("filter: '{}'".format(filter))

        data = Data()
        
        # 
        # log.debug("----")
        # for n in self.db:
        #     log.debug(n)
        #     log.debug(self.db[n].value)
        # log.debug("----")
        # 

        n = str(prefix).split("/")[-1]

        log.debug("{} value '{}' ({})".format(prefix, self.db[n].value, self.freshnessPeriod))

        data.setContent(str(self.db[n].value)) # TODO: Why does this need to be converted to string?
        data.setName(prefix)
        meta = MetaInfo()
        meta.setFreshnessPeriod(self.freshnessPeriod)
        data.setMetaInfo(meta) 
        self.keyChain.sign(data)

        face.putData(data)

    def onRegisterFailed(self, prefix):
        self._callbackCount += 1
        dump("Unable to register", prefix)

# 
try:
    plc = PLC(sys.argv[1])
except:
    plc = PLC()

# Keep trying until we get a connection.
while True:
    plc.ndnInit()
    plc.main()
    time.sleep(5)
