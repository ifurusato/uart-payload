
*****************************************************************
UART Payload
*****************************************************************

A simple UART that passes a Payload object between master and slave.

The Payload is comprised of a two character command and four float values::

    payload = Payload("MO", 10.0, 20.0, -10.0, -20.0)

The master sends a Payload to the slave, which responds with a Payload.

Hardware Configuration
**********************

While you can certainly change pin assignments, the current ones are::

    Raspberry Pi ->  Pico RP2040 
    GPIO 14 TX   ->  GP4 UART1 RX
    GPIO 15 TX   ->  GP5 UART1 RX


Payload Protocol
****************

Protocol Change: Files to Update for Sync Header
================================================

+-----------------------------------------+----------------+-----------------------------------------------------------+
| File                                   | Change Needed? | Notes                                                     |
+=========================================+================+===========================================================+
| ``payload.py`` (shared)                 | YES            | Add/use SYNC_HEADER, update (de)serialization             |
+-----------------------------------------+----------------+-----------------------------------------------------------+
| ``upy/uart_slave.py``                   | YES            | Read and search for sync header in input stream           |
+-----------------------------------------+----------------+-----------------------------------------------------------+
| ``hardware/async_uart_manager.py``      | YES            | Prepend sync header on send, search for it on receive     |
+-----------------------------------------+----------------+-----------------------------------------------------------+
| ``hardware/uart_master.py``             | MAYBE          | Only if direct byte stream manipulation is done           |
+-----------------------------------------+----------------+-----------------------------------------------------------+
| ``upy/main.py``                         | NO             | Protocol remains the same, just instantiates slave        |
+-----------------------------------------+----------------+-----------------------------------------------------------+
| ``README.rst``                          | OPTIONAL       | Good practice to document protocol change                 |
+-----------------------------------------+----------------+-----------------------------------------------------------+

Notes:
 - The ``payload.py`` file is shared between master and slave environments.


Files
*****

+--------------------------------+----------------------------------------------+
| file                           | description                                  |
+================================+==============================================+
| master_test.py                 | test script                                  |
+--------------------------------+----------------------------------------------+
| install_uart_access.sh         | script to enable non-sudo access to UART     |
+--------------------------------+----------------------------------------------+
| core/logger.py                 | application console logger                   |
+--------------------------------+----------------------------------------------+
| hardware/uart_master.py        | UART master class                            |
+--------------------------------+----------------------------------------------+
| hardware/payload.py            | payload passed on transactions               |
+--------------------------------+----------------------------------------------+
| hardware/async_uart_manager.py | asynchronous UART manager                    |
+--------------------------------+----------------------------------------------+

Files to be copied to RP2040:

+--------------------------------+----------------------------------------------+
| upy/BOARD                      | board identifier                             |
+--------------------------------+----------------------------------------------+
| upy/main.py                    | main to be run on RP2040                     |
+--------------------------------+----------------------------------------------+
| upy/colorama.py                | mcu version of colorama                      |
+--------------------------------+----------------------------------------------+
| upy/payload.py                 | payload passed on transactions               |
+--------------------------------+----------------------------------------------+
| upy/core/logger.py             | application core logger                      |
+--------------------------------+----------------------------------------------+
| upy/uart_slave.py              | UART slave class                             |
+--------------------------------+----------------------------------------------+


Status
******

The code is new, but functional.


Support & Liability
*******************

This project comes with no promise of support or acceptance of liability. Use at
your own risk.


Copyright & License
*******************

All contents (including software, documentation and images) Copyright 2020-2025
by Murray Altheim. All rights reserved.

Software and documentation are distributed under the MIT License, see LICENSE
file included with project.

