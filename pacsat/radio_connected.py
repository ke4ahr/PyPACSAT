# pacsat/radio_connected.py
# GNU General Public License v3.0
# Copyright (C) 2025-2026 Kris Kirby, KE4AHR
#
# AX.25 Connected Mode Support (Optional)
# Implements SABM/UA/DISC/I-frames for legacy compatibility
# Not used by PACSAT (unproto only) but available when enabled

import time
import logging
from typing import Dict, Optional

logger = logging.getLogger('ConnectedMode')

class ConnectedSession:
    """Track state of one connected AX.25 session."""
    STATES = ["DISCONNECTED", "CONNECTING", "CONNECTED", "DISCONNECTING"]
    
    def __init__(self, remote_callsign: str, port: int):
        self.remote_callsign = remote_callsign
        self.port = port
        self.state = "DISCONNECTED"
        self.vr = 0  # Receive sequence number
        self.vs = 0  # Send sequence number
        self.pending_data = []
        self.last_activity = time.time()

class ConnectedModeHandler:
    """
    Handle AX.25 connected mode sessions.
    Integrated with radio interface (serial or TCP).
    """
    def __init__(self, radio):
        self.radio = radio
        self.sessions: Dict[tuple, ConnectedSession] = {}
        logger.info("[ConnectedMode] Handler initialized")

    def initiate_connect(self, remote_callsign: str, port: int) -> bool:
        """Send SABM to initiate connection."""
        key = (remote_callsign.upper(), port)
        if key in self.sessions:
            logger.warning(f"[ConnectedMode] Session already exists for {remote_callsign} on port {port}")
            return False
        
        session = ConnectedSession(remote_callsign.upper(), port)
        session.state = "CONNECTING"
        self.sessions[key] = session
        
        # Send SABM (P=1)
        self.radio.send_control_frame(
            port=port,
            dest=remote_callsign,
            src=self.radio.config.callsign,
            control=b'\x2F'  # SABM with P=1
        )
        
        logger.info(f"[ConnectedMode] Initiated connection to {remote_callsign} on port {port}")
        return True

    def handle_frame(self, frame):
        """Process incoming connected mode frame."""
        control = frame.info[0] if frame.info else 0
        
        if control == 0x2F:  # SABM received
            self._handle_sabm(frame)
        elif control == 0x63:  # UA received
            self._handle_ua(frame)
        elif control == 0x73:  # DISC received
            self._handle_disc(frame)
        elif (control & 0x01) == 0:  # I-frame
            self._handle_i_frame(frame)
        # Additional: RR, RNR, REJ supervisory frames can be added

    def _handle_sabm(self, frame):
        """Incoming connection request."""
        key = (frame.call_from.decode('ascii', errors='ignore').strip(), frame.port)
        if key in self.sessions:
            # Already connected - respond UA
            self._send_ua(frame.port, frame.call_from.decode())
            return
        
        session = ConnectedSession(frame.call_from.decode('ascii', errors='ignore').strip(), frame.port)
        session.state = "CONNECTED"
        self.sessions[key] = session
        
        self._send_ua(frame.port, frame.call_from.decode())
        logger.info(f"[ConnectedMode] Accepted connection from {session.remote_callsign} on port {frame.port}")

    def _send_ua(self, port: int, dest_callsign: str):
        """Send Unnumbered Acknowledgment."""
        self.radio.send_control_frame(
            port=port,
            dest=dest_callsign,
            src=self.radio.config.callsign,
            control=b'\x63'  # UA with F=1
        )

    def _handle_ua(self, frame):
        """Connection confirmed."""
        key = (frame.call_to.decode('ascii', errors='ignore').strip(), frame.port)
        session = self.sessions.get(key)
        if session and session.state == "CONNECTING":
            session.state = "CONNECTED"
            logger.info(f"[ConnectedMode] Connection established with {session.remote_callsign}")

    def _handle_disc(self, frame):
        """Disconnect request received."""
        key = (frame.call_from.decode('ascii', errors='ignore').strip(), frame.port)
        session = self.sessions.pop(key, None)
        if session:
            logger.info(f"[ConnectedMode] Disconnected from {session.remote_callsign}")
        
        # Respond UA to DISC
        self._send_ua(frame.port, frame.call_from.decode())

    def _handle_i_frame(self, frame):
        """Handle connected data frame."""
        key = (frame.call_from.decode('ascii', errors='ignore').strip(), frame.port)
        session = self.sessions.get(key)
        if not session or session.state != "CONNECTED":
            return
        
        # Extract N(R), N(S), P/F
        control = frame.info[0]
        ns = (control >> 1) & 0x07
        nr = (control >> 5) & 0x07
        
        # Basic acknowledgment - send RR
        self._send_rr(frame.port, frame.call_from.decode(), nr)
        
        # Payload after control byte
        payload = frame.info[1:]
        
        if self.radio.on_connected_data:
            self.radio.on_connected_data(frame.port, frame.call_from.decode(), payload)

    def _send_rr(self, port: int, dest_callsign: str, nr: int):
        """Send Receiver Ready supervisory frame."""
        control = 0x01 | (nr << 5)  # RR with N(R)
        self.radio.send_control_frame(
            port=port,
            dest=dest_callsign,
            src=self.radio.config.callsign,
            control=bytes([control])
        )

    def send_connected_data(self, remote_callsign: str, port: int, data: bytes) -> bool:
        """Send data in connected session."""
        key = (remote_callsign.upper(), port)
        session = self.sessions.get(key)
        if not session or session.state != "CONNECTED":
            logger.warning(f"[ConnectedMode] No active session for {remote_callsign}")
            return False
        
        # Build I-frame control byte: N(S) in bits 1-3, P/F=0
        control = (session.vs << 1)
        session.vs = (session.vs + 1) % 8
        
        full_info = bytes([control]) + data
        
        self.radio.send_data_frame(
            port=port,
            dest=remote_callsign,
            src=self.radio.config.callsign,
            pid=0xF0,  # No layer 3 protocol
            info=full_info
        )
        
        session.last_activity = time.time()
        return True

    def disconnect(self, remote_callsign: str, port: int):
        """Initiate disconnect."""
        key = (remote_callsign.upper(), port)
        session = self.sessions.get(key)
        if not session:
            return
        
        session.state = "DISCONNECTING"
        
        # Send DISC (P=1)
        self.radio.send_control_frame(
            port=port,
            dest=remote_callsign,
            src=self.radio.config.callsign,
            control=b'\x43'  # DISC with P=1
        )
        
        # DOC: Cleanup after timeout or UA
        # DOC: (can be enhanced with timer)

# DOC: Connected mode is optional and disabled by default in the ground station
# DOC: PACSAT satellites used only unproto UI frames (PID 0xBB/0xBD)
# DOC: This module provides compatibility with legacy packet applications
