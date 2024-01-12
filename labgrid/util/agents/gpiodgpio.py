"""
This module implements switching GPIOs via gpiod python library.

Takes an integer property 'index' which refers to the gpiochip device
and 'line_offset' which refers to gpio line on the gpiochip.

"""
# NOTE: This is not the official python bindings from libgpiod
# libgpiod pip package requires libgpiod v2 to be installed. but this version is
# not yet packaged by the majority of distros. Adding this dependency would require
# labgrid users to install libgpiod from the sources. This is not acceptable.
# Let's wait for libgpiod v2 to get the major distros before using it.
# In the meantime, we can use another python lib which pokes the kernel directly,
# without going through libgpiod.

import gpiod
import logging
import os

from gpiod.line import Direction, Value

class GpiodDigitalOutput:
    value_str = {Value.ACTIVE: "Active", Value.INACTIVE: "Inactive"}
    value = Value.ACTIVE
    _gpiod_path_prefix = '/dev'

    def __init__(self, index, line_offset):
        self._logger = logging.getLogger("Device: ")
        self._logger.debug("Configuring GPIO %s line %d as output.", index, line_offset)
        gpiod_path = os.path.join(GpiodDigitalOutput._gpiod_path_prefix,
        f'gpiochip{index}')
        self.gpio_line = gpiod.request_lines(
            gpiod_path,
            consumer="labgrid",
            config={
                line_offset: gpiod.LineSettings(
                    direction=Direction.OUTPUT, output_value=self.value
                )
            },
        )
        print(self.gpio_line)
    
    def __del__(self):
        self.gpio_line.release()

    def get(self):
        value = self.gpio_line.get_value()
        if value == 0:
            return False
        elif value == 1:
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

        self.gpio_line.set_value(line_offset, value)

_gpios = {}

def _get_gpiod_line(line_offset):
    if line_offset not in _gpios:
        _gpios[line_offset] = GpiodDigitalOutput(index, line_offset)
    return _gpios[index]

def handle_set(index, line_offset, status):
    gpio_line = GpiodDigitalOutput(index, line_offset)
    gpio_line.set(status)

def handle_get(index, line_offset):
    gpio_line = GpiodDigitalOutput(index, line_offset)
    return gpio_line.get()

methods = {
    'set': handle_set,
    'get': handle_get,
}
