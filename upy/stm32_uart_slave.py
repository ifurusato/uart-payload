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
#
# A UART slave for the STM32, using UART 1-4.
#
# STM32H562 (WeActStudio 64-pin CoreBoard) UART Default Pin Mapping
#
#     +--------+-------+-------+
#     | UART   |  TX   |  RX   |
#     +--------+-------+-------+
#     | UART1  |  PA9  | PA10  |
#     | UART2  |  PA2  | PA3   |
#     | UART3  | PB10  | PB11  |
#     | UART4  | PC10  | PC11  |
#     +--------+-------+-------+
#
# Note:
# - You cannot specify tx/rx pins in MicroPython's UART() constructor; use the default pins for each.
#
# Example usage:
# uart2 = UART(2, baudrate=115200)  # Uses PA2 (TX), PA3 (RX)
# uart3 = UART(3, baudrate=115200)  # Uses PB10 (TX), PB11 (RX)
#

import uasyncio as asyncio
import time
from pyb import LED, Pin, UART
from pyb import LED
from colorama import Fore, Style

from core.logger import Logger, Level
from payload import Payload

class Stm32UartSlave:
    def __init__(self, uart_id=1, baudrate=115200):
        self._log = Logger('uart-slave', Level.INFO)
        self.uart_id  = uart_id
        self.baudrate = baudrate
        self._led = LED(1)
        self.uart = UART(uart_id)
        self.uart.init(baudrate=baudrate, bits=8, parity=None, stop=1)
        self._buffer = bytearray()
        self._last_rx    = time.ticks_ms()
        self._timeout_ms = 250
        self._verbose    = False
        self._enable_led = False
        self._log.info('UART {} slave ready at baud rate: {}.'.format(uart_id, baudrate))

    def set_verbose(self, verbose: bool):
        self._verbose = verbose

    def enable_led(self, enable: bool):
        self._enable_led = enable

    async def flash_led(self, duration_ms=30):
        if self._enable_led:
            self._led.on()
            await asyncio.sleep_ms(duration_ms)
            self._led.off()

    async def receive_packet(self):
        while True:
            if self.uart.any():
                # read all available bytes at once
                data = self.uart.read(self.uart.any())
                self._buffer += data
                self._last_rx = time.ticks_ms()
                if self._verbose:
                    self._log.info("read {} bytes, buffer size now {}".format(len(data), len(self._buffer)))
            else:
                # timeout: clear buffer to avoid garbage growth
                if self._buffer and time.ticks_diff(time.ticks_ms(), self._last_rx) > self._timeout_ms:
                    self._log.error("UART RX timeout; clearing buffer…")
                    self._buffer = bytearray()
                await asyncio.sleep(0) # was 0.005
                continue
            # check if buffer starts with SYNC_HEADER (avoid .find if possible)
            if self._buffer.startswith(Payload.SYNC_HEADER):
                if len(self._buffer) >= Payload.PACKET_SIZE:
                    packet = self._buffer[:Payload.PACKET_SIZE]
                    self._buffer = self._buffer[Payload.PACKET_SIZE:]
                    try:
                        _payload = Payload.from_bytes(packet)
                        if self._verbose:
                            self._log.info(Style.DIM + "valid packet received: {}".format(_payload))
                        await self.flash_led()
                        return _payload
                    except Exception as e:
                        # corrupt packet: remove SYNC_HEADER and resync
                        self._log.error("packet decode error: {}. resyncing…".format(e))
                        self._buffer = self._buffer[1:]
                        continue
                else:
                    # not enough data yet for a full packet
                    await asyncio.sleep(0)
                    continue
            else:
                # slow-path: search for SYNC_HEADER
                idx = self._buffer.find(Payload.SYNC_HEADER)
                if idx == -1:
                    # keep only enough bytes to possibly contain the next header
                    if len(self._buffer) > len(Payload.SYNC_HEADER):
                        self._buffer = self._buffer[-(len(Payload.SYNC_HEADER) - 1):]
                    await asyncio.sleep(0)
                    continue
                else:
                    # discard bytes up to found SYNC_HEADER
                    self._buffer = self._buffer[idx:]
                    await asyncio.sleep(0)
                    continue

    async def send_packet(self, payload: Payload):
        try:
            packet = payload.to_bytes()
            if not packet.startswith(Payload.SYNC_HEADER):
                packet = Payload.SYNC_HEADER + packet[len(Payload.SYNC_HEADER):]
            self.uart.write(packet)
            if self._verbose:
                self._log.info("sent payload: " + Fore.GREEN + '{}'.format(payload))
            await self.flash_led()
        except Exception as e:
            self._log.error("failed to send packet: {}".format(e))

#EOF
