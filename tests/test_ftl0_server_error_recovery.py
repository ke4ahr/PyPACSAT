# Copyright (C) 2025-2026 Kris Kirby, KE4AHR
# tests/test_ftl0_server_error_recovery.py
import pytest
import time
import os
from pacsat.ftl0_server import FTL0UploadServer
from pacsat.pfh import PFH

@pytest.fixture
def temp_storage_dir(tmp_path):
    return str(tmp_path / "storage")

@pytest.fixture
def ftl0_server(temp_storage_dir):
    from pacsat.file_storage import FileStorage
    storage = FileStorage(temp_storage_dir)
    server = FTL0UploadServer(storage=storage, timeout=2)
    return server

def test_error_recovery_missing_chunk(ftl0_server, temp_storage_dir):
    """Test recovery from missing chunk with correct CRC on retry."""
    # Start upload
    assert ftl0_server.start_upload(1001, 20, "RECOVER-0")
    
    # Send chunk 0-9
    ftl0_server.add_chunk(1001, 0, b"first part")
    
    # Intentionally skip chunk 10-19
    # Send wrong CRC first (simulate error)
    bad_crc = 0x0000
    success = ftl0_server.complete_upload(1001, bad_crc, {"name": "ERROR   "})
    assert not success  # Should fail
    
    # Now send missing chunk
    ftl0_server.add_chunk(1001, 10, b"secondpart")
    
    # Calculate correct CRC
    full_data = b"first partsecondpart"
    correct_crc = ftl0_server._crc16(full_data)
    
    # Retry completion
    success = ftl0_server.complete_upload(1001, correct_crc, {"name": "RECOVER ", "ext": "TXT"})
    assert success
    
    # Verify file stored correctly
    from pacsat.file_storage import FileStorage
    storage = FileStorage(temp_storage_dir)
    files = storage.list_files()
    assert len(files) == 1
    assert files[0]["file_num"] == 1001
    
    path = storage.get_file_path(1001)
    with open(path, "rb") as f:
        data = f.read()
    pfh = PFH.parse(data)
    body = data[pfh.body_offset:]
    assert body == full_data

def test_error_recovery_corrupt_chunk(ftl0_server, temp_storage_dir):
    """Test recovery when client sends corrupt chunk then correct one."""
    assert ftl0_server.start_upload(1002, 15, "CORRUPT-0")
    
    # Send corrupt chunk
    ftl0_server.add_chunk(1002, 0, b"bad data here!!")
    
    # Client realizes error, resends correct chunk
    ftl0_server.add_chunk(1002, 0, b"correct data!!")
    
    correct_crc = ftl0_server._crc16(b"correct data!!")
    assert ftl0_server.complete_upload(1002, correct_crc, {"name": "FIXED   "})
    
    # Verify correct version stored
    from pacsat.file_storage import FileStorage
    storage = FileStorage(temp_storage_dir)
    path = storage.get_file_path(1002)
    with open(path, "rb") as f:
        data = f.read()
    pfh = PFH.parse(data)
    body = data[pfh.body_offset:]
    assert body == b"correct data!!"

def test_error_recovery_network_loss(ftl0_server, temp_storage_dir):
    """Test upload survives temporary session loss (timeout + restart)."""
    # Start upload
    assert ftl0_server.start_upload(1003, 30, "NETLOSS-0")
    
    # Send some chunks
    ftl0_server.add_chunk(1003, 0, b"part one")
    ftl0_server.add_chunk(1003, 10, b"part two")
    
    # Simulate long pause - session times out
    time.sleep(4)
    
    # Cleanup runs
    ftl0_server._cleanup_loop()
    
    # Session should be gone
    assert 1003 not in ftl0_server.sessions
    
    # Client restarts upload with same file_num (new session)
    assert ftl0_server.start_upload(1003, 30, "NETLOSS-0")  # Allowed, previous timed out
    
    # Resend all chunks
    ftl0_server.add_chunk(1003, 0, b"part one")
    ftl0_server.add_chunk(1003, 10, b"part two")
    ftl0_server.add_chunk(1003, 20, b"part three")
    
    full_data = b"part onepart twopart three"
    crc = ftl0_server._crc16(full_data)
    assert ftl0_server.complete_upload(1003, crc, {"name": "RECOVER "})
    
    # File should be stored
    from pacsat.file_storage import FileStorage
    storage = FileStorage(temp_storage_dir)
    assert len(storage.list_files()) == 1

def test_error_recovery_duplicate_file_num(ftl0_server):
    """Test handling when client uses same file_num after failure."""
    # First failed upload
    ftl0_server.start_upload(1004, 10, "DUP-0")
    ftl0_server.add_chunk(1004, 0, b"bad")
    ftl0_server.complete_upload(1004, 0x0000, {})  # Fail
    
    # Client retries with same file_num
    assert ftl0_server.start_upload(1004, 10, "DUP-0")  # Should succeed (old session gone)
    
    ftl0_server.add_chunk(1004, 0, b"good data!")
    crc = ftl0_server._crc16(b"good data!")
    assert ftl0_server.complete_upload(1004, crc, {"name": "RETRY   "})
