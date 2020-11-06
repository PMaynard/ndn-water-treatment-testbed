#!/usr/bin/env python

import threading
import logging
import uuid
from datetime import datetime
import yaml
import time

log = logging.getLogger('scadasim')

class InvalidDevice(Exception):
        """Exception thrown for bad device types
        """
        def __init__(self, message):
            super(InvalidDevice, self).__init__(message)

# Devices
class Device(yaml.YAMLObject):
    allowed_device_types = ['pump', 'valve', 'filter', 'tank', 'reservoir', 'sensor', 'chlorinator']

    def __init__(self, device_type=None, fluid=None, label='', state=None, worker_frequency=1):
        self.uid = str(uuid.uuid4())[:8]
        self.device_type = device_type
        self.label = label
        self.inputs = {}
        self.outputs = {}
        self.fluid = fluid
        self.active = False
        # Time interval in seconds. set to None if the device doesnt need a worker loop
        self.worker_frequency = worker_frequency
        self.speed = 1
        self.state = state

        if (not self.device_type) or (self.device_type not in self.allowed_device_types):
            raise InvalidDevice("\'%s\' in not a valid device type" % self.device_type)

        log.info("%s: Initialized" % self)

    @classmethod
    def from_yaml(cls, loader, node):
        fields = loader.construct_mapping(node, deep=False)
        return cls(**fields)

    def add_input(self, device):
        """Add the connected `device` to our inputs and add this device to the connected device's outputs
        """
        if device.uid not in self.inputs:
            self.inputs[device.uid] = device
            device.add_output(self)
            log.info("%s: Added input <- %s" % (self, device))

    def add_output(self, device):
        """Add the connected device to our outputs and add this device to connected device's inputs
        """
        if device.uid not in self.outputs:
            self.outputs[device.uid] = device
            device.add_input(self)
            log.info("%s: Added output -> %s" % (self, device))

    def run(self):
        """Executed at atleast once and at regular intervals if `worker_frequency` is not None.
            Used to call worker method
        """
        if self.active:
            log.debug("%s %s" % (self, datetime.now()))
            self.worker()
        
            if self.worker_frequency:
                # Calculate the next run time based on simulation speed and device frequency
                delay = (-time.time()%(self.speed*self.worker_frequency))
                t = threading.Timer(delay, self.run)
                t.daemon = True
                t.start()

    def activate(self):
        """Set this device as active so the worker gets called"""
        if self.active == False:
            self.active = True
            self.run()
        log.info("%s: Active" % self)

    def deactivate(self):
        """Set this device as inactive to prevent the worker from being called"""
        if self.active == True:
            self.active = False
        log.info("%s: Inactive" % self)

    def read_state(self):
        return self.state

    def write_state(self, state=None):
        """ Set the devices state"""
        if state is not None:
            self.state = state
            return True
        return False

    def worker(self):
        """Do something each cycle of `worker_frequency`
            Update fluid, pull inputs, push outputs, etc.
            Override this for each custom Device
        """
        pass

    def input(self, fluid):
        """Receive and process some fluid
            Override this with your own processing to perform when new fluid is received
        """
        return 0

    def output(self):
        """Receive and process some fluid
            Override this with your own processing to perform when fluid is outputted
        """
        return 0

    def __repr__(self):
        return "[%s][%s][%s]" % (self.uid, self.device_type, self.label)


class Pump(Device):
    yaml_tag = u'!pump'

    def __init__(self, device_type='pump', state='off', **kwargs):
        state = bool(['off', 'on'].index(state))
        super(Pump, self).__init__(device_type=device_type, state=state, **kwargs)

    def worker(self):
        """Manipulate the fluid just as this device would in the real world
        """
        if self.state:
            for i in self.inputs:
                self.inputs[i].output(self)

    def input(self, fluid, volume=1):
        if self.state:
            self.fluid = fluid
            for o in self.outputs:
                # Send fluid to all outputs
                accepted_volume = self.outputs[o].input(fluid, volume)
            return accepted_volume
        else:
            return 0

    def output(self, to_device, volume=1):
        if self.state:
            return self.fluid
        else:
            return 0

    def turn_on(self):
        self.state = True

    def turn_off(self):
        self.state = False


