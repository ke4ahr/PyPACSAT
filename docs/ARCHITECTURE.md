# PACSAT Ground Station Architecture

**Project**: Modern PACSAT Ground Station Revival  
**Version**: 1.0.0  
**Date**: December 27, 2025  
**Authors**: Kris Kirby, KE4AHR
**License**: GNU General Public License v3.0

## 1. Overview

The **PACSAT Ground Station** is a complete, open-source implementation of a ground-based store-and-forward file server compatible with the original PACSAT satellite protocol suite (UO-14, AO-16, LO-19, UO-22).

The system faithfully implements:
- FTL0 (File Transfer Level 0) protocol
- PACSAT File Header (PFH) with checksums
- Broadcast (PID 0xBB) and directory (PID 0xBD) protocols
- Conventional file storage with subdirectory hierarchy (k/ki/kir/kirby)
- Full AX.25 v2.2 framing
- KISS/XKISS (standard + extended + polled)
- REST API with JWT authentication and refresh tokens
- Multi-database support (SQLite default, MySQL/PostgreSQL optional)

The goal is **functional parity** with 1990s PACSAT satellites while using modern, secure, and maintainable architecture.

## 2. High-Level Architecture

    +---------------------+
    |   Client Tools      |  (curl, web UI, scripts)
    +----------+----------+
               |
               v
    +---------------------+     +-------------------+
    |   FastAPI REST API  |<--->| JWT Auth + Refresh|
    |   (PyHamREST1)      |     | Token Blacklist   |
    +----------+----------+     +-------------------+
               |
               v
    +---------------------+     +-------------------+
    |   Ground Station    |<--->| File Storage      |
    |   Core Logic        |     | (SQLite indexed)  |
    +----------+----------+     +-------------------+
               |
               v
    +---------------------+     +-------------------+
    |   Radio Interface   |<--->| KISS/XKISS Serial |
    |   (pacsat-serial)   |     | Dire Wolf TCP     |
    +---------------------+     +-------------------+
               |
               v
    +---------------------+
    |   Physical Radio    |
    |   (TNC / Soundcard) |
    +---------------------+

## 3. Component Breakdown

### 3.1 Core Modules

| Module                     | Purpose                        | Key Features                                                                 |
|----------------------------|--------------------------------|------------------------------------------------------------------------------|
| `pacsat/file_storage.py`   | Conventional file storage      | Subdirectory hierarchy (k/ki/kir/), PFH+body files, SQLite index, soft delete + recovery |
| `pacsat/pfh.py`            | PFH parsing/generation         | Full round-trip serialization, checksum validation, advanced optional items |
| `pacsat/ftl0_server.py`    | FTL0 protocol                  | Bidirectional upload/download server, hole lists, CRC, error recovery        |
| `pacsat/broadcast.py`      | Broadcast scheduler            | On-demand + periodic directory/file broadcast                                |
| `pacsat/telemetry.py`      | Telemetry parsing              | WOD and realtime frame parsing                                               |
| `pacsat/radio_connected.py`| Connected mode support         | AX.25 connected sessions (SABM/UA/DISC/I-frames)                             |
| `pacsat/groundstation.py`  | Main station logic             | Async scheduler, periodic tasks, beacon transmission                         |

### 3.2 API Layer

| Module               | Purpose       |
|----------------------|---------------|
| `PyHamREST1/rest.py` | FastAPI server|
| Endpoints            | Upload, Download (with Range), Listing, Search, Stats, Cleanup, User management, Telemetry |

### 3.3 Authentication & Security

- **JWT access tokens** (30 min)
- **Refresh tokens** (7 days)
- **Token rotation** (new refresh on use)
- **SQLite token blacklist** (secure logout)
- **Role-based access** (admin/user)

### 3.4 Database

- **Primary**: SQLite (`pacsat.db`) – self-contained
- **Optional**: MySQL / PostgreSQL via SQLAlchemy
- **Connection pooling** optimized per backend
- **Full-text search** (SQLite FTS5)

### 3.5 Scheduling & Maintenance

- **Async scheduler** (asyncio)
- **Periodic tasks**:
  - Blacklist cleanup (hourly)
  - Storage cleanup (configurable)
  - Beacon transmission
  - Directory broadcast

## 4. Data Flow Examples

### File Upload (REST → Storage)

1. Client POST /upload with file
2. FastAPI validates JWT
3. Generates PFH (8.3 filename)
4. Calls `FileStorage.add_file()`
5. File written atomically to subdirectory
6. SQLite index updated
7. Returns file number

### File Download (Client → Radio)

1. Client requests file via FTL0 (after directory broadcast)
2. Ground station transmits chunks (PID 0xBB)
3. Or via REST GET /download/{file_num}

### On-Demand Broadcast

1. Client requests file via REST /broadcast/schedule
2. File added to priority queue
3. Broadcast scheduler transmits immediately

## 5. Security Model

- All REST endpoints require JWT
- Admin role for user/config management
- Users can only delete own files (configurable)
- Token blacklist prevents reuse after logout
- Refresh token rotation
- Rate limiting possible via middleware

## 6. Deployment Options

- **Standalone** (Raspberry Pi + radio)
- **Server** (multi-user BBS)
- **Docker** ready
- **Headless** or with web UI

## 7. References & Heritage

- Original PACSAT Protocol Specification (Jeff Ward G0/K8KA, Harold Price NK6K)
- AGWPE TCP/IP API Tutorial (Pedro Colla LU7DID, George Rossopoulos SV2AGW)
- AX.25 Link-Layer Protocol Specification v2.2

**73 de the PACSAT Revival Project**  
**December 27, 2025 — The revival is complete.** 🚀

Copyright (C) 2025-2026 Kris Kirby, KE4AHR
Licensed under the GPLv3.0
