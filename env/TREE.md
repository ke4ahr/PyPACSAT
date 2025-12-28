pacsat-ground-station/
├── LICENSE                          # GNU General Public License v3.0
├── README.md                        # Project overview, setup, usage
├── ARCHITECTURE.md                  # System architecture document
├── setup.py                         # Package metadata and dependencies
├── requirements.txt                 # Python dependencies
│
├── pacsat/                          # Core protocol implementation
│   ├── __init__.py
│   ├── file_storage.py              # Conventional storage with subdirs, trash, cleanup
│   ├── pfh.py                       # PFH parsing/generation with advanced items
│   ├── ftl0_server.py               # FTL0 upload/download server
│   ├── broadcast.py                 # Directory broadcast (PID 0xBD) scheduler
│   ├── telemetry.py                 # Telemetry parsing (WOD, realtime)
│   ├── radio_connected.py           # Connected mode support
│   └── groundstation.py             # Main station logic, async scheduler
│
├── PyHamREST1/
│   └── rest.py                      # FastAPI REST server (upload, download, listing, etc.)
│
├── PyAX25_22/
│   └── ax25.py                      # AX.25 framing
│
├── PyXKISS/
│   └── kiss-xkiss.py                # KISS/XKISS protocol
│
├── PyAGW3/
│   └── agwpe.py                     # AGWPE TCP client
│
├── tests/                           # Test suite
│   ├── test_file_storage.py
│   ├── test_pfh.py
│   ├── test_ftl0_server.py
│   ├── test_ftl0_server_integration.py
│   ├── test_ftl0_server_error_recovery.py
│   ├── test_directory_broadcaster.py
│   ├── test_ftl0_full_stack.py
│   └── __init__.py
│
└── docs/                            # Documentation
    ├── agwpe_frame_formats.tex
    └── agwpe_connected_mode.tex
