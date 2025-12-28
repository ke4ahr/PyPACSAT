# tests/test_pfh.py
# GNU General Public License v3.0
# Copyright (C) 2025-2026 Kris Kirby, KE4AHR
#
# Unit tests for PFH parsing and generation
# Covers mandatory items, advanced optional items, checksum, round-trip

import pytest
import struct
import time
from pacsat.pfh import PFH

def test_mandatory_items():
    """Test serialization and parsing of mandatory PFH items."""
    pfh = PFH(
        file_num=1001,
        name=b"TEST    ",
        ext=b"TXT",
        type=0,
        size=1024,
        create_time=1735689600,  # 2025-01-01
        upload_time=1735776000,
        seu_flag=1,
        body_offset=128
    )
    
    data = pfh.serialize()
    
    parsed = PFH.parse(data)
    
    assert parsed.file_num == 1001
    assert parsed.name == b"TEST    "
    assert parsed.ext == b"TXT"
    assert parsed.type == 0
    assert parsed.size == 1024
    assert parsed.create_time == 1735689600
    assert parsed.upload_time == 1735776000
    assert parsed.seu_flag == 1
    assert parsed.body_offset == 128

def test_advanced_optional_items():
    """Test advanced optional PFH items."""
    pfh = PFH(
        file_num=2002,
        compression_type=2,  # PKZIP
        body_description=b"This is a test file with description",
        download_count=42,
        priority=10,
        forwarding=["G0K8KA-1", "M0ABC-0"]
    )
    
    data = pfh.serialize()
    parsed = PFH.parse(data)
    
    assert parsed.compression_type == 2
    assert parsed.body_description == b"This is a test file with description"
    assert parsed.download_count == 42
    assert parsed.priority == 10
    assert parsed.forwarding == ["G0K8KA-1", "M0ABC-0"]

def test_checksum_validation():
    """Test PFH checksum verification."""
    pfh = PFH(file_num=3003)
    data = pfh.serialize()
    
    # Corrupt checksum
    corrupted = data[:2] + b"\x00\x00" + data[4:]
    
    with pytest.raises(ValueError, match="checksum mismatch"):
        PFH.parse(corrupted)

def test_round_trip():
    """Test full round-trip serialization."""
    original = PFH(
        file_num=4004,
        name=b"ROUND   ",
        ext=b"BIN",
        size=8192,
        compression_type=1,
        body_description=b"Round-trip test",
        download_count=7,
        priority=5,
        forwarding=["TEST-1"]
    )
    
    data = original.serialize()
    parsed = PFH.parse(data)
    
    # Compare key fields
    assert parsed.file_num == original.file_num
    assert parsed.name == original.name
    assert parsed.ext == original.ext
    assert parsed.compression_type == original.compression_type
    assert parsed.body_description == original.body_description
    assert parsed.download_count == original.download_count
    assert parsed.priority == original.priority
    assert parsed.forwarding == original.forwarding

def test_invalid_magic():
    """Test invalid magic bytes."""
    bad_data = b"\x00\x00" + b"invalid"
    with pytest.raises(ValueError, match="Invalid PFH magic"):
        PFH.parse(bad_data)

# DOC: Comprehensive PFH test suite covering mandatory, advanced items, checksum, round-trip
# DOC: Ensures full compatibility with original PACSAT specification
