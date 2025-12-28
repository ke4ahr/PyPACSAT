# PyAGW3/agwpe.py
# GNU General Public License v3.0
# Copyright (C) 2025-2026 Kris Kirby, KE4AHR
#
# AGWPE TCP/IP API client
# Full implementation with unproto, connected mode, raw, outstanding frames

import socket
import struct
import threading
import time
import logging
from typing import Optional, Callable

logger = logging.getLogger('AGWPE')

AGWPE_DEFAULT_PORT = 8000

class AGWPEFrame:
    """AGWPE frame structure."""
    port: int
    data_kind: bytes
    call_from: bytes
    call_to: bytes
    data_len: int
    data: bytes

class AGWPEClient:
    """
    Full AGWPE TCP/IP API client.
    Supports unproto, connected mode, raw frames, outstanding queries.
    """
    def __init__(self, host: str = "127.0.0.1", port: int = AGWPE_DEFAULT_PORT, callsign: str = "NOCALL"):
        self.host = host
        self.port = port
        self.callsign = callsign.ljust(10)[:10].upper().encode()
        self.sock: Optional[socket.socket] = None
        self.connected = False
        self.on_frame: Optional[Callable[[AGWPEFrame], None]] = None
        self.on_connected_data: Optional[Callable[[int, str, bytes], None]] = None
        self.on_outstanding: Optional[Callable[[int, int], None]] = None
        self.thread: Optional[threading.Thread] = None
        self.lock = threading.RLock()

    def connect(self) -> bool:
        """Connect and register callsign."""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            
            # Register callsign (R frame)
            self._send_frame(data_kind=b'R', call_from=self.callsign)
            
            self.connected = True
            self.thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.thread.start()
            
            logger.info(f"[AGWPE] Connected to {self.host}:{self.port} as {self.callsign.decode()}")
            return True
            
        except Exception as e:
            logger.error(f"[AGWPE] Connection failed: {e}")
            return False

    def _send_frame(self, data_kind: bytes, port: int = 0, call_from: bytes = b'', call_to: bytes = b'', data: bytes = b''):
        """Send raw AGWPE frame."""
        if not self.connected or not self.sock:
            return
        
        with self.lock:
            try:
                # Header (36 bytes)
                header = bytearray(36)
                header[0:1] = data_kind
                struct.pack_into('<I', header, 4, port)
                header[8:18] = call_from.ljust(10, b' ')[:10]
                header[18:28] = call_to.ljust(10, b' ')[:10]
                struct.pack_into('<I', header, 28, len(data))
                
                self.sock.sendall(header + data)
                
                logger.debug(f"[AGWPE] Sent {data_kind.decode()} frame on port {port}")
                
            except Exception as e:
                logger.error(f"[AGWPE] Send failed: {e}")
                self.connected = False

    def send_ui(self, port: int, dest: str, src: str, pid: int, info: bytes = b''):
        """Send unproto UI frame ('D')."""
        self._send_frame(
            data_kind=b'D',
            port=port,
            call_from=src.upper().ljust(10)[:10].encode(),
            call_to=dest.upper().ljust(10)[:10].encode(),
            data=bytes([pid]) + info
        )

    def send_raw_unproto(self, port: int, dest: str, src: str, data: bytes):
        """Send raw unproto frame ('K') - no PID."""
        self._send_frame(
            data_kind=b'K',
            port=port,
            call_from=src.upper().ljust(10)[:10].encode(),
            call_to=dest.upper().ljust(10)[:10].encode(),
            data=data
        )

    def send_monitor(self, port: int):
        """Enable monitoring on port ('M')."""
        self._send_frame(data_kind=b'M', port=port)

    def request_outstanding(self, port: int = 0):
        """Request outstanding frames ('Y')."""
        self._send_frame(data_kind=b'Y', port=port)

    def send_connect(self, port: int, dest: str):
        """Initiate connected mode ('C')."""
        self._send_frame(
            data_kind=b'C',
            port=port,
            call_from=self.callsign,
            call_to=dest.upper().ljust(10)[:10].encode()
        )

    def send_disconnect(self, port: int, dest: str):
        """Send disconnect ('D')."""
        self._send_frame(
            data_kind=b'D',
            port=port,
            call_from=self.callsign,
            call_to=dest.upper().ljust(10)[:10].encode()
        )

    def send_connected_data(self, port: int, dest: str, data: bytes):
        """Send connected data ('d')."""
        self._send_frame(
            data_kind=b'd',
            port=port,
            call_from=self.callsign,
            call_to=dest.upper().ljust(10)[:10].encode(),
            data=data
        )

    def _receive_loop(self):
        """Receive and parse AGWPE frames."""
        buffer = b''
        while self.connected:
            try:
                data = self.sock.recv(4096)
                if not data:
                    logger.warning("[AGWPE] Connection closed by server")
                    self.connected = False
                    break
                
                buffer += data
                
                while len(buffer) >= 36:
                    header = buffer[:36]
                    data_kind = header[0:1]
                    port = struct.unpack('<I', header[4:8])[0]
                    call_from = header[8:18].decode('ascii', errors='ignore').strip()
                    call_to = header[18:28].decode('ascii', errors='ignore').strip()
                    data_len = struct.unpack('<I', header[28:32])[0]
                    
                    if len(buffer) < 36 + data_len:
                        break
                    
                    payload = buffer[36:36 + data_len]
                    buffer = buffer[36 + data_len:]
                    
                    frame = AGWPEFrame()
                    frame.port = port
                    frame.data_kind = data_kind
                    frame.call_from = call_from.encode()
                    frame.call_to = call_to.encode()
                    frame.data_len = data_len
                    frame.data = payload
                    
                    # Route frame
                    if data_kind in [b'D', b'K']:
                        if self.on_frame:
                            self.on_frame(frame)
                    elif data_kind == b'd':
                        if self.on_connected_data:
                            self.on_connected_data(port, call_from, payload)
                    elif data_kind == b'Y':
                        if self.on_outstanding and payload:
                            count = struct.unpack('<I', payload[:4])[0]
                            self.on_outstanding(port, count)
                    elif data_kind in [b'C', b'c', b'D']:
                        # Connected control frames
                        if self.on_frame:
                            self.on_frame(frame)
                    
                    logger.debug(f"[AGWPE] Received {data_kind.decode()} frame from {call_from} to {call_to}")
                    
            except Exception as e:
                logger.error(f"[AGWPE] Receive error: {e}")
                self.connected = False
                break

    def close(self):
        """Close connection."""
        self.connected = False
        if self.sock:
            self.sock.close()
        logger.info("[AGWPE] Disconnected")

# DOC: Full AGWPE TCP client with unproto, connected mode, raw frames, outstanding queries
# DOC: Supports all implemented frame types from current project
# DOC: Single application only - multiple app support requires further research
