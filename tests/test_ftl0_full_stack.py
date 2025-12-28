# Copyright (C) 2025-2026 Kris Kirby, KE4AHR
# tests/test_ftl0_full_stack.py
import pytest
import time
import queue
from pacsat.ftl0_server import FTL0UploadServer, FTL0DownloadServer
from pacsat.file_storage import FileStorage
from pacsat.pfh import PFH

class MockRadio:
    """Mock radio that routes frames between client and server."""
    def __init__(self):
        self.server_queue = queue.Queue()
        self.client_queues = {}  # client_id: queue
    
    def send_from_server(self, frame_type, file_num, offset=None, data=None, holes=None):
        """Server sends to all clients."""
        for client_id, q in self.client_queues.items():
            q.put(("server", frame_type, file_num, offset, data, holes))
    
    def send_from_client(self, client_id, frame_type, file_num, holes=None):
        """Client sends to server."""
        self.server_queue.put((client_id, frame_type, file_num, holes))
    
    def register_client(self, client_id):
        self.client_queues[client_id] = queue.Queue()

class FTL0Client:
    """Simple FTL0 client for testing."""
    def __init__(self, client_id, radio: MockRadio):
        self.client_id = client_id
        self.radio = radio
        self.files = {}  # file_num: {data, expected_size}
        self.radio.register_client(client_id)
    
    def request_file(self, file_num, total_size):
        """Send RQ frame."""
        self.files[file_num] = {"data": bytearray(total_size), "expected_size": total_size}
        self.radio.send_from_client(self.client_id, "RQ", file_num, [(0, total_size - 1)])
    
    def handle_server_frame(self):
        """Process incoming frames."""
        try:
            src, frame_type, file_num, offset, data, holes = self.radio.client_queues[self.client_id].get_nowait()
            if frame_type == "SC" and file_num in self.files:
                file_data = self.files[file_num]["data"]
                file_data[offset:offset + len(data)] = data
                
                # Request missing holes
                missing = self._get_missing_holes(file_num)
                if missing:
                    self.radio.send_from_client(self.client_id, "RQ", file_num, missing)
            
            elif frame_type == "EF" and file_num in self.files:
                expected_crc = self._crc16(self.files[file_num]["data"])
                if data == expected_crc:  # data is CRC in EF
                    del self.files[file_num]  # Complete
        except queue.Empty:
            pass
    
    def _get_missing_holes(self, file_num):
        data = self.files[file_num]["data"]
        size = self.files[file_num]["expected_size"]
        holes = []
        start = None
        for i in range(size):
            if data[i] == 0 and start is None:
                start = i
            elif data[i] != 0 and start is not None:
                holes.append((start, i - 1))
                start = None
        if start is not None:
            holes.append((start, size - 1))
        return holes
    
    def _crc16(self, data):
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 1:
                    crc = (crc >> 1) ^ 0x8408
                else:
                    crc >>= 1
        return crc ^ 0xFFFF

@pytest.fixture
def full_stack(tmp_path):
    storage_dir = str(tmp_path / "storage")
    storage = FileStorage(storage_dir)
    
    radio = MockRadio()
    
    download_server = FTL0DownloadServer(storage=storage, radio=radio)
    
    return storage, radio, download_server

def test_end_to_end_download(full_stack):
    """End-to-end: Client requests file → server sends chunks → client reassembles."""
    storage, radio, download_server = full_stack
    
    # Server has file
    body = b"PACSAT full stack test data 12345"
    pfh = PFH(name="FULLTEST", ext="TXT", type=0, size=len(body))
    file_num = storage.add_file("SERVER-0", pfh, body)
    
    # Client
    client = FTL0Client("client1", radio)
    client.request_file(file_num, len(body))
    
    # Server processes request
    client_id, frame_type, req_file_num, holes = radio.server_queue.get()
    download_server.handle_request(req_file_num, holes, client_id)
    
    # Client processes server response
    client.handle_server_frame()
    client.handle_server_frame()  # EF
    
    # Verify client has complete file
    assert file_num not in client.files

def test_multi_client_fairness(full_stack):
    """Test multiple clients requesting different files."""
    storage, radio, download_server = full_stack
    
    # Two files
    file1 = storage.add_file("UP1-0", PFH(name="FILE1   ", size=20), b"file one data 123456")
    file2 = storage.add_file("UP2-0", PFH(name="FILE2   ", size=30), b"file two longer data 1234567890")
    
    client1 = FTL0Client("c1", radio)
    client2 = FTL0Client("c2", radio)
    
    client1.request_file(file1, 20)
    client2.request_file(file2, 30)
    
    # Process both requests
    for _ in range(2):
        client_id, _, req_file_num, holes = radio.server_queue.get()
        download_server.handle_request(req_file_num, holes, client_id)
    
    # Both clients should receive their chunks
    client1.handle_server_frame()
    client2.handle_server_frame()

def test_network_loss_simulation(full_stack):
    """Simulate packet loss - client requests missing chunks."""
    storage, radio, download_server = full_stack
    
    body = b"0123456789ABCDEFGHIJ"
    file_num = storage.add_file("LOSS-0", PFH(name="LOSS    ", size=len(body)), body)
    
    client = FTL0Client("lossy", radio)
    client.request_file(file_num, len(body))
    
    # Server sends all chunks
    client_id, _, req_file_num, holes = radio.server_queue.get()
    download_server.handle_request(req_file_num, holes, client_id)
    
    # Simulate loss: client only receives some chunks
    received = []
    while not radio.client_queues["lossy"].empty():
        frame = radio.client_queues["lossy"].get()
        if frame[1] == "SC" and frame[3] == 10:  # Drop chunk at offset 10
            continue
        received.append(frame)
    
    # Client processes received
    for frame in received:
        if frame[1] == "SC":
            client.handle_server_frame()
    
    # Client should request missing hole
    sent = radio.server_queue.get()
    assert sent[2] == file_num  # RQ for same file
    assert len(sent[3]) > 0  # Has holes
    
    # Server resends missing
    download_server.handle_request(sent[2], sent[3], sent[0])
    
    # Client gets final chunks
    client.handle_server_frame()
    client.handle_server_frame()
    
    assert file_num not in client.files  # Complete despite loss
