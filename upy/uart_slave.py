#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2025 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2025-06-12
# modified: 2025-06-22
#
# pins on WeAct STM32F405/STM32H562:
#
#    UART1_RX,PA9
#    UART1_TX,PA10
#

from pyb import LED, Pin, UART
from pyb import LED
#from machine import UART, Pin
import time
from core.logger import Logger, Level
from payload import Payload

class UARTSlave:
    def __init__(self, uart_id=1, baudrate=115200):
        self._log = Logger('uart-slave', Level.INFO)
        self.baudrate = baudrate
        self.uart_id  = uart_id
        # set up LED
        self._led = LED(1)
        # set up UART connection with custom TX and RX pins
        self.uart = UART(uart_id)
        self.uart.init(baudrate=baudrate, bits=8, parity=None, stop=1)
        self._verbose = False
        self._log.info('UART slave ready at baud rate: {}.'.format(baudrate))
        # Buffer and timing for sync protocol
        self._buffer = bytearray()
        self._last_rx = time.ticks_ms()
        self._timeout_ms = 250  # ms

    def set_verbose(self, verbose: bool):
        self._verbose = verbose

#   def flash_led(self, duration_ms=50):
#       self.led.value(1)
#       time.sleep_ms(duration_ms)
#       self.led.value(0)

    def receive_packet(self):
        """
        Waits for a valid payload packet, synchronizing on the sync header.
        Returns a Payload instance.
        """
        while True:
            # Read available bytes from UART
            if self.uart.any():
                data = self.uart.read(self.uart.any())
                self._buffer += data
                self._last_rx = time.ticks_ms()
                if self._verbose:
                    self._log.debug("Read {} bytes, buffer size now {}".format(len(data), len(self._buffer)))
            else:
                # Timeout for incomplete packets
                if self._buffer and time.ticks_diff(time.ticks_ms(), self._last_rx) > self._timeout_ms:
                    self._log.error("UART RX timeout; clearing buffer")
                    self._buffer = bytearray()
                time.sleep(0.005)
                continue

            # Look for sync header
            idx = self._buffer.find(Payload.SYNC_HEADER)
            if idx == -1:
                # Trim buffer so it doesn't grow unbounded
                if len(self._buffer) > len(Payload.SYNC_HEADER):
                    if self._verbose:
                        self._log.debug("Sync header not found; trimming buffer")
                    self._buffer = self._buffer[-(len(Payload.SYNC_HEADER)-1):]
                continue

            # Check if enough bytes for a packet
            if len(self._buffer) - idx >= Payload.PACKET_SIZE:
                packet = self._buffer[idx: idx + Payload.PACKET_SIZE]
                self._log.info("SLAVE RX BYTES: {}".format(packet.hex(' ')))  # <-- ADD THIS LINE
                packet = self._buffer[idx: idx + Payload.PACKET_SIZE]
                self._buffer = self._buffer[idx + Payload.PACKET_SIZE:]
                try:
                    pl = Payload.from_bytes(packet)
                    if self._verbose:
                        self._log.info("Valid packet received: {}".format(pl))
#                   self.flash_led()
                    return pl
                except Exception as e:
                    self._log.error("Packet decode error: {}. Resyncing...".format(e))
                    # Remove just the first header byte to attempt resync
                    self._buffer = self._buffer[idx+1:]
                    continue
            else:
                # Wait for more data
                continue

    def send_packet(self, payload: Payload):
        """
        Serializes and sends a payload packet with sync header.
        """
        try:
#           packet = payload.to_bytes()
            packet = bytes(payload)
            if not packet.startswith(Payload.SYNC_HEADER):
                packet = Payload.SYNC_HEADER + packet[len(Payload.SYNC_HEADER):]
            self.uart.write(packet)
            if self._verbose:
                self._log.info("Sent packet: {}".format(packet))
#           self.flash_led()
        except Exception as e:
            self._log.error("Failed to send packet: {}".format(e))

#EOF
