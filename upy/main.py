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
from stm32_uart_slave import Stm32UartSlave
#from rp2040_uart_slave import RP2040UartSlave
from core.logger import Logger, Level

async def wait_a_bit():
    from pyb import LED
    _led = LED(1)
    for _ in range(3):
        _led.on()
        await asyncio.sleep_ms(50)
        _led.off()
        await asyncio.sleep_ms(950)
    _led.off()

async def main():

    # delay the inevitable
    await wait_a_bit()

    _log = Logger('main', Level.INFO)
    _uart_id = 4
    _baudrate = 1_000_000 # 115200 460800 921600 
    slave = Stm32UartSlave(uart_id=_uart_id, baudrate=_baudrate)
#   slave = RP2040UartSlave(uart_id=_uart_id, baudrate=_baudrate)
#   slave.set_verbose(True)
#   slave.enable_led(True)
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

# for use from the REPL
def exec():
    asyncio.run(main())

if __name__ == "__main__":
    asyncio.run(main())

#EOF
