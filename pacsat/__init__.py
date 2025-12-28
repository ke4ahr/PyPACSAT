# pacsat/__init__.py
# GNU General Public License v3.0
# Copyright (C) 2025-2026 Kris Kirby, KE4AHR
#
# PACSAT Ground Station Core Package

__version__ = "1.0.0"
__date__ = "2025-12-27"
__author__ = "Kris Kirby, KE4AHR"
__license__ = "GNU General Public License v3.0"

"""
Modern revival of the PACSAT store-and-forward satellite ground station.

Features:
- Full FTL0 bidirectional file transfer
- PFH handling with advanced optional items
- Broadcast protocol (PID 0xBB/0xBD)
- Conventional file storage with subdirectory hierarchy
- Soft delete and recovery
- FastAPI REST interface with JWT authentication
- AGWPE TCP and KISS/XKISS radio support
- Connected mode (optional)
- Telemetry parsing
"""

# Import key classes for easier access
from .groundstation import PACSATGround
from .file_storage import FileStorage
from .pfh import PFH
from .ftl0_server import FTL0DownloadServer, FTL0UploadServer
from .broadcast import DirectoryBroadcaster
from .telemetry import PACSTATTelemetry

__all__ = [
    "PACSATGround",
    "FileStorage",
    "PFH",
    "FTL0DownloadServer",
    "FTL0UploadServer",
    "DirectoryBroadcaster",
    "PACSTATTelemetry",
    "__version__",
]
