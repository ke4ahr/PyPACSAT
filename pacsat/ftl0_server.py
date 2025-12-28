# pacsat/ftl0_server.py
# GNU General Public License v3.0
# Copyright (C) 2025-2026 Kris Kirby, KE4AHR
#
# Bidirectional FTL0 protocol server
# Supports both upload (client to server) and download (server to client)
# Hole list management, CRC verification, error recovery

import time
import logging
import threading
from typing import Dict, Optional, List, Tuple
from pacsat.file_storage import FileStorage
from pacsat.pfh import PFH

logger = logging.getLogger('FTL0Server')

class UploadSession:
    """Track one client upload session."""
    def __init__(self, file_num: int, total_size: int, callsign: str):
        self.file_num = file_num
        self.total_size = total_size
        self.callsign = callsign
        self.received_chunks = {}  # offset: data
        self.last_activity = time.time()
        self.complete = False
        self.crc_received = None

    def add_chunk(self, offset: int, data: bytes):
        if offset in self.received_chunks:
            return  # Duplicate
        self.received_chunks[offset] = data
        self.last_activity = time.time()

    def get_missing_holes(self) -> List[Tuple[int, int]]:
        """Return list of (start, end) missing byte ranges."""
        if not self.received_chunks:
            return [(0, self.total_size - 1)]
        
        offsets = sorted(self.received_chunks.keys())
        holes = []
        expected = 0
        
        for offset in offsets:
            if offset > expected:
                holes.append((expected, offset - 1))
            expected = offset + len(self.received_chunks[offset])
        
        if expected < self.total_size:
            holes.append((expected, self.total_size - 1))
        
        return holes

    def is_complete(self) -> bool:
        return len(self.get_missing_holes()) == 0

class DownloadSession:
    """Track one client download session."""
    def __init__(self, file_num: int, client_callsign: str):
        self.file_num = file_num
        self.client_callsign = client_callsign
        self.requested_holes = []
        self.last_activity = time.time()

class FTL0Server:
    """
    Bidirectional FTL0 server.
    - Upload: client sends chunks, server requests missing holes
    - Download: client requests holes, server sends chunks + EF
    """
    def __init__(self, storage: FileStorage, radio, timeout: int = 300):
        self.storage = storage
        self.radio = radio
        self.timeout = timeout
        self.upload_sessions: Dict[int, UploadSession] = {}
        self.download_sessions: Dict[int, DownloadSession] = {}
        self.lock = threading.RLock()
        
        # Start cleanup thread
        threading.Thread(target=self._cleanup_loop, daemon=True).start()
        
        logger.info("[FTL0Server] Bidirectional FTL0 server initialized")

    # Upload handling
    def start_upload(self, file_num: int, total_size: int, callsign: str) -> bool:
        """Client initiates upload."""
        with self.lock:
            if file_num in self.upload_sessions:
                logger.warning(f"[FTL0] Upload already in progress for file {file_num}")
                return False
            
            if total_size <= 0 or total_size > 20_000_000:
                logger.warning(f"[FTL0] Invalid size {total_size} for file {file_num}")
                return False
            
            self.upload_sessions[file_num] = UploadSession(file_num, total_size, callsign)
            logger.info(f"[FTL0] Upload started: file {file_num}, {total_size} bytes from {callsign}")
            return True

    def add_upload_chunk(self, file_num: int, offset: int, data: bytes) -> List[Tuple[int, int]]:
        """Client sends upload chunk."""
        with self.lock:
            session = self.upload_sessions.get(file_num)
            if not session:
                return [(0, 65535)]  # Request everything
            
            session.add_chunk(offset, data)
            
            if session.is_complete():
                return []  # No holes - complete
            
            return session.get_missing_holes()

    def complete_upload(self, file_num: int, crc: int, pfh_info: dict) -> bool:
        """Client signals end of upload."""
        with self.lock:
            session = self.upload_sessions.get(file_num)
            if not session:
                return False
            
            if not session.is_complete():
                logger.warning(f"[FTL0] Upload incomplete for file {file_num}")
                return False
            
            # Reassemble full file
            offsets = sorted(session.received_chunks.keys())
            full_data = b""
            for offset in offsets:
                full_data += session.received_chunks[offset]
            
            # Verify CRC
            calculated_crc = self._crc16(full_data)
            if calculated_crc != crc:
                logger.error(f"[FTL0] CRC mismatch for file {file_num}: expected {crc}, got {calculated_crc}")
                return False
            
            # Create PFH
            pfh = PFH(
                file_num=file_num,
                name=pfh_info.get("name", "UPLOAD  ").encode(),
                ext=pfh_info.get("ext", "BIN").encode(),
                type=pfh_info.get("type", 0),
                size=len(full_data),
                upload_time=int(time.time()),
                body_description=pfh_info.get("description", b"").encode()
            )
            
            # Store file
            success = self.storage.add_file(
                callsign=session.callsign,
                pfh=pfh,
                body=full_data
            )
            
            if success:
                logger.info(f"[FTL0] Upload completed: file {file_num}, {len(full_data)} bytes from {session.callsign}")
                del self.upload_sessions[file_num]
                return True
            else:
                return False

    # Download handling
    def handle_download_request(self, file_num: int, hole_list: List[Tuple[int, int]], client_callsign: str):
        """Client requests file - send missing chunks."""
        file_path = self.storage.get_file_path(file_num)
        if not file_path or not os.path.exists(file_path):
            logger.warning(f"[FTL0] Download request for missing file {file_num}")
            return
        
        with open(file_path, "rb") as f:
            full_data = f.read()
        
        pfh = PFH.parse(full_data)
        body = full_data[pfh.body_offset:]
        
        # Send requested chunks
        for start, end in hole_list:
            chunk = body[start:end+1]
            self.radio.send_chunk(file_num, start, chunk)
        
        # If no holes, send EF
        if not hole_list:
            crc = self._crc16(body)
            self.radio.send_ef(file_num, len(body), crc)

    def _crc16(self, data: bytes) -> int:
        """CRC-16/CCITT as used in PACSAT."""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 1:
                    crc = (crc >> 1) ^ 0x8408
                else:
                    crc >>= 1
        return crc ^ 0xFFFF

    def _cleanup_loop(self):
        """Remove stale sessions."""
        while True:
            time.sleep(60)
            with self.lock:
                now = time.time()
                stale_uploads = [fn for fn, sess in self.upload_sessions.items() if now - sess.last_activity > self.timeout]
                for fn in stale_uploads:
                    logger.info(f"[FTL0] Cleaning up stale upload session {fn}")
                    del self.upload_sessions[fn]

# DOC: Additional methods for download session tracking, multi-client fairness, etc.
# DOC: can be added as needed (current implementation focuses on core upload/download)
