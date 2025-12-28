# PyPACSAT: A Full PACSAT Server/Client in Python + Extras 

**A Modern Revival of the PACSAT Store-and-Forward Satellite Protocol**

**Version**: 1.0.0  
**Date**: December 27, 2025  
**License**: GNU General Public License v3.0  
**Authors**: Kris Kirby, KE4AHR

## Overview

This project is a complete, open-source Python implementation of a ground station and satellite protocols for the PACSAT (Packet Radio Satellite) store-and-forward file transfer system, originally used on amateur radio satellites such as UO-14, AO-16, LO-19, SEDSAT-1 / SO-33, and UO-22.

The system provides **full compatibility** with the original PACSAT protocol while adding modern security, usability, and reliability features.

Key capabilities:
- Bidirectional FTL0 file transfer (upload and download)
- Broadcast protocol (directory PID 0xBD, file chunks PID 0xBB)
- AGWPE TCP and KISS/XKISS serial radio interfaces
- Conventional file storage with k/ki/kir/kirby subdirectory hierarchy
- Soft delete with recovery ("trash" system)
- PACSAT File Header (PFH) handling with advanced optional items
- Connected mode support (for legacy compatibility)
- Telemetry parsing
- FastAPI REST interface
- JWT authentication with refresh tokens and blacklist

The project achieves **functional parity** with 1990s PACSAT satellites and exceeds them in security and user experience.

## Features

- **FTL0 Upload & Download Server** – Full hole list handling, CRC verification, chunk reassembly, error recovery
- **Directory Broadcast** – Periodic and on-demand PFH broadcasting (PID 0xBD)
- **File Management** – Upload (single/batch), download (with HTTP Range), listing, search, deletion (with recovery)
- **Maintenance** – Async periodic tasks: blacklist cleanup, storage cleanup, beacon transmission
- **Radio Support** – KISS/XKISS serial, Dire Wolf TCP, AGWPE TCP
- **Telemetry** – Parsing of Whole Orbit Data (WOD) and realtime frames
- **Security** – JWT access/refresh tokens, token rotation, SQLite blacklist for secure logout, role-based access (admin/user)
- **Testing** – Comprehensive unit, integration, and error recovery tests

## Installation

### Prerequisites

- Python 3.10+
- pip
- Git

### Quick Start

** DOES NOT WORK AT THE MOMENT **

    git clone https://github.com/ke4ahr/PyPACSAT.git
    cd PyPACSAT
    pip install -r requirements.txt

    # Run the ground station
    python -m pacsat.groundstation --config config.yaml

*I will probably re-work this to use a Python venv.*

The REST API will be available at http://localhost:8000  
OpenAPI docs at http://localhost:8000/docs

## Configuration

Create `config.yaml` in the project root:

    callsign: G0K8KA-0
    storage_dir: ./pacsat_files
    http_port: 8000

    # Radio interface
    radio:
      type: kiss_serial
      device: /dev/ttyUSB0
      baudrate: 9600

    # Alternative: AGWPE TCP (e.g., Dire Wolf)
    # type: agwpe_tcp
    # host: 127.0.0.1
    # port: 8000

    # Scheduling
    directory_broadcast_interval: 30  # minutes between full directory cycles
    cleanup_interval_hours: 24       # storage cleanup
    cleanup_max_age_days: 90
    cleanup_max_files: 5000

    # JWT
    jwt_secret_key: "change-this-to-a-strong-secret"
    jwt_access_expire_minutes: 30
    jwt_refresh_expire_days: 7

## REST API

Base URL: http://localhost:8000

### Authentication
- POST `/token` – Login with username/password → returns access + refresh token
- POST `/token/refresh` – Exchange refresh token for new access + refresh tokens
- POST `/logout` – Revoke current refresh token

### Core Endpoints
- POST `/upload` – Upload single file
- POST `/upload/batch` – Upload multiple files
- GET `/download/{file_num}` – Download file (supports Range requests for resumable downloads)
- GET `/download/{file_num}/raw` – Download raw stored file (PFH + body)
- GET `/files` – List files (pagination, sorting: newest/oldest/largest/smallest/filename/callsign, filtering)
- GET `/search` – Full-text search (filename, callsign, description)
- DELETE `/files/{file_num}` – Soft delete (moves to trash)
- DELETE `/files/{file_num}/permanent` – Permanent delete (admin only)
- GET `/trash` – List deleted files
- POST `/recover/{trash_filename}` – Recover file from trash
- GET `/stats` – Storage statistics
- GET `/telemetry/status` – Latest satellite telemetry

Full interactive documentation at `/docs` (Swagger UI) and `/redoc`.

## Radio Integration

The ground station supports multiple radio backends:

### KISS/XKISS Serial (Hardware TNC)

    radio:
      type: kiss_serial
      device: /dev/ttyUSB0
      baudrate: 9600

### AGWPE TCP (Dire Wolf, soundcard modem)

    radio:
      type: agwpe_tcp
      host: 127.0.0.1
      port: 8000

## Development

    # Run tests
    pytest tests/ -v

    # Run with hot reload (API only)
    uvicorn PyHamREST1.rest:app --reload --port 8000

## Planned Features

- FBB / RLI / Winlink Forwarding Protocol Integration from [PyFBB](https://github.com/ke4ahr/PyFBB/)
- PhilFlag Compatibility with [rax25kb](https://github.com/ke4ahr/rax25kb/) to support some radios with built-in TNCs.
- Web UI Configurator
- Command Line Interface (CLI)
- GPIO input/output
- Full capabilities over REST

## CAVEATS / DISCLAIMER

- This software is not intented for use on, in, aboard and/or in connection with any space craft, celestial object, or entity for any purpose, or no purpose.
- This software is written in an interpreted computer language. It is not written in a compiled computer language. As a result, it is not designed to be a high-performance solution. It is extremely inefficient in terms of memory and storage use. It does not have guard rails installed to prevent memory corruption, buffer overflows, general misbehavior or malfeasance.
- The software is intended to be a complete open-source reference implementation.
- This software is not designed to survive re-entry into the atmosphere of Earth, and/or any other ceslestial objects including objects lacking an atmosphere. 
- The software is not certified for use at or above the speed of sound, or underwater.
- This software may not be returned to the place of purchase in exchange for an item of equal or lesser value. 
- The software does not provide the consumer with super-, greater-, or any lesser-powers. 
- Do not fold, spindle, or mutilate. 
- Do not spin, fold, or defenestrate.
- Do not taunt Happy Fun Ball.

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Original PACSAT designers: Jeff Ward (G0/K8KA), Harold Price (NK6K)
- AMSAT volunteers and staff, N4HY, N8DEU
- KISS: KA9Q, K6THZ (K3MC), G8BPQ
- AGWPE: George Rossopoulos (SV2AGW)
- NOS: KA9Q
- TNOS: KO4KS
- Protocol documents from TAPR, AMSAT, F6FBB, and W0RLI
- Dire Wolf developers
- KD4FM, N4MSN, KB5AWP, N4HHE, WD4CPF

**73 de the PACSAT Revival Project**  
**December 27, 2025 — The satellites live again** 🚀

The uplink is open. The downlink is waiting. Good DX!

Copyright (C) 2025-2026 Kris Kirby, KE4AHR 
Licensed under GPLv3.0
