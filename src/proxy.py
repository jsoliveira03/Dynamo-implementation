import zmq
import threading
import json
from HashRing import HashRing
from server import Server  # Importing the worker server class
import time


class ProxyServer:
    def __init__(self, port, worker_ports):
        self.port = port
        self.worker_ports = worker_ports
        self.hash_ring = HashRing(worker_ports, replicas=10)
        self.worker_sockets = {}
        self.context = zmq.Context()

    def initialize_worker_sockets(self):
        """Initialize connections to all worker servers."""
        for port in self.worker_ports:
            socket = self.context.socket(zmq.REQ)
            socket.connect(f"tcp://localhost:{port}")
            self.worker_sockets[port] = socket

    def handle_worker_failure(self, primary_port, message):
        """Handle worker failure by trying backup servers."""
        neighbors = self.hash_ring.get_neighbors(message)
        for backup_port in neighbors:
            try:
                backup_socket = self.worker_sockets[backup_port]
                backup_socket.send_string(message)
                response = backup_socket.recv_string()
                print(f"Successfully failed over to backup server {backup_port}")
                return response
            except zmq.error.Again:
                continue
        return json.dumps({"success": False, "error": "All servers unavailable"})
    

    def start(self):
        """Start the proxy server to route requests to the appropriate worker."""
        server = self.context.socket(zmq.REP)
        server.bind(f"tcp://*:{self.port}")
        print(f"Proxy Server running on port {self.port}")
        
        # Initialize connections to all workers
        self.initialize_worker_sockets()
        
        # Start health check thread
        health_check_thread = threading.Thread(target=self.check_server_health, daemon=True)
        health_check_thread.start()

        while True:
            try:
                # Receive request from client
                message = server.recv_string()
                
                # Get primary server for this message
                primary_port = self.hash_ring.get_server(message)
                
                try:
                    # Try primary server
                    worker_socket = self.worker_sockets[primary_port]
                    worker_socket.send_string(message)
                    response = worker_socket.recv_string()
                except zmq.error.Again:
                    # If primary fails, try backup servers
                    print(f"Primary server {primary_port} failed, trying backups...")
                    response = self.handle_worker_failure(primary_port, message)
                
                # Send response back to client
                server.send_string(response)
                
                # Update load statistics
                print("\nCurrent server status:")
                print(self.hash_ring.get_server_status())
                
            except Exception as e:
                error_response = json.dumps({"success": False, "error": str(e)})
                server.send_string(error_response)

    def check_server_health(self, check_interval=10):
        """Periodically check server health and rebalance if needed."""
        while True:
            time.sleep(check_interval)
            for port in list(self.worker_ports):
                try:
                    socket = self.worker_sockets[port]
                    # Send health check message
                    socket.send_string(json.dumps({"action": "health_check"}))
                    socket.recv_string()
                except zmq.error.Again:
                    print(f"Server {port} appears to be down, removing from ring...")
                    self.hash_ring.remove_server(port)
                    del self.worker_sockets[port]
                    self.worker_ports.remove(port)


def main():
    # Initialize with all 5 worker ports
    worker_ports = ['9001', '9002', '9003', '9004', '9005']
    proxy_port = 9000

    # Start the proxy server
    proxy_server = ProxyServer(proxy_port, worker_ports)
    
    # Start worker servers
    worker_processes = []
    for port in worker_ports:
        worker_server = Server(port)
        worker_process = threading.Thread(target=worker_server.run)
        worker_process.start()
        worker_processes.append(worker_process)

    # Start proxy server (this will block)
    proxy_server.start()


if __name__ == "__main__":
    main()
