#!/bin/bash
set -e

# Function to handle graceful shutdown
cleanup() {
    echo "Received termination signal, shutting down gracefully..."
    if [[ -n "$SERVER_PID" ]]; then
        kill -TERM "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
    fi
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT

# Log in with username and password if provided
if [[ -n ${USERNAME} ]] && [[ -n ${PASSWORD} ]]
then
    echo "Initializing user account..."
    if ! supertuxkart --init-user --login=${USERNAME} --password=${PASSWORD}; then
        echo "Warning: Failed to initialize user account. Server may not work properly for WAN connections."
    fi
fi

# Start stk server - use info level logging instead of debug for production
LOG_LEVEL=${LOG_LEVEL:-info}
echo "Starting SuperTuxKart server with log level: $LOG_LEVEL"
supertuxkart --server-config=server_config.xml --log=$LOG_LEVEL &
SERVER_PID=$!

# Give server time to start up
sleep 5

# Add ai kart if necessary
if [[ -n ${AI_KARTS} ]]
then
    # Extract server password more robustly using xmlstarlet or fallback to grep
    if command -v xmlstarlet >/dev/null 2>&1; then
        SERVER_PASSWORD=$(xmlstarlet sel -t -v "//private-server-password/@value" server_config.xml 2>/dev/null || echo "")
    else
        # Fallback to more robust grep pattern
        SERVER_PASSWORD=$(grep -o 'private-server-password[[:space:]]*value="[^"]*"' server_config.xml | sed 's/.*value="\([^"]*\)".*/\1/' 2>/dev/null || echo "")
    fi
    
    # Get server port from config or use default
    SERVER_PORT=$(grep -o 'server-port[[:space:]]*value="[^"]*"' server_config.xml | sed 's/.*value="\([^"]*\)".*/\1/' 2>/dev/null || echo "2759")
    if [[ "$SERVER_PORT" == "0" ]]; then
        SERVER_PORT="2759"  # Default STK port when config specifies 0
    fi
    
    echo "Connecting AI karts to server on port $SERVER_PORT..."
    # Only add server password parameter if password is not empty
    if [[ -n "$SERVER_PASSWORD" ]]; then
        supertuxkart --connect-now=127.0.0.1:$SERVER_PORT --server-password="$SERVER_PASSWORD" --network-ai=${AI_KARTS} &
    else
        supertuxkart --connect-now=127.0.0.1:$SERVER_PORT --network-ai=${AI_KARTS} &
    fi
fi

# Wait for the server process with error checking
wait $SERVER_PID || echo "Server exited with status $?"
