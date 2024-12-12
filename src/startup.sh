#!/bin/bash

# List of server ports
SERVER_PORTS=(9001 9002 9003 9004 9005)

# Stop any existing server processes
for port in "${SERVER_PORTS[@]}"; do
    pid=$(lsof -t -i :$port)
    if [ ! -z "$pid" ]; then
        echo "Stopping existing server on port $port (PID: $pid)..."
        kill $pid
    fi
done

# Wait for the processes to terminate
sleep 2

# Start the 5 server instances
echo "Starting server instances..."

# Use exec to replace the shell process with proxy.py
exec python3 proxy.py

# Notify user
echo "Server instances started successfully."
echo "To start the client, run 'python3 client.py' manually."