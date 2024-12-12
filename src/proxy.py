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

    def replicate_to_neighbors(self, message, primary_port):
        """Replicate data to neighbor servers."""
        neighbors = self.hash_ring.get_neighbors(message)
        responses = []
        # First send to primary
        try:
            primary_socket = self.worker_sockets[primary_port]
            primary_socket.send_string(message)
            response = primary_socket.recv_string()
            responses.append(json.loads(response))
        except zmq.error.Again:
            print(f"Primary server {primary_port} failed during replication")
            return None

        # Then replicate to neighbors
        for neighbor_port in neighbors:
            try:
                neighbor_socket = self.worker_sockets[neighbor_port]
                neighbor_socket.send_string(message)
                response = neighbor_socket.recv_string()
                responses.append(json.loads(response))
                print(f"Successfully replicated to neighbor {neighbor_port}")
            except zmq.error.Again:
                print(f"Failed to replicate to neighbor {neighbor_port}")
                continue
                
        print(responses)
        return responses[0] if responses else None

    def handle_worker_failure(self, primary_port, message):
        """Handle worker failure by trying backup servers."""
        neighbors = self.hash_ring.get_neighbors(message)
        for backup_port in neighbors:
            try:
                backup_socket = self.worker_sockets[backup_port]
                backup_socket.send_string(message)
                response = backup_socket.recv_string()
                print(f"Successfully failed over to backup server {backup_port}")
                
                self.sync_after_failover(message, backup_port)
                return response
            except zmq.error.Again:
                continue
        return json.dumps({"success": False, "error": "All servers unavailable"})
    
    def sync_after_failover(self, message, successful_port):
        """Sync data to other available servers after a failover."""
        try:
            socket = self.worker_sockets[successful_port]
            sync_message = json.dumps({"action": "get_state"})
            socket.send_string(sync_message)
            state = socket.recv_string()

            for port in self.worker_ports:
                if port != successful_port:
                    try:
                        sync_socket = self.worker_sockets[port]
                        sync_socket.send_string(json.dumps({
                            "action": "sync_state",
                            "data": json.loads(state)
                        }))
                        sync_socket.recv_string()  
                        print(f"Successfully synced state to server {port}")
                    except zmq.error.Again:
                        print(f"Failed to sync state to server {port}")
        except Exception as e:
            print(f"Error during post-failover sync: {e}")
    

    def start(self):
        """Modified start method to use list ID-based routing."""
        server = self.context.socket(zmq.REP)
        server.bind(f"tcp://*:{self.port}")
        print(f"Proxy Server running on port {self.port}")
        
        self.initialize_worker_sockets()
        listt = list()

        
        #health_check_thread = threading.Thread(target=self.check_server_health, daemon=True)
        #health_check_thread.start()
        while True:
            try:
                message = server.recv_string()

                # Parse the incoming message
                parsed_message = json.loads(message)
                action = parsed_message.get("action", "")
                data = parsed_message.get("data", {})

                if action == "syncLists" and isinstance(data, dict):
                    primary_ports = {}  # To map list IDs to their primary servers
                    for list_id, list_data in data.items():
                        primary_port = self.hash_ring.get_server(list_id)
                        primary_ports[list_id] = primary_port

                        # Replicate each list to its neighbors
                        response_data = self.replicate_to_neighbors(
                            message,
                            primary_port
                        )

                        listt.append({list_id: list_data})                     

                        # Log the response or handle failures
                        if response_data:
                            print(f"Successfully handled replication for list {list_id}")
                        else:
                            print(f"Failed to replicate list {list_id}")

                    lists_dict = {}
                    for d in listt:
                        lists_dict.update(d) 

                    response = {
                        "success": True,
                        "lists": lists_dict  
                    }
                    
                    # Send the mapping of list IDs to primary ports back as the response
                    print("\n\n\ndoing rn set thing, :DMD NDS  DS SN: ", response)
                    server.send_string(json.dumps(response))
                    listt = list()
                else:
                    # Handle other actions or invalid messages
                    response = {"success": False, "error": "Invalid action or data format"}
                    server.send_string(json.dumps(response))

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
                    socket.send_string(json.dumps({"action": "health_check"}))
                    socket.recv_string()
                except zmq.error.Again:
                    print(f"Server {port} appears to be down, removing from ring...")
                    self.hash_ring.remove_server(port)
                    del self.worker_sockets[port]
                    self.worker_ports.remove(port)
                    self.sync_after_server_removal(port)

    def sync_after_server_removal(self, failed_port):
        """Ensure data is properly redistributed after a server fails."""
        try:
            neighbors = self.hash_ring.get_neighbors(failed_port)
            if not neighbors:
                return

            for neighbor_port in neighbors:
                try:
                    socket = self.worker_sockets[neighbor_port]
                    socket.send_string(json.dumps({"action": "get_state"}))
                    state = socket.recv_string()
                    
                    state_data = json.loads(state)
                    self.redistribute_data(state_data, neighbor_port)
                    break
                except zmq.error.Again:
                    continue
        except Exception as e:
            print(f"Error during post-removal sync: {e}")

    def redistribute_data(self, state_data, source_port):
        """Redistribute data to available servers."""
        for port in self.worker_ports:
            if port != source_port:
                try:
                    socket = self.worker_sockets[port]
                    socket.send_string(json.dumps({
                        "action": "sync_state",
                        "data": state_data
                    }))
                    socket.recv_string()
                    print(f"Successfully redistributed data to server {port}")
                except zmq.error.Again:
                    print(f"Failed to redistribute data to server {port}")


def main():
    worker_ports = ['9001', '9002', '9003', '9004', '9005']
    proxy_port = 9000
    proxy_server = ProxyServer(proxy_port, worker_ports)
    
    worker_processes = []
    for port in worker_ports:
        worker_server = Server(port)
        worker_process = threading.Thread(target=worker_server.run)
        worker_process.start()
        worker_processes.append(worker_process)

    proxy_server.start()


if __name__ == "__main__":
    main()
