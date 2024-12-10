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
    python3 server.py --port $port --all_ports "${SERVER_PORTS[@]}" &
done

echo "All servers started successfully!"
