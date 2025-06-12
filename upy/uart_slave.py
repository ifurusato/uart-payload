#!/micropython
# -*- coding: utf-8 -*-
#
# Copyright 2020-2025 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2025-06-12
# modified: 2025-06-12

from machine import UART, Pin
import time
from payload import Payload
from core.logger import Logger, Level

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

    def receive_packet(self):
        self.led.on()  # Turn on the LED at the start of receiving a packet
        buf = bytearray()
        while len(buf) < Payload.PACKET_SIZE:
            if self.uart.any():
                buf.extend(self.uart.read(1))
            else:
                time.sleep(0.01) # avoid busy wait
        if self._verbose:
            self._log.debug("raw packet: {}".format(' '.join("{:02X}".format(b) for b in buf)))
        # check CRC
        received_crc = buf[-1]
        computed_crc = Payload.calculate_crc8(buf[:-1])
        if self._verbose:
            self._log.debug("received CRC: {:02X}, Computed CRC: {:02X}".format(received_crc, computed_crc))
        if received_crc != computed_crc:
            self._log.error("CRC mismatch!")
            return None
        try:
            # Decode the packet to a Payload object
            payload = Payload.from_bytes(buf)
            if self._verbose:
                self._log.info("received: {}".format(payload))  # debug print for confirmation
            return payload
        except Exception as e:
            self._log.error("error during payload decoding: {}".format(e))
            return None
        finally:
            self.led.off()

    def send_packet(self, payload):
        packet = payload.to_bytes()  # Directly call to_bytes() method
        if not isinstance(packet, (bytes, bytearray)):
            self._log.error("packet is not a byte-like object:", type(packet))
            return  # Or handle as needed
#       self._log.debug("sending packet: {} (type: {})".format(packet, type(packet)))  # Debugging the packet content and type
        self.uart.write(packet)  # Send the byte data to UART
        if self._verbose:
            self._log.info("sent: {}".format(payload))  # debug print for confirmation

#EOF
