import zmq
import threading
import json
from HashRing import HashRing
from server import Server  # Importing the worker server class


class ProxyServer:
    def __init__(self, port, worker_ports):
        self.port = port
        self.worker_ports = worker_ports
        self.hash_ring = HashRing(worker_ports)

    def start(self):
        """Start the proxy server to route requests to the appropriate worker."""
        context = zmq.Context()
        server = context.socket(zmq.REP)
        server.bind(f"tcp://*:{self.port}")
        print(f"Proxy Server running on port {self.port}")

        while True:
            # Receive a request from the client (proxy communicates directly with the client)
            msg = server.recv_string()

            # Hash the message to find the appropriate worker
            target_worker = self.hash_ring.get_server(msg)

            # Connect to the selected worker
            worker_socket = context.socket(zmq.REQ)
            worker_socket.connect(f"tcp://localhost:{target_worker}")

            # Send the task to the worker
            worker_socket.send_string(msg)

            # Wait for the worker's response
            result = worker_socket.recv_string()

            # Since the worker will send the updated state, forward it to the client
            server.send_string(result)


def main():
    # Initialize the worker ports and create the hash ring for routing
    worker_ports = ['9001']
    proxy_port = 9000

    # Start the proxy server
    proxy_server = ProxyServer(proxy_port, worker_ports)
    proxy_server_process = threading.Thread(target=proxy_server.start)
    proxy_server_process.start()

    # Start worker servers (workers are instances of the Server class)
    worker_processes = []
    for port in worker_ports:
        worker_server = Server(port)
        worker_process = threading.Thread(target=worker_server.run)
        worker_process.start()
        worker_processes.append(worker_process)

    # Join all worker threads (this keeps the main thread alive)
    for worker in worker_processes:
        worker.join()


if __name__ == "__main__":
    main()
