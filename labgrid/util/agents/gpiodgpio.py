"""
This module implements switching GPIOs via gpiod python library.

Takes an integer property 'gpiochip' which refers to the gpiochip device
and 'index' which refers to gpio line on the gpiochip.

"""
# NOTE: This is not the official python bindings from libgpiod
# libgpiod pip package requires libgpiod v2 to be installed. but this version is
# not yet packaged by the majority of distros. Adding this dependency would require
# labgrid users to install libgpiod from the sources. This is no acceptable.
# Let's wait for libgpiod v2 to get the major distros before using it.
# In the meantime, we can use another python lib which pokes the kernel directly,
# without going through libgpiod.

import gpiod
import logging
import os

class GpiodDigitalOutput:
    def __init__(self, gpiochip, index):
        self._logger = logging.getLogger("Device: ")
        self._logger.debug("Configuring GPIO %s line %d as output.", gpiochip, index)
        chip = gpiod.chip(gpiochip, gpiod.chip.OPEN_BY_PATH)
        cfg = gpiod.line_request()
        cfg.consumer = "labgrib"
        cfg.request_type = gpiod.line_request.DIRECTION_OUTPUT
        self.line = chip.get_line(index)
        self.line.request(cfg)

    def __del__(self):
        self.line.release()

    def get(self):
        value = self.line.get_value()
        if value == 0:
            return False
        else if value == 1:
            return True
        else:
            ValueError("GPIO value is out of range.")
 
    def set(self, status):
        self._logger.debug("Setting GPIO to `%s`.", status)
        value = None
        if status is True:
            value = 1
        elif status is False:
            value = 0

        if value is None:
            raise ValueError("GPIO value is out of range.")

        self.line.set_value(value)

# NOTE: Here are not keeping ownership of the gpio in between calls
# This might something worth fixing later on
        
def handle_set(gpiochip, index, status):
    gpio_line = GpiodDigitalOutput(gpiochip, index)
    gpio_line.set(status)

def handle_get(gpiochip, index):
    gpio_line = GpiodDigitalOutput(gpiochip, index)
    return gpio_line.get()

methods = {
    'set': handle_set,
    'get': handle_get,
}
