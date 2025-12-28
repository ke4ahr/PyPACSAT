# Requirements.txt Dependencies

**Project**: PACSAT Ground Station  
**Version**: 1.0.0  
**Date**: December 27, 2025

## Core Dependencies

- **fastapi>=0.110.0**  
  High-performance web framework for building the REST API endpoints (upload, download, listing, etc.)

- **uvicorn[standard]>=0.29.0**  
  ASGI server to run the FastAPI application with auto-reload and production capabilities

- **pydantic>=2.7.0**  
  Data validation and settings management using Python type annotations (used throughout for config and models)

- **python-jose[cryptography]>=3.3.0**  
  JSON Web Token implementation for JWT authentication (access + refresh tokens)

- **passlib[bcrypt]>=1.7.4**  
  Password hashing library using bcrypt for secure user credential storage

- **python-multipart>=0.0.9**  
  Handles multipart/form-data requests for file uploads in FastAPI

## Database & ORM

- **sqlalchemy>=2.0.0**  
  SQL toolkit and ORM for database operations (supports SQLite, MySQL, PostgreSQL)

- **alembic>=1.13.0**  
  Database migration tool (for future schema changes)

## Optional Database Drivers

- **pymysql>=1.1.0**  
  MySQL driver for SQLAlchemy (optional backend)

- **psycopg2-binary>=2.9.9**  
  PostgreSQL driver for SQLAlchemy (optional backend)

## Configuration & Utilities

- **pyyaml>=6.0.1**  
  YAML parser for configuration file loading

## Testing

- **pytest>=8.1.0**  
  Testing framework for unit and integration tests

- **pytest-asyncio>=0.23.0**  
  Async support for pytest (used in FastAPI and async tasks)

## Radio Interface

- **pyserial>=3.5**  
  Serial port communication for KISS/XKISS TNC interface

**All dependencies are pinned to stable, modern versions** for reliability and security.

**73 – Dependencies complete**  
**December 27, 2025** 🚀

Copyright (C) 2025-2026 Kris Kirby, KE4AHR
Licensed under GPLv3.0
