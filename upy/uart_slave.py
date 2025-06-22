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

from machine import UART, Pin
import time
from core.logger import Logger, Level
from payload import Payload, SYNC_HEADER

class UARTSlave:
    def __init__(self, uart_id=1, baudrate=115200, rx_pin=5, tx_pin=4, led_pin=25):
        self._log = Logger('uart-slave', Level.INFO)
        self.baudrate = baudrate
        self.uart_id  = uart_id
        self.rx_pin   = rx_pin
        self.tx_pin   = tx_pin
        self.led_pin  = led_pin  # Pin for the LED
        self._log.info('pins: rx={}; tx={}.'.format(rx_pin, tx_pin))
        # set up LED pin
        self.led = Pin(self.led_pin, Pin.OUT)
        # set up UART connection with custom TX and RX pins
        self.uart = UART(self.uart_id, baudrate=self.baudrate, bits=8, parity=None, stop=1, tx=Pin(self.tx_pin), rx=Pin(self.rx_pin))
        self._verbose = False
        self._log.info('UART slave ready at baud rate: {}.'.format(baudrate))
        # Buffer and timing for sync protocol
        self._buffer = bytearray()
        self._last_rx = time.ticks_ms()
        self._timeout_ms = 250  # ms

    def set_verbose(self, verbose: bool):
        self._verbose = verbose

    def flash_led(self, duration_ms=50):
        self.led.value(1)
        time.sleep_ms(duration_ms)
        self.led.value(0)

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
            idx = self._buffer.find(SYNC_HEADER)
            if idx == -1:
                # Trim buffer so it doesn't grow unbounded
                if len(self._buffer) > len(SYNC_HEADER):
                    if self._verbose:
                        self._log.debug("Sync header not found; trimming buffer")
                    self._buffer = self._buffer[-(len(SYNC_HEADER)-1):]
                continue

            # Check if enough bytes for a packet
            if len(self._buffer) - idx >= Payload.PACKET_SIZE:
                packet = self._buffer[idx: idx + Payload.PACKET_SIZE]
                self._buffer = self._buffer[idx + Payload.PACKET_SIZE:]
                try:
                    pl = Payload.from_bytes(packet)
                    if self._verbose:
                        self._log.info("Valid packet received: {}".format(pl))
                    self.flash_led()
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
            packet = payload.to_bytes()
            if not packet.startswith(SYNC_HEADER):
                packet = SYNC_HEADER + packet[len(SYNC_HEADER):]
            self.uart.write(packet)
            if self._verbose:
                self._log.info("Sent packet: {}".format(packet))
            self.flash_led()
        except Exception as e:
            self._log.error("Failed to send packet: {}".format(e))

#EOF
