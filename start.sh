#!/bin/bash
set -e

cleanup() {
    echo "Received termination signal, shutting down gracefully..."
    if [[ -n "$SERVER_PID" ]]; then
        kill -TERM "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
    fi
    exit 0
}

trap cleanup SIGTERM SIGINT
if [[ -n ${USERNAME} ]] && [[ -n ${PASSWORD} ]]
then
    echo "Initializing user account..."
    if ! supertuxkart --init-user --login=${USERNAME} --password=${PASSWORD}; then
        echo "Warning: Failed to initialize user account. Server may not work properly for WAN connections."
    fi
fi

# Initialize database on first run
if [[ ! -f /stk/stkservers.db ]] || [[ ! -s /stk/stkservers.db ]]; then
    echo "Initializing STK server database..."
    # Create empty database file (may fail due to volume permissions, so try with sqlite directly)
    if sqlite3 /stk/stkservers.db < /stk/init.sql 2>/dev/null; then
        echo "Database initialized successfully."
    else
        # If database file exists but is empty/read-only, try to initialize it anyway
        echo "Warning: Could not initialize database, server may not work properly with SQL management enabled."
    fi
else
    echo "Database already exists, skipping initialization."
fi

echo "Starting SuperTuxKart server..."
supertuxkart --server-config=server_config.xml &
SERVER_PID=$!

sleep 5
if [[ -n ${AI_KARTS} ]]
then
    if command -v xmlstarlet >/dev/null 2>&1; then
        SERVER_PASSWORD=$(xmlstarlet sel -t -v "//private-server-password/@value" server_config.xml 2>/dev/null || echo "")
    else
        SERVER_PASSWORD=$(grep -o 'private-server-password[[:space:]]*value="[^"]*"' server_config.xml | sed 's/.*value="\([^"]*\)".*/\1/' 2>/dev/null || echo "")
    fi
    
    SERVER_PORT=$(grep -o 'server-port[[:space:]]*value="[^"]*"' server_config.xml | sed 's/.*value="\([^"]*\)".*/\1/' 2>/dev/null || echo "2759")
    if [[ "$SERVER_PORT" == "0" ]]; then
        SERVER_PORT="2759"
    fi
    
    echo "Connecting AI karts to server on port $SERVER_PORT..."
    if [[ -n "$SERVER_PASSWORD" ]]; then
        supertuxkart --connect-now=127.0.0.1:$SERVER_PORT --server-password="$SERVER_PASSWORD" --network-ai=${AI_KARTS} &
    else
        supertuxkart --connect-now=127.0.0.1:$SERVER_PORT --network-ai=${AI_KARTS} &
    fi
fi
wait $SERVER_PID || echo "Server exited with status $?"
