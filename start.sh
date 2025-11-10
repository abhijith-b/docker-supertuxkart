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

if [[ ! -f /stk/stkservers.db ]] || [[ ! -s /stk/stkservers.db ]]; then
    echo "Initializing STK server database..."
    if sqlite3 /stk/stkservers.db < /stk/init.sql; then
        echo "Database initialized successfully."
    else
        echo "Warning: Failed to initialize database. Server may not work properly with SQL management enabled."
    fi
else
    echo "Database already exists, skipping initialization."
fi

LOG_LEVEL=${LOG_LEVEL:-info}
echo "Starting SuperTuxKart server with log level: $LOG_LEVEL"
supertuxkart --server-config=server_config.xml --log=$LOG_LEVEL &
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