class Valve(Device):
    yaml_tag = u'!valve'

    def __init__(self, device_type='valve', state='closed', **kwargs):
        state = bool(['closed', 'open'].index(state))
        super(Valve, self).__init__(device_type=device_type, state=state, **kwargs)

    def open(self):
        self.state = True

    def close(self):
        self.state = False

    def output(self, to_device, volume=1):
        """If the valve is open, pull `volume` amount from connected devices
            TODO: Handle multiple inputs and outputs. Distributing the volume across
            all based on valve capacity.
        """
        if self.state:
            available_volume = 0
            for i in self.inputs:
                available_volume = self.inputs[i].output(self, volume=volume)
            return available_volume
        else:
            #log.debug("%s closed" % self)
            return 0

    def input(self, fluid, volume=1):
        """If the valve is open, pass `volume` amount of `fluid` to the connected devices
            Normally used when pump's push fluid through.
        """
        if self.state:
            accepted_volume = 0
            for o in self.outputs:
                # Send the fluid on to all outputs
                #log.debug("%s sending fluid to %s" % (self, self.outputs[o]))
                accepted_volume = self.outputs[o].input(fluid, volume)
            return accepted_volume
        else:
            return 0

class Filter(Device):
    yaml_tag = u'!filter'

    def __init__(self, device_type='filter', **kwargs):
        super(Filter, self).__init__(device_type=device_type, **kwargs)

    def output(self, to_device, volume=1):
        available_volume = 0
        for i in self.inputs:
            available_volume = self.inputs[i].output(self, volume=volume)
        return available_volume

    def input(self, fluid, volume=1):
        accepted_volume = 0
        for o in self.outputs:
            accepted_volume = self.outputs[o].input(fluid, volume)
        return accepted_volume

class Tank(Device):
    yaml_tag = u'!tank'

    def __init__(self, volume=0, device_type='tank', **kwargs):
    	self.volume = volume
        super(Tank, self).__init__(device_type=device_type, **kwargs)

    def __increase_volume(self, volume):
        """Raise the tank's volume by `volume`"""
        self.volume += volume
        return volume

    def __decrease_volume(self, volume):
        """Lower the tank's volume by `volume`"""
        self.volume -= self.__check_volume(volume)

    def __check_volume(self, volume):
        """See if the tank has enough volume to provide the requested `volume` amount
        """
        if self.volume <= 0:
            volume = 0
        elif self.volume > volume:
            volume = volume
        else:
            volume = self.volume
        return volume

    def __update_fluid(self, new_context):
    	self.fluid = new_context

    def input(self, fluid, volume=1):
        """Receive `volume` amount of `fluid`"""
        self.__update_fluid(fluid)
        accepted_volume = self.__increase_volume(volume)
        return accepted_volume

    def output(self, to_device, volume=1):
        """Send `volume` amount of fluid to connected device
            This verifies that the connected device accepts the amount of volume before
            we decrease our volume. e.g. full tank.
        """
        accepted_volume = to_device.input(self.fluid, self.__check_volume(volume))
        self.__decrease_volume(accepted_volume)

    def worker(self):
        """For debugging only. Used to display the tank's volume"""
        pass

class Reservoir(Tank):
    yaml_tag = u'!reservoir'

    def __init__(self, **kwargs):
        super(Reservoir, self).__init__(device_type='reservoir', **kwargs)
    
    def worker(self):
        """Make sure that we don't run dry.
        """
        self.volume += 10

class Chlorinator(Tank):
    yaml_tag = u'!chlorinator'

    def __init__(self, device_type='chlorinator', **kwargs):
        super(Chlorinator, self).__init__(device_type=device_type, **kwargs)

    def output(self, to_device, volume=1):
        available_volume = 0
        for i in self.inputs:
            available_volume = self.inputs[i].output(self, volume=volume)
        return available_volume

    def input(self, fluid, volume=1):
        self.fluid = fluid
        accepted_volume = 0
        for o in self.outputs:
            accepted_volume = self.outputs[o].input(fluid, volume)
        return accepted_volume

