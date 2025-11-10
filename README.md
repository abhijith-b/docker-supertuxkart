# Docker SuperTuxKart Server

This is a docker image for deploying a [SuperTuxKart](https://supertuxkart.net) server.

## What is SuperTuxKart?

SuperTuxKart (STK) is a free and open-source kart racing game, distributed under the terms of the GNU General Public License, version 3. It features mascots of various open-source projects. SuperTuxKart is cross-platform, running on Linux, macOS, Windows, and Android systems. Version 1.0 was officially released on April 20, 2019.

SuperTuxKart started as a fork of TuxKart, originally developed by Steve and Oliver Baker in 2000. When TuxKart's development ended around March 2004, a fork as SuperTuxKart was conducted by other developers in 2006. SuperTuxKart is under active development by the game's community.

> [wikipedia.org/wiki/SuperTuxKart](https://en.wikipedia.org/wiki/SuperTuxKart)

![logo](https://raw.githubusercontent.com/jwestp/docker-supertuxkart/master/supertuxkart-logo.png)

## Getting Started

### Prerequisites

- **Docker** (with Compose v2) or **Podman** with podman-compose
- **Git** (to clone the repository)
- **Subversion (SVN)** (optional, only needed to download game assets locally)
- **~2GB disk space** for the Docker image and database
- **UDP ports 2757 and 2759** open (for game server)

### Quick Start

1. **Clone the repository:**
```bash
git clone https://github.com/jwestp/docker-supertuxkart.git
cd docker-supertuxkart
```

2. **Download game assets (required):**

The game assets (~1.5GB) need to be available. Choose one approach:

**Option A: Download with SVN (one-time download):**
```bash
# Install SVN if needed
sudo apt install subversion          # Ubuntu/Debian
sudo dnf install subversion          # Fedora
brew install subversion              # macOS

# Download assets
svn co https://svn.code.sf.net/p/supertuxkart/code/stk-assets stk-assets

# For Fedora/RHEL with SELinux, fix permissions
chcon -R system_u:object_r:container_file_t:s0 ./stk-assets/
```

**Option B: Use pre-built Docker image (downloads during build):**
```bash
# Skip SVN download and let Docker build handle it
# Just run: docker compose build
```

3. **Start the server:**
```bash
docker compose up -d
```

4. **Verify it's running:**
```bash
docker compose logs -f
# Wait for: "STKHost: Listening has been started."

# Check database was initialized
docker compose exec stk-server sqlite3 /stk/stkservers.db ".tables"
# Should show: ip_ban  ipv6_ban  online_id_ban  player_reports
```

---

## How to use this image

The image exposes ports 2759/udp (server) and 2757/udp (server discovery). The server should be configured using your own server config file. The config file template can be found in `server_config.xml`. Modify it according to your needs and mount it at `/stk/server_config.xml`.

This enhanced version includes SQLite database support for advanced server management, addon support, and persistent data storage.

### Hosting a server in your local network

**Using docker-compose (Recommended):**
```bash
git clone <repository>
cd docker-supertuxkart
docker compose up -d
```

**Or with docker run:**
```bash
docker run --name my-stk-server \
           -d \
           -p 2757:2757/udp \
           -p 2759:2759/udp \
           -v $(pwd)/server_config.xml:/stk/server_config.xml \
           -v $(pwd)/stk/supertuxkart:/stk/supertuxkart \
           -v $(pwd)/stk/stkservers.db:/stk/stkservers.db \
           -v $(pwd)/motd.txt:/stk/motd.txt \
           stk-server:latest
```

### Hosting a server on the internet (WAN)

For hosting a server on the internet (by setting `wan-server` to `true` in `server_config.xml`) it is required to log in with your STK account. You can register a free account [here](https://online.supertuxkart.net/register.php).

**Using docker-compose:**

Edit `docker-compose.yml` to set your credentials:
```yaml
environment:
  USERNAME: "your_stk_username"
  PASSWORD: "your_stk_password"
```

Then update `server_config.xml`:
```xml
<wan-server value="true" />
```

**Or with docker run:**
```bash
docker run --name my-stk-server \
           -d \
           -p 2757:2757/udp \
           -p 2759:2759/udp \
           -v $(pwd)/server_config.xml:/stk/server_config.xml \
           -v $(pwd)/stk/supertuxkart:/stk/supertuxkart \
           -v $(pwd)/stk/stkservers.db:/stk/stkservers.db \
           -v $(pwd)/motd.txt:/stk/motd.txt \
           -e USERNAME=myusername \
           -e PASSWORD=mypassword \
           stk-server:latest
```

### Adding AI Karts

You can add AI karts to your server by setting the `AI_KARTS` environment variable.

**Using docker-compose:**

Edit `docker-compose.yml`:
```yaml
environment:
  USERNAME: "your_stk_username"
  PASSWORD: "your_stk_password"
  AI_KARTS: 4  # Number of AI karts to add
```

Then restart:
```bash
docker compose restart
```

**Or with docker run:**
```bash
docker run --name my-stk-server \
           -d \
           -p 2757:2757/udp \
           -p 2759:2759/udp \
           -v $(pwd)/server_config.xml:/stk/server_config.xml \
           -v $(pwd)/stk/supertuxkart:/stk/supertuxkart \
           -v $(pwd)/stk/stkservers.db:/stk/stkservers.db \
           -v $(pwd)/motd.txt:/stk/motd.txt \
           -e USERNAME=myusername \
           -e PASSWORD=mypassword \
           -e AI_KARTS=4 \
           stk-server:latest
```

### Accessing the network console

You can access the interactive network console with the following command:

```
docker exec -it my-stk-server supertuxkart --connect-now=127.0.0.1:2759 --network-console
```

If your server is password secured use the following command:

```
docker exec -it my-stk-server supertuxkart --connect-now=127.0.0.1:2759 --server-password=MY_SERVER_PASSWORD --network-console
```

### Using docker-compose (Recommended)

Clone this repository and edit the `docker-compose.yml` file to configure your server:

1. **Update credentials**: Edit the `USERNAME` and `PASSWORD` in the environment section
2. **Persistent storage** (automatically created):
   - `./server_config.xml`: Server configuration
   - `./stk/stkservers.db`: SQLite database ✅ auto-initialized with schema
   - `./stk/supertuxkart/`: Game data, addons, configs
   - `./motd.txt`: Message of the day
3. **Network settings**: IPv6 support is enabled by default

**First run**:
```bash
docker compose up -d
# Database is created and initialized automatically
```

**Verify database was created**:
```bash
docker compose exec stk-server sqlite3 /stk/stkservers.db ".tables"
# Output: ip_ban  ipv6_ban  online_id_ban  player_reports
```

```yaml
services:
  stk-server:
    image: stk-server
    restart: unless-stopped
    volumes:
      - ./server_config.xml:/stk/server_config.xml
      - ./stk/supertuxkart:/stk/supertuxkart
      - ./stk/stkservers.db:/stk/stkservers.db
      - ./motd.txt:/stk/motd.txt
    environment:
      USERNAME: "your_stk_username"
      PASSWORD: "your_stk_password"
      #AI_KARTS: 1
    ports:
      - "2757:2757/udp"
      - "2759:2759/udp"
```

**Note**: The database file (`./stk/stkservers.db`) is created automatically on first run if it doesn't exist.

**Common commands:**
- **Start server**: `docker compose up -d`
- **View logs**: `docker compose logs -f`
- **Stop server**: `docker compose down`
- **Rebuild**: `docker compose build && docker compose up -d`
- **Restart**: `docker compose restart`

**Note**: Docker Compose v2+ uses `docker compose` (space). If you have an older version, use `docker-compose` (hyphen) instead.

## Addon Management

This repository includes an enhanced addon management system (`addons.py`) that automatically downloads and installs SuperTuxKart addons (tracks, karts, and arenas).

### Installing Addons

1. **Install dependencies** (optional but recommended):
   ```bash
   pip install tqdm
   # or
   sudo apt install python3-tqdm
   ```

2. **Basic usage** (interactive mode):
   ```bash
   python3 addons.py
   ```

3. **Command-line options**:
   ```bash
   # List what would be installed without downloading
   python3 addons.py --list-only
   
   # Non-interactive mode (auto-confirm installation)
   python3 addons.py --non-interactive
   
   # Use different filters
   python3 addons.py --filter all              # All addons
   python3 addons.py --filter tracks-only      # Only tracks/arenas
   python3 addons.py --filter high-rated       # Addons rated ≥2.8 stars
   python3 addons.py --filter recent           # Updated within last year
   python3 addons.py --filter default          # Default selection (recommended)
   
   # Skip updating addon database (use cached version)
   python3 addons.py --skip-update
   
   # Show detailed filtering decisions (debug mode)
   python3 addons.py --debug --list-only
   
   # Use system STK directory (for native installations)
   python3 addons.py --addons-dir ~/.local/share/supertuxkart/addons
   
   # Get help
   python3 addons.py --help
   ```

### Features

- **Multi-threaded downloads** with progress bars (up to 5 concurrent downloads)
- **Multi-environment support** - automatically detects Docker vs native STK installations
- **Smart filtering** with multiple preset options:
  - **Default**: Tracks, arenas, and featured karts only (recommended for most users)
  - **All**: Every available addon including all karts (~5GB download)
  - **Tracks-only**: Only tracks and arenas, no karts
  - **High-rated**: Only addons with user rating ≥2.8 stars
  - **Recent**: Only addons updated within the last year
- **Automatic updates** for existing addons when newer revisions are available
- **Environment-aware** directory handling:
  - **Docker**: Uses `./stk/addons/` when `docker-compose.yml` present
  - **System STK**: Uses `~/.local/share/supertuxkart/addons/` for native installations
  - **Custom**: Manual override with `--addons-dir`
- **Resume capability** - interrupted downloads can be resumed safely
- **Skip duplicate downloads** - already downloaded files are automatically skipped
- **Safe cancellation** - Ctrl+C preserves completed installations

### Directory Structure

After starting the server and running the addon script, your project directory will look like:
```
docker-supertuxkart/
├── Dockerfile               # Docker build configuration
├── docker-compose.yml       # Docker Compose configuration
├── server_config.xml        # STK server configuration
├── start.sh                 # Container entrypoint script
├── init.sql                 # Database schema
├── motd.txt                 # Message of the day
├── addons.py                # Addon management script
├── README.md                # This file
├── stk/
│   ├── stkservers.db        # SQLite database (auto-created)
│   ├── supertuxkart/        # Game data directory
│   │   ├── config.xml       # User config (auto-created)
│   │   ├── players.xml      # Player data (auto-created)
│   │   └── addons/          # Downloaded addons
│   │       ├── tracks/      # Track addons
│   │       ├── karts/       # Kart addons
│   │       └── addons.xml   # Addon database
│   └── addons/              # Convenience symlink
└── stk-assets/              # Game assets (optional, for local build)
```

### Usage Examples

```bash
# Interactive installation with default filter (recommended for first-time setup)
python3 addons.py

# Quick non-interactive installation
python3 addons.py --non-interactive --filter default

# Download all available addons (large download ~5GB)
python3 addons.py --non-interactive --filter all

# Only install highly-rated tracks and arenas
python3 addons.py --filter tracks-only

# Preview what would be installed without downloading
python3 addons.py --list-only --filter all

# Install addons for native STK installation (auto-detected on Fedora/Linux)
python3 addons.py --addons-dir ~/.local/share/supertuxkart/addons

# Force Docker mode even when system STK is present
python3 addons.py --addons-dir ./stk/addons
```

### Troubleshooting

**Download failures**: If some addons fail to download, simply run the script again. Already completed downloads will be skipped.

**Interrupted installation**: Press Ctrl+C to cancel. Completed addons remain installed. Run the script again to continue.

**Disk space**: Check available space before running `--filter all` (requires ~5GB).

**Permission issues**: Ensure the current user has write access to the `stk/` directory.

**Important**: Restart your STK server container after adding new addons:
```bash
docker-compose restart
```

## Platform-Specific Setup

### Fedora/RHEL Systems (SELinux)

If you're running on Fedora or RHEL with SELinux in **Enforcing** mode, follow these steps:

**1. Install SVN:**
```bash
sudo dnf install subversion
```

**2. Download assets:**
```bash
svn co https://svn.code.sf.net/p/supertuxkart/code/stk-assets stk-assets
```

**3. Fix SELinux context (Required for Fedora/RHEL):**
```bash
# Check SELinux status
getenforce

# If output is "Enforcing", fix the context:
chcon -R system_u:object_r:container_file_t:s0 ./stk-assets/
```

**Why SELinux fix is needed**: Docker/Podman on SELinux systems enforces file access policies. Without the correct context, containers cannot access the `stk-assets` directory. Ubuntu systems don't have SELinux enabled by default, so this step is not required there.

**Verify the fix:**
```bash
ls -lZ ./stk-assets/ | head -5
# Should show: system_u:object_r:container_file_t:s0
```

**Troubleshooting:**
- If you see `Permission denied` errors during Docker build, the SELinux context is wrong
- Always run the `chcon` command after downloading assets
- If context reverts, download with `svn co` may override it - reapply `chcon` if needed

### Linux Network Configuration

For local network server discovery on Linux systems, ensure:
1. `wan-server` is set to `false` in `server_config.xml` for LAN play
2. Firewall allows UDP traffic on ports 2757 and 2759:
   ```bash
   sudo firewall-cmd --permanent --add-port=2757/udp
   sudo firewall-cmd --permanent --add-port=2759/udp
   sudo firewall-cmd --reload
   ```

## Advanced Server Features

This enhanced version includes several advanced features not found in the basic STK server:

### SQLite Database Integration

**Enhanced**: This setup includes automatic database initialization with `init.sql` schema.

#### Database Setup (Automatic)

The database is **automatically initialized on the first startup**. No manual setup required!

**How it works:**
1. The `start.sh` entrypoint script checks if `/stk/stkservers.db` exists and is empty
2. If needed, it executes `sqlite3 /stk/stkservers.db < /stk/init.sql`
3. The `init.sql` file creates all required tables with proper schema
4. Database file is persisted on the host at `./stk/stkservers.db` for backups and management

**Tables created automatically:**
1. **`ip_ban`** - IPv4-based ban list with expiration support
2. **`ipv6_ban`** - IPv6-based ban list with expiration support
3. **`online_id_ban`** - Online ID-based ban list for account bans
4. **`player_reports`** - Player report system for moderation

**First startup output:**
```
Initializing STK server database...
Database initialized successfully.
```

On subsequent startups, the script detects the existing database and skips initialization:
```
Database already exists, skipping initialization.
```

#### Database Schema

The `init.sql` file contains:

```sql
-- IPv4 ban list
CREATE TABLE IF NOT EXISTS ip_ban (
    ip_start INTEGER UNSIGNED NOT NULL UNIQUE,
    ip_end INTEGER UNSIGNED NOT NULL UNIQUE,
    starting_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expired_days REAL NULL DEFAULT NULL,
    reason TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    trigger_count INTEGER UNSIGNED NOT NULL DEFAULT 0,
    last_trigger TIMESTAMP NULL DEFAULT NULL
);

-- IPv6 ban list
CREATE TABLE IF NOT EXISTS ipv6_ban (
    ipv6_cidr TEXT NOT NULL UNIQUE,
    starting_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expired_days REAL NULL DEFAULT NULL,
    reason TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    trigger_count INTEGER UNSIGNED NOT NULL DEFAULT 0,
    last_trigger TIMESTAMP NULL DEFAULT NULL
);

-- Online ID ban list
CREATE TABLE IF NOT EXISTS online_id_ban (
    online_id INTEGER UNSIGNED NOT NULL UNIQUE,
    starting_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expired_days REAL NULL DEFAULT NULL,
    reason TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    trigger_count INTEGER UNSIGNED NOT NULL DEFAULT 0,
    last_trigger TIMESTAMP NULL DEFAULT NULL
);

-- Player reports
CREATE TABLE IF NOT EXISTS player_reports (
    server_uid TEXT NOT NULL,
    reporter_ip INTEGER UNSIGNED NOT NULL,
    reporter_ipv6 TEXT NOT NULL DEFAULT '',
    reporter_online_id INTEGER UNSIGNED NOT NULL,
    reporter_username TEXT NOT NULL,
    reported_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    info TEXT NOT NULL,
    reporting_ip INTEGER UNSIGNED NOT NULL,
    reporting_ipv6 TEXT NOT NULL DEFAULT '',
    reporting_online_id INTEGER UNSIGNED NOT NULL,
    reporting_username TEXT NOT NULL
);
```

#### Manual Database Management

To access or manage the database directly:

```bash
# Connect to the database
sqlite3 ./stk/stkservers.db

# Example queries:
# List all tables
.tables

# View ban list
SELECT * FROM ip_ban;

# Add an IPv4 ban
INSERT INTO ip_ban (ip_start, ip_end, reason)
VALUES (3232235777, 3232235777, 'Player banned for griefing');

# Exit sqlite3
.exit
```

#### Enabling Database Management

The database tables are created automatically, but SQL management is **disabled by default**. To enable it in your server, update `server_config.xml`:

```xml
<!-- Use sql database for handling server stats and maintenance -->
<sql-management value="true" />

<!-- Database filename for sqlite to use -->
<database-file value="stkservers.db" />

<!-- Ban tables (empty to disable) -->
<ip-ban-table value="ip_ban" />
<ipv6-ban-table value="ipv6_ban" />
<online-id-ban-table value="online_id_ban" />

<!-- Player reports table (empty to disable) -->
<player-reports-table value="player_reports" />
```

Then restart the server:
```bash
docker compose restart
```

**Current status**: The database is pre-created and ready to use. Once you enable `sql-management`, the server will automatically start using the ban and player report tables.

#### About init.sql

The `init.sql` file contains the database schema and is located in the project root.

**How it works:**
- On first startup, `start.sh` checks if the database is empty
- If empty, it executes: `sqlite3 /stk/stkservers.db < /stk/init.sql`
- The file is copied into the Docker image during build
- Subsequent startups skip this step (database already initialized)

**File contents** (`./init.sql`):
```sql
CREATE TABLE IF NOT EXISTS ip_ban (...)
CREATE TABLE IF NOT EXISTS ipv6_ban (...)
CREATE TABLE IF NOT EXISTS online_id_ban (...)
CREATE TABLE IF NOT EXISTS player_reports (...)
```

#### Customizing the Database Schema

To modify the database schema or add custom tables:

1. **Before first startup** - Edit `./init.sql` before running `docker compose up -d`:
   ```bash
   nano init.sql
   # Add your custom tables
   docker compose up -d
   ```

2. **After database exists** - Add tables manually:
   ```bash
   # Create a file with your new table definition
   cat > custom_tables.sql << 'EOF'
   CREATE TABLE IF NOT EXISTS custom_stats (
       player_id INTEGER NOT NULL PRIMARY KEY,
       races_completed INTEGER DEFAULT 0,
       total_wins INTEGER DEFAULT 0
   );
   EOF

   # Load it into the database
   docker compose exec stk-server sqlite3 /stk/stkservers.db < custom_tables.sql
   ```

3. **Backup before major changes**:
   ```bash
   cp stk/stkservers.db stk/stkservers.db.backup
   ```

#### Database Features
- **Player statistics**: Automatic tracking of player connections, playtime, and performance
- **Ban system**: IP-based and Online ID-based banning with expiration support
- **Player reports**: Built-in player reporting system for moderation
- **Geolocation**: IP geolocation for player tracking (requires additional setup)

### Server Configuration Highlights
- **Supports up to 16 players**: Configurable in `server_config.xml` (default: 16, recommended: 8 for optimal performance)
- **Multiple game modes**: Normal race, time trial, soccer, free-for-all, capture the flag
- **AI kart management**: Automatic AI kart scaling based on player count (`ai-handling="true"`)
- **Live spectating**: Players can join/spectate games in progress (`live-spectate="true"`)
- **Advanced networking**: IPv6 support, high ping workarounds, STUN for NAT traversal
- **Enhanced difficulty**: Set to SuperTux difficulty (3) - the most challenging level
- **Resource limits**: Configurable CPU/memory limits to prevent host system overload

### Volume Mounts Explained

The docker-compose.yml includes these persistent volume mounts:

| Mount | Purpose | Host Path | Container Path |
|-------|---------|-----------|-----------------|
| Config | Server settings | `./server_config.xml` | `/stk/server_config.xml` |
| Game Data | Addons, config, cache | `./stk/supertuxkart` | `/stk/supertuxkart` |
| Database | SQLite database | `./stk/stkservers.db` | `/stk/stkservers.db` |
| MOTD | Message of the day | `./motd.txt` | `/stk/motd.txt` |

**Key points:**
- `./stk/stkservers.db` is created automatically and initialized with schema on first run
- `./stk/supertuxkart/` stores game configs, addons, and cache
- All files are persisted on the host for backup and management
- Database is automatically backed up when you copy the `stk/` directory

### Building the Image

To build the Docker image locally:
```bash
# Basic build
docker build -t stk-server .

# Build with specific STK version and metadata
docker build -t stk-server \
  --build-arg STK_VERSION=1.4 \
  --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
  --build-arg VCS_REF=$(git rev-parse --short HEAD) \
  .

# Build with caching for faster rebuilds
DOCKER_BUILDKIT=1 docker build -t stk-server .
```

The optimized build process:
1. **Build stage**: Compiles STK from source following official build guide
2. **Dependencies**: Uses exact package versions from STK documentation
3. **Runtime stage**: Minimal Debian slim with only required libraries
4. **Security**: Runs as non-root user `stk`
5. **Caching**: Build cache support for faster rebuilds
6. **Size optimization**: Multi-stage build removes build dependencies

## Troubleshooting

### Server not appearing in local network list

**Issue**: Server is running but doesn't appear in the in-game server browser

**Solution**: Ensure `wan-server` is set to `false` in `server_config.xml`:
```xml
<wan-server value="false" />
```

Then restart the container:
```bash
docker compose restart
```

### SELinux Permission Denied (Fedora/RHEL)

**Issue**: `Permission denied` errors when Docker tries to access `stk-assets`

**Solution**: Set correct SELinux context:
```bash
chcon -R system_u:object_r:container_file_t:s0 ./stk-assets/
```

Verify with:
```bash
ls -lZ ./stk-assets/ | head -1
```

### Configuration changes not taking effect

**Issue**: Modified `server_config.xml` but server still using old config

**Solution**: The config file is mounted as a volume, so changes should take effect on restart:
```bash
# For a simple restart (should work)
docker compose restart

# If that doesn't work, do a full rebuild
docker compose build && docker compose up -d
```

### Database file permission issues

**Issue**: `Error: unable to open database` or SQLite errors

**Solution**: Ensure database file has read-write permissions:
```bash
chmod 666 ./stk/stkservers.db
```

Or verify the volume mount has `:rw` flag in `docker-compose.yml`:
```yaml
volumes:
  - ./stk/stkservers.db:/stk/stkservers.db:rw
```

### Firewall blocking server discovery

**Issue**: Ports 2757/2759 are open but server still not visible

**Solution**: On Fedora with firewall enabled, open the ports:
```bash
sudo firewall-cmd --permanent --add-port=2757/udp
sudo firewall-cmd --permanent --add-port=2759/udp
sudo firewall-cmd --reload
```

Verify ports are listening:
```bash
ss -ulpn | grep -E "2757|2759"
```

### Docker vs Podman

**Note**: If using Podman instead of Docker, use these commands:
```bash
podman-compose up -d
podman-compose logs -f
podman-compose restart
```

Ensure you have `podman-compose` installed:
```bash
pip install podman-compose
```

### Database Backup

The database file is stored on your host at `./stk/stkservers.db`. To backup:

```bash
# Create a timestamped backup
cp stk/stkservers.db stk/stkservers.db.$(date +%Y%m%d_%H%M%S).backup

# Restore from backup
cp stk/stkservers.db.20251110_120000.backup stk/stkservers.db
docker compose restart
```

**Important**: Always backup before enabling SQL management features or modifying the server configuration.
