# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-12-27T00:00+00:00

### Added
- Complete bidirectional FTL0 file transfer protocol (upload and download server)
- Full PACSAT File Header (PFH) parsing and generation with advanced optional items (compression_type, body_description, download_count, priority, forwarding destinations)
- Broadcast protocol implementation (PID 0xBB file chunks, PID 0xBD directory broadcast)
- Conventional file storage with k/ki/kir/kirby subdirectory hierarchy
- Soft delete with .trash/ recovery system
- JWT authentication with access/refresh tokens, token rotation, and SQLite blacklist for secure logout
- FastAPI REST interface with endpoints for upload (single/batch), download (with Range), listing, search, deletion, recovery, stats, telemetry
- AGWPE TCP and KISS/XKISS serial radio interfaces
- Connected mode AX.25 support (optional)
- Telemetry parsing (Whole Orbit Data and realtime frames)
- Async periodic maintenance tasks (blacklist cleanup, storage cleanup, beacon, directory broadcast)
- Comprehensive unit, integration, and error recovery test suite
- Full documentation (ARCHITECTURE.md, man pages, README)
- GPLv3 license and packaging (setup.py)

### Security
- Role-based access control (admin/user)
- Ownership protection on file deletion
- Token revocation and rotation

Initial stable release – achieves full functional parity with original PACSAT satellites while adding modern security and usability.

**73 de the PACSAT Revival Project**  
The uplink is open. The downlink is waiting.

Copyright (C) 2025-2026 Kris Kirby, KE4AHR
Licensed under GPLv3.0
