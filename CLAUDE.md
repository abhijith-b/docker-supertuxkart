# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Docker-based SuperTuxKart (STK) server deployment project. SuperTuxKart is an open-source kart racing game, and this repository provides containerized server infrastructure with addon management capabilities.

## Key Commands

### Docker Operations
- **Build image**: `docker build -t stk-server .`
- **Run server with docker-compose**: `docker-compose up -d`
- **View logs**: `docker-compose logs`
- **Stop server**: `docker-compose down`
- **Access network console**: `docker exec -it my-stk-server supertuxkart --connect-now=127.0.0.1:2759 --network-console`
- **Access network console with password**: `docker exec -it my-stk-server supertuxkart --connect-now=127.0.0.1:2759 --server-password=MY_SERVER_PASSWORD --network-console`

### Addon Management
- **Download and install addons**: `python3 addons.py`
- **Install tqdm for progress bars**: `pip install tqdm` or `sudo apt install python3-tqdm`

## Architecture

### Core Components

1. **Multi-stage Dockerfile**:
   - Build stage: Compiles STK from source with server-only configuration
   - Runtime stage: Minimal Ubuntu image with runtime dependencies only
   - Uses non-root user `stk` for security

2. **Server Configuration** (`server_config.xml`):
   - XML-based configuration for STK server settings
   - Supports WAN/LAN modes, player limits, game modes, and database integration
   - Includes SQLite database support for ban lists and player reports

3. **Startup Script** (`start.sh`):
   - Handles user authentication with STK addons server
   - Manages server startup with configurable logging
   - Supports AI kart injection based on environment variables

4. **Addon Management** (`addons.py`):
   - Python script for downloading and managing STK addons (tracks, karts, arenas)
   - Multi-threaded downloads with progress reporting
   - Docker volume-aware directory structure
   - Supports filtering by addon type, rating, and recency

### Directory Structure
```
/stk/
├── server_config.xml     # Server configuration
├── stkservers.db        # SQLite database for server management
├── motd.txt             # Message of the day
└── supertuxkart/addons/ # Addon installation directory
    ├── tracks/          # Track addons
    └── karts/           # Kart addons
```

### Environment Variables
- `USERNAME`: STK addons account username (required for WAN servers)
- `PASSWORD`: STK addons account password (required for WAN servers)  
- `AI_KARTS`: Number of AI karts to add to server (optional)

### Network Ports
- `2757/udp`: Server discovery port
- `2759/udp`: Main server port

## Development Notes

- The server is built from STK source code with `SERVER_ONLY=ON` cmake flag
- SQLite integration is enabled for advanced server management features
- The addon system supports tracks (format > 5), karts, and arenas
- Server supports various game modes: normal race, time trial, soccer, free-for-all, capture the flag
- Database tables can be shared across multiple server instances