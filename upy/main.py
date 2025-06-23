#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2025 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2025-06-12
# modified: 2025-06-23

import uasyncio as asyncio
from colorama import Fore, Style

from payload import Payload
from uart_slave import UARTSlave
from core.logger import Logger, Level

async def main():
    await asyncio.sleep(3)

    _log = Logger('main', Level.INFO)
    _uart_id = 4
    _baudrate = 1_000_000 # 115200 460800 921600 
    slave = UARTSlave(uart_id=_uart_id, baudrate=_baudrate)
#   slave.set_verbose(True)
    slave.enable_led(True)
    _log.info("UART slave: waiting for command from master…")
    while True:
        packet = await slave.receive_packet()
        if packet is not None:
#           _log.info(Fore.MAGENTA + "received payload: {}".format(packet))
            # respond with ACK + same payload command but zeroed floats (example)
            ack_payload = Payload("AK", 0.0, 0.0, 0.0, 0.0)
            await slave.send_packet(ack_payload)
        else:
            _log.warning("no valid packet received.")

def exec():
    asyncio.run(main())

if __name__ == "__main__":
    exec()

#EOF
