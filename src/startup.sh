#!/bin/bash

# List of server ports
SERVER_PORTS=(5501 5502 5503 5504 5505)

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

for port in "${SERVER_PORTS[@]}"
do
    echo "Starting server on port $port..."
    # Start each server in the background
    # Ensure the server.py file is in the correct location or adjust the path
    python3 server.py --port $port &
done

# Allow servers to start before the client interacts
sleep 5

# Notify that the servers are running
echo "Server instances started successfully."

echo "To start the client, run 'python3 client.py' manually."
