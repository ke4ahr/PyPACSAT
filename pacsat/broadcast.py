# pacsat/broadcast.py
# GNU General Public License v3.0
# Copyright (C) 2025-2026 Kris Kirby, KE4AHR
#
# PACSAT Broadcast Protocol implementation
# PID 0xBD: Directory broadcast (PFH entries)
# PID 0xBB: File chunk broadcast
# Periodic and on-demand scheduling

import time
import logging
import threading
from typing import Optional, List
from pacsat.file_storage import FileStorage
from pacsat.pfh import PFH

logger = logging.getLogger('Broadcast')

class DirectoryBroadcaster:
    """
    PACSAT Directory Broadcast (PID 0xBD)
    Periodically broadcasts PFH entries for all files
    Also supports file chunk broadcast (PID 0xBB) on demand
    """
    def __init__(self, storage: FileStorage, radio, config):
        self.storage = storage
        self.radio = radio
        self.config = config
        self.running = True
        
        logger.info("[Directory] Broadcaster initialized")

    def start(self):
        """Start periodic directory broadcast."""
        if self.config.directory_broadcast_interval:
            thread = threading.Thread(target=self._broadcast_loop, daemon=True)
            thread.start()
            logger.info(f"[Directory] Periodic broadcast started (every {self.config.directory_broadcast_interval} min)")

    def _broadcast_loop(self):
        """Main broadcast loop."""
        interval = self.config.directory_broadcast_interval * 60
        while self.running:
            time.sleep(interval)
            self.broadcast_directory()

    def broadcast_directory(self, file_nums: Optional[List[int]] = None):
        """
        Broadcast directory entries.
        If file_nums is None, broadcast all files.
        """
        try:
            if file_nums is None:
                files = self.storage.list_files()
            else:
                files = []
                for fn in file_nums:
                    info = self.storage.get_file_info(fn)
                    if info:
                        files.append(info)
            
            logger.info(f"[Directory] Broadcasting {len(files)} file entries")
            
            # Sort newest first (common practice)
            files.sort(key=lambda x: x["upload_time"], reverse=True)
            
            for file_info in files:
                file_num = file_info["file_num"]
                path = self.storage.get_file_path(file_num)
                if not path or not os.path.exists(path):
                    continue
                
                with open(path, "rb") as f:
                    data = f.read()
                
                try:
                    pfh = PFH.parse(data)
                    
                    # Send as PID 0xBD UI frame
                    frame = self.radio.framer.encode(
                        dest="PACSAT-0",
                        src=self.config.callsign,
                        pid=0xBD,  # Directory
                        info=pfh.serialize()
                    )
                    self.radio.send(frame)
                    
                    time.sleep(0.5)  # Spacing between entries
                    
                except Exception as e:
                    logger.warning(f"[Directory] Failed to parse PFH for file {file_num}: {e}")
                    
        except Exception as e:
            logger.error(f"[Directory] Broadcast failed: {e}")

    def broadcast_single_file(self, file_num: int):
        """Broadcast single file entry (on-demand)."""
        self.broadcast_directory([file_num])

    def broadcast_file_chunks(self, file_num: int, client_callsign: Optional[str] = None):
        """Broadcast file chunks (PID 0xBB) - on-demand download."""
        try:
            path = self.storage.get_file_path(file_num)
            if not path or not os.path.exists(path):
                logger.warning(f"[Broadcast] File {file_num} not found for chunk broadcast")
                return
            
            with open(path, "rb") as f:
                data = f.read()
            
            pfh = PFH.parse(data)
            body = data[pfh.body_offset:]
            
            chunk_size = 256
            offset = 0
            while offset < len(body):
                chunk = body[offset:offset + chunk_size]
                # Send as PID 0xBB UI frame
                frame = self.radio.framer.encode(
                    dest=client_callsign or "PACSAT-0",
                    src=self.config.callsign,
                    pid=0xBB,  # File data
                    info=chunk
                )
                self.radio.send(frame)
                offset += len(chunk)
                time.sleep(0.1)
            
            logger.info(f"[Broadcast] Transmitted file {file_num} ({len(body)} bytes)")
            
        except Exception as e:
            logger.error(f"[Broadcast] Chunk broadcast failed for file {file_num}: {e}")

    def stop(self):
        self.running = False
        logger.info("[Directory] Broadcaster stopped")
