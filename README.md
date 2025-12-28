# PACSAT Ground Station

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
- PACSAT File Header (PFH) handling with advanced optional items
- Broadcast protocol (directory PID 0xBD, file chunks PID 0xBB)
- Conventional file storage with k/ki/kir/kirby subdirectory hierarchy
- Soft delete with recovery ("trash" system)
- JWT authentication with refresh tokens and blacklist
- FastAPI REST interface
- AGWPE TCP and KISS/XKISS serial radio interfaces
- Telemetry parsing
- Connected mode support (for legacy compatibility)

The project achieves **functional parity** with 1990s PACSAT satellites and exceeds them in security and user experience.

## Features

- **FTL0 Upload & Download Server** – Full hole list handling, CRC verification, chunk reassembly, error recovery
- **Directory Broadcast** – Periodic and on-demand PFH broadcasting (PID 0xBD)
- **File Management** – Upload (single/batch), download (with HTTP Range), listing, search, deletion (with recovery)
- **Security** – JWT access/refresh tokens, token rotation, SQLite blacklist for secure logout, role-based access (admin/user)
- **Radio Support** – KISS/XKISS serial, Dire Wolf TCP, AGWPE TCP
- **Maintenance** – Async periodic tasks: blacklist cleanup, storage cleanup, beacon transmission
- **Telemetry** – Parsing of Whole Orbit Data (WOD) and realtime frames
- **Testing** – Comprehensive unit, integration, and error recovery tests

## Installation

### Prerequisites

- Python 3.10+
- pip
- Git

### Quick Start

    git clone https://github.com/yourusername/pacsat-ground-station.git
    cd pacsat-ground-station
    pip install -r requirements.txt

    # Run the ground station
    python -m pacsat.groundstation --config config.yaml

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

### KISS Serial (Hardware TNC)

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
