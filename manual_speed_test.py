#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2025 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2025-06-12
# modified: 2025-06-24

from hardware.uart_master import UARTMaster
from hardware.digital_pot_async import DigitalPotentiometer

class ValueProvider:
    def __call__(self):
        raise NotImplementedError("Subclasses must implement __call__()")

class DigitalPotValueProvider(ValueProvider):

    def __init__(self):
        self._digital_pot = DigitalPotentiometer()
        self._digital_pot.start()

    def __call__(self):
        normalized_value = (self._digital_pot.value * 2) - 1  # scale 0..1 to -1..+1
        return round(100.0 * normalized_value)

if __name__ == "__main__":

    _provider = DigitalPotValueProvider()

    # instantiate the UARTMaster and run in a loop
    _baudrate = 1_000_000 # 115200 460800 921600 
    master = UARTMaster(baudrate=_baudrate)
    master.run(_provider)

#EOF
