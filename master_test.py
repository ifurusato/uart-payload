#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2025 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2025-06-12
# modified: 2025-06-12

from hardware.uart_master import UARTMaster

if __name__ == "__main__":
    # instantiate the UARTMaster and run in a loop
    _baudrate = 460800 # 115200 921600 1_000_000 
    master = UARTMaster(baudrate=_baudrate)
    master.run()

#EOF
