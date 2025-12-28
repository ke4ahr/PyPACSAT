# tests/test_file_storage.py
# GNU General Public License v3.0
# Copyright (C) 2025-2026 Kris Kirby, KE4AHR
#
# Unit tests for FileStorage
# Covers add_file, list_files, delete_file, subdirectory hierarchy, advanced PFH

import pytest
import os
import time
from unittest.mock import patch
from pacsat.file_storage import FileStorage
from pacsat.pfh import PFH

@pytest.fixture
def temp_storage(tmp_path):
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()
    return FileStorage(str(storage_dir))

def test_add_file_creates_subdirs(temp_storage):
    """Test subdirectory hierarchy creation."""
    pfh = PFH(name=b"TEST    ", ext=b"TXT")
    file_num = temp_storage.add_file("G0K8KA-0", pfh, b"test data")
    
    assert file_num == 1
    expected_path = os.path.join(temp_storage.storage_dir, "t", "te", "tes", "test", "00000001.bin")
    assert os.path.exists(expected_path)
    
    # Check DB entry
    files = temp_storage.list_files()
    assert len(files) == 1
    assert files[0]["filename"] == "TEST.TXT"
    assert files[0]["callsign"] == "G0K8KA-0"

def test_add_file_advanced_pfh(temp_storage):
    """Test storage of advanced PFH items."""
    pfh = PFH(
        name=b"ADV     ",
        ext=b"DAT",
        compression_type=2,  # PKZIP
        body_description=b"Advanced test file with description",
        download_count=5,
        priority=10,
        forwarding=["G0K8KA-1", "M0ABC-0"]
    )
    file_num = temp_storage.add_file("TEST-0", pfh, b"data")
    
    files = temp_storage.list_files()
    assert files[0]["compression_type"] == 2
    assert files[0]["description"] == "Advanced test file with description"
    assert files[0]["download_count"] == 5
    assert files[0]["priority"] == 10
    assert "G0K8KA-1" in files[0]["forwarding"]

def test_list_files_ordering(temp_storage):
    """Test files listed newest first."""
    pfh1 = PFH(name=b"OLD     ")
    temp_storage.add_file("USER1", pfh1, b"old")
    time.sleep(0.1)  # Ensure timestamp difference
    
    pfh2 = PFH(name=b"NEW     ")
    temp_storage.add_file("USER2", pfh2, b"new")
    
    files = temp_storage.list_files()
    assert files[0]["filename"] == "NEW.DAT"  # Assuming default ext
    assert files[1]["filename"] == "OLD.DAT"

def test_delete_file_soft(temp_storage):
    """Test soft delete moves to trash."""
    pfh = PFH(name=b"DELETE  ")
    file_num = temp_storage.add_file("DEL-0", pfh, b"to delete")
    
    assert temp_storage.delete_file(file_num, permanent=False)
    
    # File should be gone from main storage
    assert temp_storage.get_file_path(file_num) is None
    files = temp_storage.list_files()
    assert len(files) == 0
    
    # Should be in trash
    trash_files = os.listdir(temp_storage.trash_dir)
    assert len(trash_files) == 1
    assert trash_files[0].startswith(str(file_num))

def test_delete_file_permanent(temp_storage):
    """Test permanent delete removes file."""
    pfh = PFH(name=b"PERM    ")
    file_num = temp_storage.add_file("PERM-0", pfh, b"permanent")
    path = temp_storage.get_file_path(file_num)
    
    assert temp_storage.delete_file(file_num, permanent=True)
    
    assert not os.path.exists(path)
    assert temp_storage.get_file_path(file_num) is None

def test_increment_download_count(temp_storage):
    """Test download counter increment."""
    pfh = PFH(name=b"COUNT   ", download_count=3)
    file_num = temp_storage.add_file("CNT-0", pfh, b"data")
    
    temp_storage.increment_download_count(file_num)
    temp_storage.increment_download_count(file_num)
    
    files = temp_storage.list_files()
    assert files[0]["download_count"] == 5

def test_subdir_cleanup(temp_storage):
    """Test empty subdirectories are removed on delete."""
    pfh = PFH(name=b"CLEAN   ")
    file_num = temp_storage.add_file("CLEAN-0", pfh, b"data")
    path = temp_storage.get_file_path(file_num)
    subdir = os.path.dirname(path)
    
    temp_storage.delete_file(file_num)
    
    assert not os.path.exists(subdir)  # Should be cleaned up

# DOC: Additional tests for trash listing, recovery, bulk cleanup, etc.
# DOC: can be added as needed
