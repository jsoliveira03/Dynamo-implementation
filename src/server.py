import argparse
import zmq
import json
import os
import threading
from crdt.ShoppingList import ShoppingList

class Server:
    def __init__(self, port):
        self.port = port
        self.shopping_list = ShoppingList(owner=port)
        self.json_path = f"./data/lists_{self.port}.json"
        self.lock = threading.Lock()
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{self.port}")
        self._load_data()

    def _load_data(self):
        """Load data from local storage and merge it into the shopping list."""
        if os.path.exists(self.json_path):
            try:
                with open(self.json_path, "r") as file:
                    # Check if the file is empty
                    content = file.read().strip()
                    if content:
                        data = json.loads(content)
                        self.shopping_list.merge(data)
                    else:
                        print(f"Warning: {self.json_path} is empty, initializing with empty data.")
            except json.JSONDecodeError:
                print(f"Warning: {self.json_path} contains invalid JSON, initializing with empty data.")
            except Exception as e:
                print(f"Error loading data from {self.json_path}: {e}")
        else:
            os.makedirs("./data/", exist_ok=True)
            print(f"Warning: {self.json_path} does not exist, initializing with empty data.")

    def _save_data(self):
        """Save shopping list data to local storage if changes exist."""
        if self.shopping_list.changed():
            with open(self.json_path, "w") as file:
                json.dump(self.shopping_list.info(), file, indent=4)

    def handle_request(self, message):
        """
        Handle incoming client or proxy requests and perform appropriate actions.
        """
        try:
            request = json.loads(message)
            action = request.get("action")
            data = request.get("data", {})
            response = {"success": True} 
            
            if action == "syncLists":
                self.shopping_list.merge(data)
                self._save_data()
                response["lists"] = self.shopping_list.info()
            elif action == "getListById":
                list_id = data.get("list_id")
                if list_id and list_id in self.shopping_list.info():
                    response["list"] = self.shopping_list.info()[list_id]
                else:
                    response = {"success": False, "error": "List ID not found"}
            else:
                response = {"success": False, "error": "Invalid action requested"}

            return json.dumps(response)

        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def run(self):
        """
        Start the server to listen for incoming client or proxy requests.
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
