import argparse
import zmq
import json
import os
import threading
from crdt.ShoppingList import ShoppingList

CONFIG = {
    "json_folder": "./data/",
    "update_interval": 15,  # Periodic update interval in seconds
}

class Server:
    def __init__(self, port):
        self.port = port
        self.shopping_list = ShoppingList(owner=port)  # Initialize ShoppingList
        # Set a unique JSON file path based on the server's port number
        self.json_path = f"{CONFIG['json_folder']}lists_{self.port}.json"
        self.lock = threading.Lock()
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{self.port}")
        self._load_data()

    def _load_data(self):
        """Load data from local storage and merge it into the shopping list."""
        if os.path.exists(self.json_path):
            with open(self.json_path, "r") as file:
                data = json.load(file)
                self.shopping_list.merge(data)  # Merge data into the shopping list
        else:
            os.makedirs(CONFIG['json_folder'], exist_ok=True)

    def _save_data(self):
        """Save shopping list data to local storage if changes exist."""
        if self.shopping_list.changed():  # Only save if there are changes
            with open(self.json_path, "w") as file:
                json.dump(self.shopping_list.info(), file, indent=4)

    def handle_request(self, message):
        """
        Handle incoming client requests and perform appropriate actions.
        """
        try:
            request = json.loads(message)
            action = request.get("action")
            data = request.get("data", {})
            response = {"success": True}  # Default response structure

            if action == "syncLists":
                # Merge incoming client data into the server's state
                self.shopping_list.merge(data)  # Merge data into local shopping list
                
                # Save the merged state to the server's persistent storage
                self._save_data()
                
                # Respond with the updated server state
                response["lists"] = self.shopping_list.info()

            else:
                response = {"success": False, "error": "Invalid action requested"}

            return json.dumps(response)

        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})


    def run(self):
        """
        Start the server to listen for incoming client requests.
        """
        print(f"Server listening on port {self.port}")
        while True:
            try:
                message = self.socket.recv_string()
                with self.lock:
                    response = self.handle_request(message)
                self.socket.send_string(response)
            except Exception as e:
                print(f"Error in server loop: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Shopping List Server')
    parser.add_argument('--port', type=int, required=True, help="Port for the server to listen on")
    args = parser.parse_args()

    server = Server(port=args.port)
    server.run()
