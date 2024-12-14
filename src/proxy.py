import zmq
import threading
import json
from HashRing import HashRing
from server import Server 
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
        """Replicate data to neighbor servers using SyncLists action."""
        neighbors = self.hash_ring.get_neighbors(message)
        responses = []
        print("Primaryyyyyy")
        print(primary_port)
        try:
            primary_socket = self.worker_sockets[primary_port]
            primary_request = {
                "action": "syncLists",
                "data": json.loads(message)["data"]  
            }
            primary_socket.send_string(json.dumps(primary_request))
            response = primary_socket.recv_string()
            responses.append(json.loads(response))       
        except zmq.error.Again:
            print(f"Primary server {primary_port} failed during replication")
            return None

        for neighbor_port in neighbors:
            try:
                neighbor_socket = self.worker_sockets[neighbor_port]
                neighbor_request = {
                    "action": "syncLists",
                    "data": json.loads(message)["data"]  
                }
                neighbor_socket.send_string(json.dumps(neighbor_request))
                response = neighbor_socket.recv_string()
                responses.append(json.loads(response))
                print(f"Successfully replicated to neighbor {neighbor_port}")
            except zmq.error.Again:
                print(f"Failed to replicate to neighbor {neighbor_port}")
                continue
        
        return responses[0] if responses else None
    

    def start(self):
        """Modified start method to use list ID-based routing."""
        server = self.context.socket(zmq.REP)
        server.bind(f"tcp://*:{self.port}")
        print(f"Proxy Server running on port {self.port}")
        
        self.initialize_worker_sockets()
        listt = []

        while True:
            try:
                message = server.recv_string()

                parsed_message = json.loads(message)
                action = parsed_message.get("action", "")
                data = parsed_message.get("data", {})

                if action == "syncLists" and isinstance(data, dict):
                    primary_ports = {} 
                    for list_id, list_data in data.items():
                        primary_port = self.hash_ring.get_server(list_id)
                        primary_ports[list_id] = primary_port

                        response_data = self.replicate_to_neighbors(
                            message,
                            primary_port
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

                print("\nCurrent server status:")
                print(self.hash_ring.get_server_status())

            except Exception as e:
                error_response = json.dumps({"success": False, "error": str(e)})
                server.send_string(error_response)


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
