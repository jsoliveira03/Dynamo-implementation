import zmq
import threading
import json
from HashRing import HashRing
from server import Server
import time


class ProxyServer:
    def __init__(self, port, worker_ports):
        self.port = port
        self.worker_ports = set(worker_ports)
        self.hash_ring = HashRing(worker_ports, replicas=10)
        self.worker_sockets = {}
        self.context = zmq.Context()
        self.running = True

    def initialize_worker_sockets(self):
        """Initialize connections to all worker servers with timeout."""
        for port in self.worker_ports:
            socket = self.context.socket(zmq.REQ)
            socket.setsockopt(zmq.RCVTIMEO, 5000)
            socket.setsockopt(zmq.SNDTIMEO, 5000)
            socket.connect(f"tcp://localhost:{port}")
            self.worker_sockets[port] = socket

    def try_worker_request(self, port, message, retries=2):
        """Attempt to send a request to a worker with retries."""
        for attempt in range(retries):
            try:
                socket = self.worker_sockets[port]
                socket.send_string(json.dumps(message))
                return json.loads(socket.recv_string())
            except (zmq.error.Again, zmq.error.ZMQError) as e:
                if attempt == retries - 1:
                    print(f"Server {port} is unresponsive after {retries} attempts")
                    self.handle_server_failure(port)
                    return None
                time.sleep(0.5)
        return None
    
    def handle_server_failure(self, failed_port):
        """Handle a server failure by removing it and redistributing data."""
        if failed_port in self.worker_ports:
            print(f"Removing failed server {failed_port}")
            self.worker_ports.remove(failed_port)
            self.hash_ring.remove_server(failed_port)
            if failed_port in self.worker_sockets:
                self.worker_sockets[failed_port].close()
                del self.worker_sockets[failed_port]
            
            if self.worker_ports:
                self.redistribute_after_failure()

    def redistribute_after_failure(self):
        """Redistribute data among remaining servers."""
        for port in self.worker_ports:
            response = self.try_worker_request(port, {"action": "get_state"})
            if response:
                for target_port in self.worker_ports:
                    if target_port != port:
                        self.try_worker_request(target_port, {
                            "action": "sync_state",
                            "data": response
                        })
                break

    def replicate_to_neighbors(self, message, primary_port):
        """Replicate data to neighbor servers with failure handling."""
        if primary_port not in self.worker_ports:
            return self.handle_primary_failure(message)
            
        parsed_message = json.loads(message)
        neighbors = self.hash_ring.get_neighbors(message)
        responses = []

        primary_response = self.try_worker_request(primary_port, {
            "action": "syncLists",
            "data": parsed_message["data"]
        })
        
        if primary_response:
            responses.append(primary_response)
            for neighbor_port in neighbors:
                if neighbor_port in self.worker_ports:
                    neighbor_response = self.try_worker_request(neighbor_port, {
                        "action": "syncLists",
                        "data": parsed_message["data"]
                    })
                    if neighbor_response:
                        responses.append(neighbor_response)

        return responses[0] if responses else None
    
    def handle_primary_failure(self, message):
        """Handle primary server failure by promoting a neighbor."""
        parsed_message = json.loads(message)
        for list_id in parsed_message.get("data", {}).keys():
            new_primary = self.hash_ring.get_server(list_id)
            if new_primary in self.worker_ports:
                return self.replicate_to_neighbors(message, new_primary)
        return None


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
        """Main server loop with improved error handling."""
        server = self.context.socket(zmq.REP)
        server.bind(f"tcp://*:{self.port}")
        print(f"Proxy Server running on port {self.port}")
        
        self.initialize_worker_sockets()
        
        health_check_thread = threading.Thread(target=self.check_server_health)
        health_check_thread.daemon = True
        health_check_thread.start()

        listt = []

        while self.running:
            try:
                message = server.recv_string()

                parsed_message = json.loads(message)
                action = parsed_message.get("action", "")
                data = parsed_message.get("data", {})
                response = {"success": False, "error": "Invalid action"}

                if action == "syncLists" and isinstance(data, dict):
                    primary_ports = {}
                    for list_id, list_data in data.items():
                        primary_port = self.hash_ring.get_server(list_id)
                        primary_ports[list_id] = primary_port

                        response_data = self.replicate_to_neighbors(
                            message, primary_port
                        )

                        processed_lists = response_data["lists"]
                        print("List data")
                        print(list_data)
                        for resp_list_id, resp_list_data in processed_lists.items():
                            if(list_id == resp_list_id):
                                listt.append({resp_list_id: resp_list_data})
                        
                        if response_data:
                            print(f"Successfully handled replication for list {list_id}")
                        else:
                            print(f"Failed to replicate list {list_id}")


                    lists_dict = {}
                    for d in listt:
                        lists_dict.update(d)

                    print("response dict")
                    print(lists_dict)
                    response = {
                        "success": True,
                        "lists": lists_dict
                    }
                    
                    server.send_string(json.dumps(response))
                    listt = []
                elif action == "getListById" and isinstance(data, dict):
                    list_id = data.get("list_id")
                    if list_id:
                        primary_port = self.hash_ring.get_server(list_id)
                        try:
                            primary_socket = self.worker_sockets[primary_port]
                            primary_request = {
                                "action": "getListById",
                                "data": {"list_id": list_id}
                            }
                            primary_socket.send_string(json.dumps(primary_request))
                            response = primary_socket.recv_string()
                            server_response = json.loads(response)

                            if server_response.get("success"):
                                server.send_string(json.dumps({
                                    "success": True,
                                    "list": server_response.get("list")
                                }))
                            else:
                                server.send_string(json.dumps({
                                    "success": False,
                                    "error": "Failed to fetch list from server"
                                }))
                        except zmq.error.Again:
                            server.send_string(json.dumps({
                                "success": False,
                                "error": f"Server {primary_port} is unavailable"
                            }))
                    else:
                        server.send_string(json.dumps({
                            "success": False,
                            "error": "List ID is missing"
                        }))

                else:
                    response = {"success": False, "error": "Invalid action or data format"}
                    server.send_string(json.dumps(response))


                server.send_string(json.dumps(response))

            except zmq.error.ZMQError as e:
                print(f"ZMQ Error in main loop: {e}")
                continue
            except Exception as e:
                print(f"Unexpected error in main loop: {e}")
                try:
                    server.send_string(json.dumps({
                        "success": False,
                        "error": str(e)
                    }))
                except:
                    pass
                continue

    def check_server_health(self, check_interval=5):
        """Periodic health check with improved error handling."""
        while self.running:
            time.sleep(check_interval)
            for port in list(self.worker_ports):
                try:
                    response = self.try_worker_request(port, {"action": "health_check"})
                    if not response:
                        self.handle_server_failure(port)
                except Exception as e:
                    print(f"Health check error for server {port}: {e}")
                    self.handle_server_failure(port)

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
        worker_process.daemon = True
        worker_process.start()
        worker_processes.append(worker_process)

    try:
        proxy_server.start()
    except KeyboardInterrupt:
        print("Shutting down proxy server...")
        proxy_server.running = False


if __name__ == "__main__":
    main()
