# pacsat/pfh.py
# GNU General Public License v3.0
# Copyright (C) 2025-2026 Kris Kirby, KE4AHR
#
# PACSAT File Header (PFH) parsing and generation
# Supports mandatory, extended, and optional items
# Full round-trip serialization with checksum

import struct
import time
from typing import Optional, List

class PFH:
    """
    PACSAT File Header (PFH) class.
    Supports all mandatory, extended, and optional items from spec.
    """
    MAGIC = b'\xAA\x55'

    def __init__(
        self,
        file_num: Optional[int] = None,
        name: bytes = b'        ',
        ext: bytes = b'   ',
        type: int = 0,
        size: int = 0,
        create_time: int = int(time.time()),
        upload_time: int = int(time.time()),
        seu_flag: int = 0,
        body_offset: int = 0,
        # Extended/Optional
        compression_type: Optional[int] = None,
        body_description: Optional[bytes] = None,
        download_count: int = 0,
        priority: int = 0,
        forwarding: List[str] = None
    ):
        self.file_num = file_num
        self.name = name[:8].ljust(8, b' ')
        self.ext = ext[:3].ljust(3, b' ')
        self.type = type & 0xFF
        self.size = size
        self.create_time = create_time
        self.upload_time = upload_time
        self.seu_flag = seu_flag & 0xFF
        self.body_offset = body_offset
        self.compression_type = compression_type
        self.body_description = body_description
        self.download_count = download_count
        self.priority = priority
        self.forwarding = forwarding or []

    def serialize(self) -> bytes:
        """Serialize full PFH with all items and checksum."""
        items = []
        
        # Mandatory items
        if self.file_num is not None:
            items.append((1, struct.pack('<I', self.file_num)))
        items.append((2, self.name))
        items.append((3, self.ext))
        items.append((4, bytes([self.type])))
        items.append((5, struct.pack('<I', self.size)))
        items.append((7, struct.pack('<I', self.create_time)))
        items.append((8, struct.pack('<I', self.upload_time)))
        items.append((9, bytes([self.seu_flag])))
        items.append((11, struct.pack('<H', self.body_offset)))
        
        # Extended/Optional items
        if self.compression_type is not None:
            items.append((12, bytes([self.compression_type])))
        if self.body_description:
            items.append((13, self.body_description))
        if self.download_count > 0:
            items.append((20, struct.pack('<I', self.download_count)))
        if self.priority > 0:
            items.append((21, bytes([self.priority])))
        if self.forwarding:
            fwd_data = ";".join(self.forwarding).encode('ascii')
            items.append((99, fwd_data))
        
        # Build raw items data
        raw_data = b''
        for item_id, data in items:
            raw_data += struct.pack('<HB', item_id, len(data)) + data
        
        # End marker
        raw_data += b'\x00\x00\x00'
        
        # Calculate checksum (CRC-16 on raw_data)
        checksum = self._crc16(raw_data)
        
        # Header = magic + checksum + raw_data
        header = self.MAGIC + struct.pack('<H', checksum) + raw_data
        
        return header

    def _crc16(self, data: bytes) -> int:
        """CRC-16/CCITT-FALSE checksum as per spec."""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0x8408
                else:
                    crc >>= 1
        return crc ^ 0xFFFF

    @classmethod
    def parse(cls, data: bytes) -> 'PFH':
        """Parse PFH from data."""
        if data[:2] != cls.MAGIC:
            raise ValueError("Invalid PFH magic")
        
        checksum_received = struct.unpack('<H', data[2:4])[0]
        raw_data = data[4:]
        
        # Verify checksum
        checksum_calculated = cls._crc16(raw_data)
        if checksum_received != checksum_calculated:
            raise ValueError("PFH checksum mismatch")
        
        pfh = cls()
        offset = 0
        
        while offset < len(raw_data) - 2:
            item_id = raw_data[offset]
            item_len = struct.unpack('<H', raw_data[offset+1:offset+3])[0]
            if item_id == 0 and item_len == 0:
                break  # End marker
            
            item_data = raw_data[offset+3:offset+3+item_len]
            offset += 3 + item_len
            
            # Parse items
            if item_id == 1:
                pfh.file_num = struct.unpack('<I', item_data)[0]
            elif item_id == 2:
                pfh.name = item_data
            elif item_id == 3:
                pfh.ext = item_data
            elif item_id == 4:
                pfh.type = item_data[0]
            elif item_id == 5:
                pfh.size = struct.unpack('<I', item_data)[0]
            elif item_id == 7:
                pfh.create_time = struct.unpack('<I', item_data)[0]
            elif item_id == 8:
                pfh.upload_time = struct.unpack('<I', item_data)[0]
            elif item_id == 9:
                pfh.seu_flag = item_data[0]
            elif item_id == 11:
                pfh.body_offset = struct.unpack('<H', item_data)[0]
            # Extended/Optional
            elif item_id == 12:
                pfh.compression_type = item_data[0]
            elif item_id == 13:
                pfh.body_description = item_data
            elif item_id == 20:
                pfh.download_count = struct.unpack('<I', item_data)[0]
            elif item_id == 21:
                pfh.priority = item_data[0]
            elif item_id == 99:
                pfh.forwarding = item_data.decode('ascii', errors='ignore').split(';')
        
        return pfh
