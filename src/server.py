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

            if action == "createList":
                # Create a new shopping list
                list_id = self.shopping_list.create_list(data["name"])
                response["listId"] = list_id

            elif action == "joinList":
                # Join an existing shopping list
                list_id = data["listId"]
                response["list"] = self.shopping_list.get_list(list_id)

            elif action == "deleteList":
                # Delete a shopping list
                list_id = data["listId"]
                self.shopping_list.delete_list(list_id)

            elif action == "addItem":
                # Add an item to a shopping list
                list_id = data["listId"]
                item = data["item"]
                self.shopping_list.create_item(list_id, item["name"], item["quantity"])

            elif action == "removeItem":
                # Remove an item from a shopping list
                list_id = data["listId"]
                item_name = data["itemName"]
                self.shopping_list.delete_item(list_id, item_name)

            elif action == "updateItem":
                # Update the quantity of an item in a shopping list
                list_id = data["listId"]
                item_name = data["itemName"]
                self.shopping_list.update_quantity(
                    list_id,
                    item_name,
                    increment=data.get("increment", 0),
                    decrement=data.get("decrement", 0)
                )

            elif action == "syncLists":
                client_lists = data  # Data sent by the client
                print("Server received sync data:", client_lists)
                self.shopping_list.merge(client_lists)  # Merge client's lists into server's data
                response["lists"] = self.shopping_list.info()  # Send updated server lists back
                print("Server's updated lists:", self.shopping_list.info())

            elif action == "mergeData":
                # Merge incoming data into the shopping list
                incoming_data = data["lists"]
                self.shopping_list.merge(incoming_data)
                response["message"] = "Merge completed successfully."

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
