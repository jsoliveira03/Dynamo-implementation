#!/bin/bash

SERVER_PORTS=(9001 9002 9003 9004 9005)

for port in "${SERVER_PORTS[@]}"; do
    pid=$(lsof -t -i :$port)
    if [ ! -z "$pid" ]; then
        echo "Stopping existing server on port $port (PID: $pid)..."
        kill $pid
    fi
done

sleep 2

echo "Starting server instances..."

exec python3 proxy.py

echo "Server instances started successfully."
echo "To start the client, run 'python3 client.py' manually."