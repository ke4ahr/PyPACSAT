# Copyright (C) 2025-2026 Kris Kirby, KE4AHR
# tests/test_ftl0_server_integration.py
import pytest
import time
import os
from unittest.mock import MagicMock
from pacsat.ftl0_server import FTL0UploadServer
from pacsat.pfh import PFH

@pytest.fixture
def temp_storage_dir(tmp_path):
    """Temporary directory for storage."""
    return str(tmp_path / "storage")

@pytest.fixture
def ftl0_server(temp_storage_dir):
    from pacsat.file_storage import FileStorage
    storage = FileStorage(temp_storage_dir)
    server = FTL0UploadServer(storage=storage, timeout=2)
    return server

def test_full_upload_lifecycle(ftl0_server, temp_storage_dir):
    """Integration test: complete upload from start to storage."""
    # Start upload
    assert ftl0_server.start_upload(1001, 30, "G0K8KA-0")
    
    # Send chunks
    assert ftl0_server.add_chunk(1001, 0, b"Hello ") == [(6, 29)]
    assert ftl0_server.add_chunk(1001, 6, b"PACSAT ") == [(14, 29)]
    assert ftl0_server.add_chunk(1001, 14, b"ground station!") == []
    
    # Calculate CRC
    full_data = b"Hello PACSAT ground station!"
    expected_crc = ftl0_server._crc16(full_data)
    
    pfh_info = {
        "name": "HELLO   ",
        "ext": "TXT",
        "type": 0,
        "description": "Integration test upload"
    }
    
    # Complete
    assert ftl0_server.complete_upload(1001, expected_crc, pfh_info)
    
    # Verify file on disk
    from pacsat.file_storage import FileStorage
    storage = FileStorage(temp_storage_dir)
    files = storage.list_files()
    assert len(files) == 1
    assert files[0]["file_num"] == 1001
    assert files[0]["callsign"] == "G0K8KA-0"
    
    # Verify content
    path = storage.get_file_path(1001)
    assert os.path.exists(path)
    with open(path, "rb") as f:
        data = f.read()
    pfh = PFH.parse(data)
    body = data[pfh.body_offset:]
    assert body == full_data

def test_upload_timeout_cleanup(ftl0_server):
    """Test stale upload sessions are removed."""
    assert ftl0_server.start_upload(1002, 100, "TIMEOUT-0")
    assert ftl0_server.start_upload(1003, 200, "TIMEOUT-1")
    
    # Only touch one
    ftl0_server.add_chunk(1003, 0, b"keep")
    
    # Wait for cleanup
    time.sleep(4)
    
    # Force cleanup cycle
    ftl0_server._cleanup_loop()  # Run one iteration
    
    assert 1002 not in ftl0_server.sessions
    assert 1003 in ftl0_server.sessions  # Still active

def test_concurrent_uploads(ftl0_server):
    """Test multiple simultaneous uploads."""
    import threading
    
    def upload_file(file_num: int, size: int, callsign: str, data: bytes):
        ftl0_server.start_upload(file_num, size, callsign)
        ftl0_server.add_chunk(file_num, 0, data)
        crc = ftl0_server._crc16(data)
        ftl0_server.complete_upload(file_num, crc, {"name": f"FILE{file_num}"})
    
    threads = []
    for i in range(5):
        t = threading.Thread(
            target=upload_file,
            args=(2000 + i, 10 + i, f"USER{i}-0", b"X" * (10 + i))
        )
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    # All should be stored
    from pacsat.file_storage import FileStorage
    storage = FileStorage(ftl0_server.storage.storage_dir)
    files = storage.list_files()
    assert len(files) == 5

def test_crc_failure_prevents_storage(ftl0_server, temp_storage_dir):
    """Test bad CRC prevents file storage."""
    ftl0_server.start_upload(1004, 10, "BADCRC-0")
    ftl0_server.add_chunk(1004, 0, b"bad data!!")
    
    bad_crc = 0x0000
    assert not ftl0_server.complete_upload(1004, bad_crc, {})
    
    # File should not be in storage
    from pacsat.file_storage import FileStorage
    storage = FileStorage(temp_storage_dir)
    assert len(storage.list_files()) == 0
    assert 1004 in ftl0_server.sessions  # Session remains open

def test_duplicate_chunks_ignored(ftl0_server):
    """Test sending same chunk twice doesn't break hole list."""
    ftl0_server.start_upload(1005, 20, "DUP-0")
    
    holes1 = ftl0_server.add_chunk(1005, 0, b"first part")
    holes2 = ftl0_server.add_chunk(1005, 0, b"different")  # Same offset
    
    assert holes1 == holes2  # Hole list unchanged
