# pacsat/telemetry.py
# GNU General Public License v3.0
# Copyright (C) 2025-2026 Kris Kirby, KE4AHR
#
# PACSAT Telemetry Parsing
# Supports Whole Orbit Data (WOD) and realtime telemetry frames
# PID values: 0xB0 (WOD), 0xB1 (Realtime)

import struct
import time
from typing import Dict, Optional

class PACSTATTelemetry:
    """
    Parse PACSAT telemetry frames.
    Supports Whole Orbit Data (WOD) and realtime telemetry.
    """
    
    # Common telemetry PID values
    WOD_PID = 0xB0
    REALTIME_PID = 0xB1
    
    def __init__(self):
        self.last_wod: Optional[Dict] = None
        self.last_realtime: Optional[Dict] = None
    
    def parse_frame(self, pid: int, data: bytes) -> Optional[Dict]:
        """Parse telemetry frame by PID."""
        if pid == self.WOD_PID:
            return self._parse_wod(data)
        elif pid == self.REALTIME_PID:
            return self._parse_realtime(data)
        return None
    
    def _parse_wod(self, data: bytes) -> Optional[Dict]:
        """Parse Whole Orbit Data (WOD)."""
        if len(data) < 64:
            return None
        
        try:
            telemetry = {
                "type": "WOD",
                "timestamp": int(time.time()),
                "battery_voltage": struct.unpack('<H', data[0:2])[0] / 100.0,   # V
                "battery_current": struct.unpack('<H', data[2:4])[0] / 100.0,   # A
                "solar_panel_x": struct.unpack('<H', data[4:6])[0] / 100.0,
                "solar_panel_y": struct.unpack('<H', data[6:8])[0] / 100.0,
                "solar_panel_z": struct.unpack('<H', data[8:10])[0] / 100.0,
                "temp_transmitter": struct.unpack('<h', data[10:12])[0] / 10.0, # °C
                "temp_receiver": struct.unpack('<h', data[12:14])[0] / 10.0,
                "temp_battery": struct.unpack('<h', data[14:16])[0] / 10.0,
                "rx_doppler": struct.unpack('<h', data[16:18])[0],
                "tx_power": struct.unpack('<H', data[18:20])[0] / 10.0,         # W
                "uptime_seconds": struct.unpack('<I', data[20:24])[0],
                "reboots": struct.unpack('<H', data[24:26])[0],
                "mode": data[26],  # 0=safe, 1=science, etc.
            }
            
            self.last_wod = telemetry
            return telemetry
        except Exception:
            return None
    
    def _parse_realtime(self, data: bytes) -> Optional[Dict]:
        """Parse realtime telemetry."""
        if len(data) < 32:
            return None
        
        try:
            telemetry = {
                "type": "Realtime",
                "timestamp": int(time.time()),
                "battery_voltage": struct.unpack('<H', data[0:2])[0] / 100.0,
                "bus_current": struct.unpack('<H', data[2:4])[0] / 100.0,
                "temp_pa": struct.unpack('<h', data[4:6])[0] / 10.0,
                "temp_rx": struct.unpack('<h', data[6:8])[0] / 10.0,
                "rssi": struct.unpack('<H', data[8:10])[0],
                "channel_activity": data[10],
            }
            
            self.last_realtime = telemetry
            return telemetry
        except Exception:
            return None
    
    def get_status_summary(self) -> Dict:
        """Return current satellite status summary."""
        return {
            "last_wod": self.last_wod,
            "last_realtime": self.last_realtime,
            "satellite_healthy": self.last_wod is not None or self.last_realtime is not None,
            "last_seen": max(
                self.last_wod["timestamp"] if self.last_wod else 0,
                self.last_realtime["timestamp"] if self.last_realtime else 0
            )
        }
