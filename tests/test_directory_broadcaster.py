# Copyright (C) 2025-2026 Kris Kirby, KE4AHR
# tests/test_directory_broadcaster.py
import pytest
import time
import threading
from unittest.mock import MagicMock
from pacsat.broadcast import DirectoryBroadcaster
from pacsat.file_storage import FileStorage
from pacsat.pfh import PFH

@pytest.fixture
def mock_radio():
    radio = MagicMock()
    radio.framer.encode.return_value = b"mock_frame"
    radio.send = MagicMock()
    return radio

@pytest.fixture
def temp_storage(tmp_path):
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()
    return FileStorage(str(storage_dir))

@pytest.fixture
def config():
    class Config:
        callsign = "G0K8KA-0"
        directory_broadcast_interval = 0.1  # Fast for testing
    return Config()

def test_periodic_broadcast(temp_storage, mock_radio, config):
    """Test periodic full directory broadcast."""
    broadcaster = DirectoryBroadcaster(temp_storage, mock_radio, config)
    
    # Create test files
    for i in range(3):
        pfh = PFH(name=f"FILE{i}  ", ext="TXT", type=0, size=10 + i)
        temp_storage.add_file(f"USER{i}-0", pfh, b"test data")
    
    # Start broadcaster
    thread = threading.Thread(target=broadcaster._broadcast_loop)
    thread.daemon = True
    thread.start()
    
    # Wait for one cycle
    time.sleep(0.3)
    
    # Stop
    broadcaster.stop()
    thread.join(timeout=1)
    
    # Should have sent 3 frames
    assert mock_radio.send.call_count >= 3
    mock_radio.framer.encode.assert_called_with(
        dest="PACSAT-0",
        src="G0K8KA-0",
        pid=0xBD,
        info=mock_radio.framer.encode.call_args_list[-1][1]['info']  # PFH serialized
    )

def test_on_demand_single_file(temp_storage, mock_radio, config):
    """Test broadcasting single file on demand."""
    broadcaster = DirectoryBroadcaster(temp_storage, mock_radio, config)
    
    pfh = PFH(name="SINGLE  ", ext="BIN", type=0, size=100)
    file_num = temp_storage.add_file("TEST-0", pfh, b"single file")
    
    broadcaster.broadcast_single_file(file_num)
    
    mock_radio.send.assert_called_once()
    call_args = mock_radio.framer.encode.call_args
    assert call_args[1]['pid'] == 0xBD
    assert call_args[1]['dest'] == "PACSAT-0"

def test_broadcast_corrupt_pfh(temp_storage, mock_radio, config):
    """Test broadcaster skips files with corrupt PFH."""
    broadcaster = DirectoryBroadcaster(temp_storage, mock_radio, config)
    
    # Create valid file
    pfh_good = PFH(name="GOOD    ", ext="TXT", type=0, size=10)
    good_num = temp_storage.add_file("GOOD-0", pfh_good, b"good")
    
    # Create corrupt file (wrong path or bad data)
    # Manually insert bad path
    bad_path = temp_storage.storage_dir / "bad" / "00000001.bin"
    bad_path.parent.mkdir(exist_ok=True)
    bad_path.write_bytes(b"corrupt data")
    
    # Broadcast all
    broadcaster.broadcast_directory()
    
    # Should only send the good one
    assert mock_radio.send.call_count == 1

def test_broadcast_empty_directory(temp_storage, mock_radio, config):
    """Test broadcast with no files."""
    broadcaster = DirectoryBroadcaster(temp_storage, mock_radio, config)
    
    broadcaster.broadcast_directory()
    
    assert mock_radio.send.call_count == 0

def test_broadcast_stop(temp_storage, mock_radio, config):
    """Test broadcaster stops cleanly."""
    config.directory_broadcast_interval = 0.1
    broadcaster = DirectoryBroadcaster(temp_storage, mock_radio, config)
    
    # Start loop
    thread = threading.Thread(target=broadcaster._broadcast_loop)
    thread.daemon = True
    thread.start()
    
    time.sleep(0.15)  # Allow one cycle
    initial_calls = mock_radio.send.call_count
    
    broadcaster.stop()
    thread.join(timeout=1)
    
    time.sleep(0.2)
    final_calls = mock_radio.send.call_count
    
    assert final_calls == initial_calls  # No more broadcasts
