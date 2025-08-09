# Docker SuperTuxKart Server

This is a docker image for deploying a [SuperTuxKart](https://supertuxkart.net) server.

## What is SuperTuxKart?

SuperTuxKart (STK) is a free and open-source kart racing game, distributed under the terms of the GNU General Public License, version 3. It features mascots of various open-source projects. SuperTuxKart is cross-platform, running on Linux, macOS, Windows, and Android systems. Version 1.0 was officially released on April 20, 2019.

SuperTuxKart started as a fork of TuxKart, originally developed by Steve and Oliver Baker in 2000. When TuxKart's development ended around March 2004, a fork as SuperTuxKart was conducted by other developers in 2006. SuperTuxKart is under active development by the game's community.

> [wikipedia.org/wiki/SuperTuxKart](https://en.wikipedia.org/wiki/SuperTuxKart)

![logo](https://raw.githubusercontent.com/jwestp/docker-supertuxkart/master/supertuxkart-logo.png)

## How to use this image

The image exposes ports 2759/udp (server) and 2757/udp (server discovery). The server should be configured using your own server config file. The config file template can be found [here](https://github.com/jwestp/docker-supertuxkart/blob/master/server_config.xml). Modify it according to your needs and mount it at `/stk/server_config.xml`.

This enhanced version includes SQLite database support for advanced server management, addon support, and persistent data storage.

### Hosting a server in your local network

```
docker run --name my-stk-server \
           -d \
           -p 2757:2757/udp \
           -p 2759:2759/udp \
           -v $(pwd)/server_config.xml:/stk/server_config.xml \
           -v $(pwd)/stk:/stk/supertuxkart \
           stk-server:latest
```

### Hosting a server on the internet

For hosting a server on the internet (by setting `wan-server` to `true` in the config file) it is required to log in with your STK account. You can register a free account [here](https://online.supertuxkart.net/register.php). Pass your username and password to the container via environment variables.

```
docker run --name my-stk-server \
           -d \
           -p 2757:2757/udp \
           -p 2759:2759/udp \
           -v $(pwd)/server_config.xml:/stk/server_config.xml \
           -v $(pwd)/stk:/stk/supertuxkart \
           -v $(pwd)/motd.txt:/stk/motd.txt \
           -e USERNAME=myusername \
           -e PASSWORD=mypassword \
           stk-server:latest
```

### Adding ai karts

You can add ai karts to your server by setting the environment variable `AI_KARTS` like shown in the following example:

```
docker run --name my-stk-server \
           -d \
           -p 2757:2757/udp \
           -p 2759:2759/udp \
           -v $(pwd)/server_config.xml:/stk/server_config.xml \
           -v $(pwd)/stk:/stk/supertuxkart \
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
2. **Configure volumes**: The setup includes persistent storage for:
   - `server_config.xml`: Server configuration
   - `stk/stkservers.db`: SQLite database for server management
   - `motd.txt`: Message of the day
   - `stk/addons/`: Downloaded addons (tracks, karts, arenas)
3. **Network settings**: IPv6 support is enabled by default

```yaml
services:
  stk-server:
    image: stk-server
    restart: unless-stopped
    volumes:
      - ./server_config.xml:/stk/server_config.xml
      - ./stk/stkservers.db:/stk/stkservers.db
      - ./motd.txt:/stk/motd.txt
      - ./stk/addons/:/stk/supertuxkart/addons/
    environment:
      USERNAME: "your_stk_username"
      PASSWORD: "your_stk_password"
      #AI_KARTS: 1
    ports:
      - "2757:2757/udp"
      - "2759:2759/udp"
```

**Commands:**
- **Start server**: `docker-compose up -d`
- **View logs**: `docker-compose logs -f`
- **Stop server**: `docker-compose down`
- **Rebuild**: `docker-compose build`

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
   
   # Get help
   python3 addons.py --help
   ```

### Features

- **Multi-threaded downloads** with progress bars (up to 5 concurrent downloads)
- **Smart filtering** with multiple preset options:
  - **Default**: Tracks, arenas, and featured karts only (recommended for most users)
  - **All**: Every available addon including all karts (~5GB download)
  - **Tracks-only**: Only tracks and arenas, no karts
  - **High-rated**: Only addons with user rating ≥2.8 stars
  - **Recent**: Only addons updated within the last year
- **Automatic updates** for existing addons when newer revisions are available
- **Docker-aware** directory structure (`./stk/addons/`)
- **Resume capability** - interrupted downloads can be resumed safely
- **Skip duplicate downloads** - already downloaded files are automatically skipped
- **Safe cancellation** - Ctrl+C preserves completed installations

### Directory Structure

After running the addon script, your directory will look like:
```
stk/
├── addons/
│   ├── tracks/          # Downloaded track addons
│   ├── karts/           # Downloaded kart addons
│   └── addons.xml       # Addon database
└── stkservers.db        # Server database
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

## Advanced Server Features

This enhanced version includes several advanced features not found in the basic STK server:

### SQLite Database Integration

**Important**: This setup has `sql-management="true"` enabled, which requires manual database initialization.

#### Database Setup (Required)

1. **Create the database**:
   ```bash
   sqlite3 stk/stkservers.db
   ```

2. **Create required tables** (run these SQL commands in sqlite3):
   ```sql
   -- IPv4 ban list
   CREATE TABLE ip_ban (
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
   CREATE TABLE ipv6_ban (
       ipv6_cidr TEXT NOT NULL UNIQUE,
       starting_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
       expired_days REAL NULL DEFAULT NULL,
       reason TEXT NOT NULL DEFAULT '',
       description TEXT NOT NULL DEFAULT '',
       trigger_count INTEGER UNSIGNED NOT NULL DEFAULT 0,
       last_trigger TIMESTAMP NULL DEFAULT NULL
   );

   -- Online ID ban list
   CREATE TABLE online_id_ban (
       online_id INTEGER UNSIGNED NOT NULL UNIQUE,
       starting_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
       expired_days REAL NULL DEFAULT NULL,
       reason TEXT NOT NULL DEFAULT '',
       description TEXT NOT NULL DEFAULT '',
       trigger_count INTEGER UNSIGNED NOT NULL DEFAULT 0,
       last_trigger TIMESTAMP NULL DEFAULT NULL
   );

   -- Player reports
   CREATE TABLE player_reports (
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

3. **Exit sqlite3**: Type `.exit` to save and exit

#### Database Features
- **Player statistics**: Automatic tracking of player connections, playtime, and performance
- **Ban system**: IP-based and Online ID-based banning with expiration support
- **Player reports**: Built-in player reporting system for moderation
- **Geolocation**: IP geolocation for player tracking (requires additional setup)

### Server Configuration Highlights
- **High player count**: Supports up to 16 players (configurable, default 8 with performance warning)
- **Multiple game modes**: Normal race, time trial, soccer, free-for-all, capture the flag
- **AI kart management**: Automatic AI kart scaling based on player count (`ai-handling="true"`)
- **Live spectating**: Players can join/spectate games in progress (`live-spectate="true"`)
- **Advanced networking**: IPv6 support, high ping workarounds, STUN for NAT traversal
- **Enhanced difficulty**: Set to SuperTux difficulty (3) - the most challenging level

### Volume Mounts Explained
- `server_config.xml`: Server configuration file
- `stkservers.db`: SQLite database for persistent server data
- `motd.txt`: Custom message of the day displayed to players
- `stk/addons/`: Addon storage directory for tracks and karts

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
