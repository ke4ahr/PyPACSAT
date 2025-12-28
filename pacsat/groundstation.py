# pacsat/groundstation.py
# GNU General Public License v3.0
# Copyright (C) 2025-2026 Kris Kirby, KE4AHR
#
# Main ground station class
# Coordinates radio interface, file storage, FTL0 server, broadcast, telemetry
# Async periodic tasks for maintenance

import asyncio
import time
import logging
from datetime import datetime
from typing import Optional

from pacsat.file_storage import FileStorage
from pacsat.ftl0_server import FTL0Server
from pacsat.broadcast import DirectoryBroadcaster
from pacsat.telemetry import PACSTATTelemetry
from pacsat.radio_connected import ConnectedModeHandler

logger = logging.getLogger('PACSATGround')
logger.setLevel(logging.INFO)

class PACSATGround:
    """
    Central ground station controller.
    Manages all subsystems and async scheduling.
    """
    def __init__(self, config):
        self.config = config
        self.running = True
        
        # Core components
        self.storage = FileStorage(config.storage_dir)
        self.radio = self._init_radio()
        self.ftl0_server = FTL0Server(self.storage, self.radio)
        self.directory_broadcaster = DirectoryBroadcaster(self.storage, self.radio, config)
        self.telemetry_parser = PACSTATTelemetry()
        self.connected_handler = ConnectedModeHandler(self.radio) if config.enable_connected_mode else None
        
        # Start async scheduler
        self.loop = asyncio.get_event_loop()
        self.loop.create_task(self._async_scheduler())
        
        logger.info("[GroundStation] PACSAT ground station initialized")

    def _init_radio(self):
        """Initialize radio interface based on config."""
        if self.config.radio.type == "kiss_serial":
            from pacsat.serial_interface import KISSSerialRadio
            return KISSSerialRadio(self.config)
        elif self.config.radio.type == "agwpe_tcp":
            from PyAGW3.agwpe import AGWPEClient
            return AGWPEClient(self.config)
        else:
            raise ValueError(f"Unknown radio type: {self.config.radio.type}")

    async def _async_scheduler(self):
        """Async scheduler for periodic tasks."""
        logger.info("[Scheduler] Async scheduler started")
        
        # Periodic tasks
        tasks = []
        
        # Directory broadcast
        if self.config.directory_broadcast_interval:
            tasks.append(self._directory_task())
        
        # Storage cleanup
        if self.config.cleanup_interval_hours:
            tasks.append(self._storage_cleanup_task())
        
        # Blacklist cleanup (if using SQLite blacklist)
        tasks.append(self._blacklist_cleanup_task())
        
        # Keep alive
        while self.running:
            await asyncio.sleep(3600)
        
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _directory_task(self):
        """Periodic directory broadcast."""
        interval = self.config.directory_broadcast_interval * 60
        logger.info(f"[Scheduler] Directory broadcast task started (every {interval}s)")
        
        while self.running:
            await asyncio.sleep(interval)
            try:
                self.directory_broadcaster.broadcast_directory()
            except Exception as e:
                logger.error(f"[Scheduler] Directory broadcast failed: {e}")

    async def _storage_cleanup_task(self):
        """Periodic storage cleanup."""
        interval = self.config.cleanup_interval_hours * 3600
        logger.info(f"[Scheduler] Storage cleanup task started (every {interval}s)")
        
        while self.running:
            await asyncio.sleep(interval)
            try:
                start_time = time.time()
                logger.info("[Scheduler] Starting storage cleanup")
                
                result = await asyncio.to_thread(
                    self.storage.bulk_cleanup,
                    max_age_days=self.config.cleanup_max_age_days,
                    max_files=self.config.cleanup_max_files,
                    dry_run=False
                )
                
                duration = time.time() - start_time
                logger.info("[Scheduler] Storage cleanup completed", 
                           extra={
                               "deleted_files": result.get("deleted_files", 0),
                               "removed_dirs": result.get("removed_dirs", 0),
                               "duration_seconds": round(duration, 3)
                           })
            except Exception as e:
                logger.error(f"[Scheduler] Storage cleanup failed: {e}")

    async def _blacklist_cleanup_task(self):
        """Periodic token blacklist cleanup."""
        interval = 3600  # hourly
        logger.info(f"[Scheduler] Blacklist cleanup task started (every {interval}s)")
        
        while self.running:
            await asyncio.sleep(interval)
            try:
                start_time = time.time()
                logger.info("[Cleanup] Starting blacklist cleanup")
                
                deleted = self.blacklist.cleanup()
                
                duration = time.time() - start_time
                logger.info("[Cleanup] Blacklist cleanup completed", 
                           extra={
                               "deleted_tokens": deleted,
                               "duration_seconds": round(duration, 3)
                           })
            except Exception as e:
                logger.error(f"[Cleanup] Blacklist cleanup failed: {e}")

    def stop(self):
        """Gracefully stop the ground station."""
        self.running = False
        if self.directory_broadcaster:
            self.directory_broadcaster.stop()
        if self.radio:
            self.radio.close()
        logger.info("[GroundStation] Shutdown complete")

    def main(self):
        """Entry point - run forever."""
        try:
            asyncio.run(self._run_forever())
        except KeyboardInterrupt:
            logger.info("[GroundStation] Interrupted by user")
        finally:
            self.stop()

    async def _run_forever(self):
        """Keep event loop running."""
        while self.running:
            await asyncio.sleep(1)

# DOC: Main entry point when run as script
if __name__ == "__main__":
    import argparse
    from pacsat.config import load_config
    
    parser = argparse.ArgumentParser(description="PACSAT Ground Station")
    parser.add_argument("-c", "--config", default="config.yaml", help="Config file path")
    args = parser.parse_args()
    
    config = load_config(args.config)
    groundstation = PACSATGround(config)
    groundstation.main()
