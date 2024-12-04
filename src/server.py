import zmq
import threading
import json
from crdt.ShoppingList import ShoppingList
import os
import time
import sys

CONFIG = {
    "update_interval": 10,  # seconds
    "neighbor_update_interval": 10,  # seconds
    "zmq_port": 9000,  # Base port for ZeroMQ communication
    "json_folder": "./data/",  # Folder for storing JSON files
}

class Server:
    def __init__(self, port):
        self.port = port  # Dynamic port passed by client
        self.shopping_list = ShoppingList(owner=port)
        self.json_path = f"{CONFIG['json_folder']}{port}.json"
        self.lock = threading.Lock()
        self.context = zmq.Context()
        self.sock = self.context.socket(zmq.REP)  # REP socket for request-reply pattern
        self.sock.bind(f"tcp://*:{self.port}")  # Dynamically bind to the client-specified port
        self._load_data()

    def _load_data(self):
        """Load the shopping list state from a JSON file."""
        if os.path.exists(self.json_path):
            with open(self.json_path, "r") as file:
                data = json.load(file)
                self.shopping_list.merge(data)  # Merge the saved state into the current ShoppingList
        else:
            # Ensure the folder exists
            os.makedirs(CONFIG['json_folder'], exist_ok=True)

    def _save_data(self):
        """Save the shopping list state to a JSON file."""
        with open(self.json_path, "w") as file:
            json.dump(self.shopping_list.info(), file)

    def handle_request(self, request):
        """Handle incoming requests from clients."""
        request = json.loads(request)
        action = request.get("action")
        response = {"status": "ok"}

        try:
            if request.get("message") == "Hello":
                response["message"] = "Hello World"
            if action == "create_list":
                name = request["name"]
                list_id = self.shopping_list.create_list(name)
                response["list_id"] = list_id

            elif action == "delete_list":
                list_id = request["list_id"]
                self.shopping_list.delete_list(list_id)

            elif action == "create_item":
                list_id = request["list_id"]
                item_name = request["item_name"]
                quantity = request.get("quantity", 1)
                self.shopping_list.create_item(list_id, item_name, quantity)

            elif action == "delete_item":
                list_id = request["list_id"]
                item_name = request["item_name"]
                self.shopping_list.delete_item(list_id, item_name)

            elif action == "update_quantity":
                list_id = request["list_id"]
                item_name = request["item_name"]
                increment = request.get("increment", 0)
                decrement = request.get("decrement", 0)
                self.shopping_list.update_quantity(list_id, item_name, increment, decrement)

            elif action == "get_list":
                list_id = request["list_id"]
                response["list"] = self.shopping_list.get_list(list_id)

            elif action == "get_all_lists":
                response["lists"] = self.shopping_list.info()

            elif action == "merge":
                remote_data = request["data"]
                self.shopping_list.merge(remote_data)

        except Exception as e:
            response = {"status": "error", "message": str(e)}

        return json.dumps(response)

    def listen(self):
        """Start listening for incoming ZeroMQ requests."""
        print(f"Server {self.port} started and listening on port {self.port}")
        while True:
            request = self.sock.recv().decode("utf-8")
            with self.lock:
                response = self.handle_request(request)
                self._save_data()  # Save the state after handling the request
            self.sock.send(response.encode("utf-8"))

    def run(self):
        """Start the server."""
        listener_thread = threading.Thread(target=self.listen)
        listener_thread.start()
        listener_thread.join()


# Run the server
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Please provide a port number to bind the server.")
        sys.exit(1)

    port = int(sys.argv[1])  # The port should be passed from the client
    server = Server(port)
    server.run()
