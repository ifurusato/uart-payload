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

import time
from pyb import LED, Pin, UART
from pyb import LED
from colorama import Fore, Style

from core.logger import Logger, Level
from payload import Payload

class UARTSlave:
    def __init__(self, uart_id=1, baudrate=115200):
        self._log = Logger('uart-slave', Level.INFO)
        self.uart_id  = uart_id
        self.baudrate = baudrate
        # set up LED
        self._led = LED(1)
        # set up UART connection with default pins
        self.uart = UART(uart_id)
        self.uart.init(baudrate=baudrate, bits=8, parity=None, stop=1)
        # buffer and timing for sync protocol
        self._buffer = bytearray()
        self._last_rx = time.ticks_ms()
        self._timeout_ms = 250
        self._verbose = False
        self._log.info('UART {} slave ready at baud rate: {}.'.format(uart_id, baudrate))

    def set_verbose(self, verbose: bool):
        self._verbose = verbose

    def flash_led(self, duration_ms=30):
        self._led.on()
        time.sleep_ms(duration_ms)
        self._led.off()

    def receive_packet(self):
        """
        Waits for a valid payload packet, synchronizing on the sync header.
        Returns a Payload instance.
        """
        while True:
            # read available bytes from UART
            if self.uart.any():
                data = self.uart.read(self.uart.any())
                self._buffer += data
                self._last_rx = time.ticks_ms()
                if self._verbose:
                    self._log.info("read {} bytes, buffer size now {}".format(len(data), len(self._buffer)))
            else:
                # timeout for incomplete packets
                if self._buffer and time.ticks_diff(time.ticks_ms(), self._last_rx) > self._timeout_ms:
                    self._log.error("UART RX timeout; clearing buffer…")
                    self._buffer = bytearray()
                time.sleep(0.005)
                continue
            # look for sync header
            idx = self._buffer.find(Payload.SYNC_HEADER)
            if idx == -1:
                # trim buffer so it doesn't grow unbounded
                if len(self._buffer) > len(Payload.SYNC_HEADER):
                    if self._verbose:
                        self._log.info("sync header not found; trimming buffer…")
                    self._buffer = self._buffer[-(len(Payload.SYNC_HEADER)-1):]
                continue
            # check if enough bytes for a packet
            if len(self._buffer) - idx >= Payload.PACKET_SIZE:
                packet = self._buffer[idx: idx + Payload.PACKET_SIZE]
                self._buffer = self._buffer[idx + Payload.PACKET_SIZE:]
                try:
                    _payload = Payload.from_bytes(packet)
                    if self._verbose:
                        self._log.info(Style.DIM + "valid packet received: {}".format(_payload))
                    self.flash_led()
                    return _payload
                except Exception as e:
                    self._log.error("packet decode error: {}. Resyncing...".format(e))
                    # remove just the first header byte to attempt resync
                    self._buffer = self._buffer[idx+1:]
                    continue
            else:
                # wait for more data
                continue

    def send_packet(self, payload: Payload):
        """
        Serializes and sends a payload packet with sync header.
        """
        try:
            packet = payload.to_bytes()
            if not packet.startswith(Payload.SYNC_HEADER):
                packet = Payload.SYNC_HEADER + packet[len(Payload.SYNC_HEADER):]
            self.uart.write(packet)
            if self._verbose:
                self._log.info("sent payload: " + Fore.GREEN + '{}'.format(payload))
            self.flash_led()
        except Exception as e:
            self._log.error("failed to send packet: {}".format(e))

#EOF
