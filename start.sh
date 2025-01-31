#!/bin/bash
set -em

# Log in with username and password if provided
if [[ -n ${USERNAME} ]] && [[ -n ${PASSWORD} ]]
then
    supertuxkart --init-user --login=${USERNAME} --password=${PASSWORD}
fi

# Start stk server with more verbose output
supertuxkart --server-config=server_config.xml --log=debug &
SERVER_PID=$!

# Add ai kart if necessary
if [[ -n ${AI_KARTS} ]]
then
    SERVER_PASSWORD=`cat server_config.xml | grep private-server-password | awk -F '"' '{print $2}'`
    supertuxkart --connect-now=127.0.0.1:2759 --server-password=$SERVER_PASSWORD --network-ai=${AI_KARTS} &
fi

# Wait for the server process with error checking
wait $SERVER_PID || echo "Server exited with status $?"
