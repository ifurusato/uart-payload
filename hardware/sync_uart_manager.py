#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2025 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2025-06-23
# modified: 2025-06-23

import serial
import time
from colorama import init, Fore, Style
init()

from hardware.payload import Payload
from core.logger import Logger, Level

class SyncUARTManager:
    def __init__(self, port='/dev/serial0', baudrate=115200, timeout=0.001):
        self._log = Logger('sync-uart-mgr', Level.INFO)
        self._port_name  = port
        self._baudrate   = baudrate
        self._timeout    = timeout
        self._serial     = None
        self._log.info('using port {} at {} baud.'.format(port, baudrate))
        # Buffer for sync-header-based framing
        self._rx_buffer  = bytearray()
        self._rx_timeout = 0.015 # 15ms
        self._log.info('ready.')

    def open(self):
        if self._serial is None or not self._serial.is_open:
            self._serial = serial.Serial(self._port_name, self._baudrate, timeout=self._timeout)
            self._log.info("serial port {} opened.".format(self._port_name))
            
    def close(self):
        if self._serial and self._serial.is_open:
            self._serial.close()
            self._log.info("serial port closed.")

    def send_packet(self, payload):
        packet_bytes = payload.to_bytes()
        # ensure sync header is present for robust protocol
        if not packet_bytes.startswith(Payload.SYNC_HEADER):
            packet_bytes = Payload.SYNC_HEADER + packet_bytes[len(Payload.SYNC_HEADER):]
        self._serial.write(packet_bytes)
        self._serial.flush()
        # self._log.info(Style.DIM + "sent: {}".format(repr(payload)))

    def receive_packet(self):
        '''Reads bytes, synchronizes on sync header, and returns the first valid Payload found.'''
        start_time = time.time()
        while True:
            if self._serial.in_waiting:
                data = self._serial.read(self._serial.in_waiting)
                self._rx_buffer += data
                start_time = time.time()
            idx = self._rx_buffer.find(Payload.SYNC_HEADER)
            if idx == -1:
                # not found: trim buffer if too large
                if len(self._rx_buffer) > len(Payload.SYNC_HEADER):
                    self._rx_buffer = self._rx_buffer[-(len(Payload.SYNC_HEADER)-1):]
                # tight loop, no sleep
                if time.time() - start_time > self._rx_timeout:
                    self._log.error("UART RX timeout; sync header not found, clearing buffer.")
                    self._rx_buffer = bytearray()
                    start_time = time.time()
                continue
            # found sync header: do we have a full packet?
            if len(self._rx_buffer) - idx >= Payload.PACKET_SIZE:
                packet = self._rx_buffer[idx: idx + Payload.PACKET_SIZE]
                self._rx_buffer = self._rx_buffer[idx + Payload.PACKET_SIZE:]
                try:
                    payload = Payload.from_bytes(packet)
                    return payload
                except ValueError as e:
                    self._log.error("receive error: {}. Resyncing...".format(e))
                    # remove just the first header byte to attempt resync
                    self._rx_buffer = self._rx_buffer[idx+1:]
                    continue
            else:
                # not enough bytes yet for a full packet
                # tight loop, no sleep
                if time.time() - start_time > self._rx_timeout:
                    self._log.error('UART RX timeout; incomplete packet, clearing buffer.')
                    self._rx_buffer = bytearray()
                    start_time = time.time()
                continue

    def receive_values(self):
        '''Convenience method to receive a Payload and return the tuple (cmd, pfwd, sfwd, paft, saft).'''
        payload = self.receive_packet()
        if payload:
            return (payload.cmd.decode('ascii'), payload.pfwd, payload.sfwd, payload.paft, payload.saft)
        return None

#EOF
