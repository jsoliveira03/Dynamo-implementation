import zmq
import threading
import json
import os
from crdt.ShoppingList import ShoppingList

CONFIG = {
    "json_folder": "./data/",
    "port": 5500
}

class Server:
    def __init__(self, port=CONFIG["port"]):
        self.port = port
        self.shopping_list = ShoppingList(owner=port)  # Initialize ShoppingList
        self.json_path = f"{CONFIG['json_folder']}lists.json"
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
                client_lists = data  # Data sent by the client
                print("Server received sync data:", client_lists)
                self.shopping_list.merge(client_lists)  # Merge client's lists into server's data
                response["lists"] = self.shopping_list.info()  # Send updated server lists back
                print("Server's updated lists:", self.shopping_list.info())

            else:
                print("\n\n\nInvalid action requested. (mauybe revert to the other commit where we had other actions here)\n\n\n")

            # Save data after handling the request
            self._save_data()

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
    server = Server()
    server.run()
