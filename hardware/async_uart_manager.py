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
        self.port_name = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None
        self._log.info('using port {} at baud rate of {}'.format(port, baudrate))
        self.executor = ThreadPoolExecutor(max_workers=1)
        # dedicated asyncio loop and thread
        self.loop = asyncio.new_event_loop()
        self.loop_thread = Thread(target=self.loop.run_forever, daemon=True)
        self.loop_thread.start()
        self._log.info('ready.')
        # Buffer for sync-header-based framing
        self._rx_buffer = bytearray()
        self._rx_timeout = 0.25  # seconds
        self._log.info('ready.')

    def open(self):
        print('🌸 open')
        if self.ser is None or not self.ser.is_open:
            self.ser = serial.Serial(self.port_name, self.baudrate, timeout=self.timeout)
            self._log.info("serial port {} opened.".format(self.port_name))
            
    def close(self):
        print('🌸 close')
        if self.ser and self.ser.is_open:
            self.ser.close()
            self._log.info("serial port closed.")
        self.executor.shutdown(wait=False)
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.loop_thread.join()
        
    def _send_packet_sync(self, payload):
        packet_bytes = bytes(payload)  # Calls __bytes__ internally or to_bytes explicitly
        # Ensure sync header is present for robust protocol
        if not packet_bytes.startswith(Payload.SYNC_HEADER):
            packet_bytes = Payload.SYNC_HEADER + packet_bytes[len(Payload.SYNC_HEADER):]
        self.ser.write(packet_bytes)
        self.ser.flush()
        self._log.info(Style.DIM + "sent: {}".format(repr(payload)))

    def send_packet(self, payload):
        '''
        Synchronous wrapper: schedule async send on background loop.
        '''
        print('🌸 send_packet')
        future = asyncio.run_coroutine_threadsafe(
            self._send_packet_async(payload), self.loop)
        return future.result()  # wait for completion
        
    async def _send_packet_async(self, payload):
        print('🌸 _send_packet_async')
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(self.executor, self._send_packet_sync, payload)
        
    def _receive_packet_sync(self):
        '''
        Reads bytes, synchronizes on sync header, and returns the first valid Payload found.
        '''
        print('🌸 a. _receive_packet_sync')
        start_time = time.time()
        while True:
            if self.ser.in_waiting:
                data = self.ser.read(self.ser.in_waiting)
                self._rx_buffer += data
                self._log.debug('read {} bytes from serial; buffer size now: {}'.format(len(data), len(self._rx_buffer)))
                start_time = time.time()
            idx = self._rx_buffer.find(Payload.SYNC_HEADER)
            if idx == -1:
                # not found: trim buffer if too large
                if len(self._rx_buffer) > len(Payload.SYNC_HEADER):
                    print('🌸 b. _receive_packet_sync too large')
                    self._rx_buffer = self._rx_buffer[-(len(Payload.SYNC_HEADER)-1):]
                time.sleep(0.005)
                if time.time() - start_time > self._rx_timeout:
                    self._log.error("UART RX timeout; sync header not found, clearing buffer.")
                    self._rx_buffer = bytearray()
                    start_time = time.time()
                continue
            # found sync header: do we have a full packet?
            if len(self._rx_buffer) - idx >= Payload.PACKET_SIZE:
                print('🌸 c. _receive_packet_sync header')
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
                print('🌸 d. _receive_packet_sync filling...')
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
        print('🌸 receive_packet')
        future = asyncio.run_coroutine_threadsafe(
            self._receive_packet_async(), self.loop)
        return future.result()
        
    async def _receive_packet_async(self):
        print('🌸 _receive_packet_async')
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self.executor, self._receive_packet_sync)
    
    def receive_values(self):
        '''
        Convenience method to receive a Payload and return the tuple (cmd, pfwd, sfwd, paft, saft).
        '''
        print('🌸 receive_values')
        payload = self.receive_packet()
        if payload:
            return (payload.cmd.decode('ascii'), payload.pfwd, payload.sfwd, payload.paft, payload.saft)
        return None

#EOF
