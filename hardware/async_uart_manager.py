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

import serial
import asyncio
from threading import Thread
from concurrent.futures import ThreadPoolExecutor
from colorama import init, Fore, Style
init()

from hardware.payload import Payload
from core.logger import Logger, Level
import time

class AsyncUARTManager:
    def __init__(self, port='/dev/serial0', baudrate=115200, timeout=1):
        self._log = Logger('async-uart-mgr', Level.INFO)
        self._port_name = port
        self._baudrate  = baudrate
        self._timeout   = timeout
        self._serial    = None
        self._log.info('using port {} at {} baud.'.format(port, baudrate))
        self._executor  = ThreadPoolExecutor(max_workers=1)
        # dedicated asyncio loop and thread
        self._loop = asyncio.new_event_loop()
        self._loop_thread = Thread(target=self._loop.run_forever, daemon=True)
        self._loop_thread.start()
        self._log.info('ready.')
        # Buffer for sync-header-based framing
        self._rx_buffer = bytearray()
        self._rx_timeout = 0.25  # seconds
        self._log.info('ready.')

    def open(self):
        if self._serial is None or not self._serial.is_open:
            self._serial = serial.Serial(self._port_name, self._baudrate, timeout=self._timeout)
            self._log.info("serial port {} opened.".format(self._port_name))
            
    def close(self):
        if self._serial and self._serial.is_open:
            self._serial.close()
            self._log.info("serial port closed.")
        self._executor.shutdown(wait=False)
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._loop_thread.join()
        
    def _send_packet_sync(self, payload):
        packet_bytes = payload.to_bytes()
        # ensure sync header is present for robust protocol
        if not packet_bytes.startswith(Payload.SYNC_HEADER):
            packet_bytes = Payload.SYNC_HEADER + packet_bytes[len(Payload.SYNC_HEADER):]
        self._serial.write(packet_bytes)
        self._serial.flush()
#       self._log.info(Style.DIM + "sent: {}".format(repr(payload)))

    def send_packet(self, payload):
        '''
        Synchronous wrapper: schedule async send on background loop.
        '''
        self._log.debug('send payload.')
        future = asyncio.run_coroutine_threadsafe(
            self._send_packet_async(payload), self._loop)
        return future.result() # wait for completion
        
    async def _send_packet_async(self, payload):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self._executor, self._send_packet_sync, payload)
        
    def _receive_packet_sync(self):
        '''
        Reads bytes, synchronizes on sync header, and returns the first valid Payload found.
        '''
        start_time = time.time()
        while True:
            if self._serial.in_waiting:
                data = self._serial.read(self._serial.in_waiting)
#               self._log.debug(f"RAW RX BYTES: {data.hex()}")
                self._rx_buffer += data
                self._log.debug('read {} bytes from serial; buffer size now: {}'.format(len(data), len(self._rx_buffer)))
                start_time = time.time()
            idx = self._rx_buffer.find(Payload.SYNC_HEADER)
            if idx == -1:
                # not found: trim buffer if too large
                if len(self._rx_buffer) > len(Payload.SYNC_HEADER):
                    self._rx_buffer = self._rx_buffer[-(len(Payload.SYNC_HEADER)-1):]
                time.sleep(0.005)
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
                    self._log.debug("received: {}".format(repr(payload)))
                    return payload
                except ValueError as e:
                    self._log.error("receive error: {}. Resyncing...".format(e))
                    # remove just the first header byte to attempt resync
                    self._rx_buffer = self._rx_buffer[idx+1:]
                    continue
            else:
                # not enough bytes yet for a full packet
                time.sleep(0.005)
                if time.time() - start_time > self._rx_timeout:
                    self._log.error('UART RX timeout; incomplete packet, clearing buffer.')
                    self._rx_buffer = bytearray()
                    start_time = time.time()
                continue
        
    def receive_packet(self):
        '''
        Synchronous wrapper: schedule async receive on background loop.
        '''
        self._log.debug('receive packet.')
        future = asyncio.run_coroutine_threadsafe(
            self._receive_packet_async(), self._loop)
        return future.result()
        
    async def _receive_packet_async(self):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, self._receive_packet_sync)
    
    def receive_values(self):
        '''
        Convenience method to receive a Payload and return the tuple (cmd, pfwd, sfwd, paft, saft).
        '''
        payload = self.receive_packet()
        if payload:
            return (payload.cmd.decode('ascii'), payload.pfwd, payload.sfwd, payload.paft, payload.saft)
        return None

#EOF
