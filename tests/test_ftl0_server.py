# Copyright (C) 2025-2026 Kris Kirby, KE4AHR
# tests/test_ftl0_server.py
import pytest
import time
from unittest.mock import MagicMock
from pacsat.ftl0_server import FTL0UploadServer, UploadSession

@pytest.fixture
def mock_storage():
    storage = MagicMock()
    storage.add_file.return_value = 1001
    return storage

@pytest.fixture
def ftl0_server(mock_storage):
    return FTL0UploadServer(storage=mock_storage, timeout=1)  # Short timeout for testing

def test_start_upload_success(ftl0_server):
    """Test successful upload initiation."""
    success = ftl0_server.start_upload(file_num=1001, total_size=1024, callsign="G0K8KA-0")
    assert success is True
    
    session = ftl0_server.sessions.get(1001)
    assert session is not None
    assert session.total_size == 1024
    assert session.callsign == "G0K8KA-0"

def test_start_upload_duplicate(ftl0_server):
    """Test starting upload for already active file."""
    ftl0_server.start_upload(1001, 1024, "G0K8KA-0")
    success = ftl0_server.start_upload(1001, 2048, "M0ABC-1")
    assert success is False

def test_add_chunk_and_holes(ftl0_server):
    """Test chunk addition and hole list calculation."""
    ftl0_server.start_upload(1001, 1024, "TEST-0")
    
    # Add chunk at offset 256 (256 bytes)
    holes = ftl0_server.add_chunk(1001, 256, b"A" * 256)
    assert holes == [(0, 255), (512, 1023)]  # Two holes
    
    # Add chunk at offset 0
    holes = ftl0_server.add_chunk(1001, 0, b"B" * 256)
    assert holes == [(512, 1023)]
    
    # Add final chunk
    holes = ftl0_server.add_chunk(1001, 512, b"C" * 512)
    assert holes == []  # Complete

def test_complete_upload_success(ftl0_server, mock_storage):
    """Test successful upload completion with CRC."""
    ftl0_server.start_upload(1001, 512, "TEST-0")
    
    # Add chunks
    ftl0_server.add_chunk(1001, 0, b"Hello")
    ftl0_server.add_chunk(1001, 5, b" World!")
    
    # Calculate expected CRC
    full_data = b"Hello World!"
    expected_crc = ftl0_server._crc16(full_data)
    
    pfh_info = {
        "name": "HELLO   ",
        "ext": "TXT",
        "type": 0,
        "description": "Test upload"
    }
    
    success = ftl0_server.complete_upload(1001, expected_crc, pfh_info)
    assert success is True
    
    # Storage should have been called
    mock_storage.add_file.assert_called_once()
    assert 1001 not in ftl0_server.sessions  # Session cleaned up

def test_complete_upload_crc_fail(ftl0_server):
    """Test upload fails on CRC mismatch."""
    ftl0_server.start_upload(1001, 11, "TEST-0")
    ftl0_server.add_chunk(1001, 0, b"Hello World")
    
    bad_crc = 0x0000
    success = ftl0_server.complete_upload(1001, bad_crc, {})
    assert success is False
    assert 1001 in ftl0_server.sessions  # Session remains

def test_complete_upload_incomplete(ftl0_server):
    """Test completion fails if chunks missing."""
    ftl0_server.start_upload(1001, 1024, "TEST-0")
    ftl0_server.add_chunk(1001, 0, b"A" * 512)
    
    success = ftl0_server.complete_upload(1001, 0x1234, {})
    assert success is False

def test_timeout_cleanup(ftl0_server):
    """Test stale sessions are cleaned up."""
    ftl0_server.start_upload(1001, 1024, "TEST-0")
    ftl0_server.start_upload(1002, 512, "TEST-1")
    
    # Override last_activity for testing
    ftl0_server.sessions[1001].last_activity = time.time() - 10
    
    # Trigger cleanup
    ftl0_server._cleanup_loop()  # Run one iteration
    
    assert 1001 not in ftl0_server.sessions
    assert 1002 in ftl0_server.sessions  # Recent one remains

def test_duplicate_chunk(ftl0_server):
    """Test duplicate chunks are ignored."""
    ftl0_server.start_upload(1001, 512, "TEST-0")
    
    holes1 = ftl0_server.add_chunk(1001, 0, b"data")
    holes2 = ftl0_server.add_chunk(1001, 0, b"different")  # Duplicate offset
    
    assert holes1 == holes2  # No change in holes

def test_invalid_parameters(ftl0_server):
    """Test invalid size/start rejected."""
    assert not ftl0_server.start_upload(1001, 0, "BAD")
    assert not ftl0_server.start_upload(1001, -1024, "BAD")
    assert not ftl0_server.start_upload(1001, 30_000_000, "BAD")
