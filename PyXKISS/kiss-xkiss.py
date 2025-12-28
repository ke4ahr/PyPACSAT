# PyXKISS/kiss-xkiss.py
# GNU General Public License v3.0
# Copyright (C) 2025-2026 Kris Kirby, KE4AHR
#
# KISS/XKISS protocol implementation
# Standard KISS + Extended KISS + Polled mode
# For serial radio/TNC interface

import serial
import time
import logging
from typing import Optional, Callable

logger = logging.getLogger('XKISS')

FEND = 0xC0
FESC = 0xDB
TFEND = 0xDC
TFESC = 0xDD

class XKISSRadio:
    """
    XKISS serial radio interface.
    Supports standard KISS, extended KISS, and polled mode for multi-TNC.
    """
    def __init__(self, device: str, baudrate: int = 9600, polled: bool = False):
        self.serial = serial.Serial(device, baudrate, timeout=1)
        self.polled = polled
        self.on_frame: Optional[Callable[[bytes], None]] = None
        self.buffer = bytearray()
        self.last_poll_time = 0
        self.poll_interval = 0.1  # 100ms
        
        # Start receive loop
        threading.Thread(target=self._receive_loop, daemon=True).start()
        
        logger.info(f"[XKISS] Initialized on {device} at {baudrate} baud (polled: {polled})")

    def send_frame(self, data: bytes, cmd: int = 0):
        """Send KISS frame with optional command byte."""
        kiss_data = bytearray([FEND, cmd])
        for byte in data:
            if byte == FEND:
                kiss_data.extend([FESC, TFEND])
            elif byte == FESC:
                kiss_data.extend([FESC, TFESC])
            else:
                kiss_data.append(byte)
        kiss_data.append(FEND)
        self.serial.write(kiss_data)

    def _receive_loop(self):
        """Receive and parse KISS frames."""
        while True:
            try:
                byte = self.serial.read(1)
                if byte:
                    self._process_byte(byte[0])
            except Exception as e:
                logger.error(f"[XKISS] Receive error: {e}")
                break

    def _process_byte(self, byte: int):
        """Process incoming byte for KISS deframing."""
        if byte == FEND:
            if len(self.buffer) > 1:
                # Extract command and data
                cmd = self.buffer[0]
                data = self.buffer[1:]
                # Destuff
                destuffed = bytearray()
                i = 0
                while i < len(data):
                    if data[i] == FESC:
                        i += 1
                        if i < len(data):
                            if data[i] == TFEND:
                                destuffed.append(FEND)
                            elif data[i] == TFESC:
                                destuffed.append(FESC)
                            else:
                                destuffed.append(data[i])
                    else:
                        destuffed.append(data[i])
                    i += 1
                
                if self.on_frame:
                    self.on_frame(bytes(destuffed))
            
            self.buffer = bytearray()
        else:
            self.buffer.append(byte)

    def poll(self):
        """Send poll in polled mode."""
        if self.polled and time.time() - self.last_poll_time > self.poll_interval:
            self.serial.write(bytes([FEND, 0x0F, FEND]))  # Poll command
            self.last_poll_time = time.time()

    def close(self):
        """Close serial port."""
        if self.serial.is_open:
            self.serial.close()
        logger.info("[XKISS] Closed")

# DOC: XKISS radio interface for serial TNC
# DOC: Standard KISS (cmd=0), extended commands, polled mode for multi-TNC
# DOC: Integrates with groundstation radio init
