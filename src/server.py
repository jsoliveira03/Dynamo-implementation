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
        self.shopping_list = ShoppingList(owner=port)
        self.json_path = f"{CONFIG['json_folder']}lists.json"
        self.lock = threading.Lock()
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{self.port}")
        self._load_data()

    def _load_data(self):
        if os.path.exists(self.json_path):
            with open(self.json_path, "r") as file:
                data = json.load(file)
                self.shopping_list.merge(data)
        else:
            os.makedirs(CONFIG['json_folder'], exist_ok=True)

    def _save_data(self):
        if self.shopping_list.changed():
            with open(self.json_path, "w") as file:
                json.dump(self.shopping_list.info(), file, indent=4)

    def handle_request(self, message):
        try:
            request = json.loads(message)
            action = request.get("action")
            data = request.get("data", {})
            response = {"success": True}

            if action == "createList":
                list_id = self.shopping_list.create_list(data["name"])
                response["listId"] = list_id

            elif action == "joinList":
                list_id = data["listId"]
                response["list"] = self.shopping_list.get_list(list_id)

            elif action == "deleteList":
                list_id = data["listId"]
                self.shopping_list.delete_list(list_id)

            elif action == "addItem":
                list_id = data["listId"]
                item = data["item"]
                self.shopping_list.create_item(list_id, item["name"], item["quantity"])

            elif action == "removeItem":
                list_id = data["listId"]
                item_name = data["itemName"]
                self.shopping_list.delete_item(list_id, item_name)

            elif action == "updateItem":
                list_id = data["listId"]
                item_name = data["itemName"]
                self.shopping_list.update_quantity(
                    list_id, 
                    item_name,
                    increment=data["increment"],
                    decrement=data["decrement"]
                )

            elif action == "syncLists":
                response["lists"] = self.shopping_list.info()

            self._save_data()
            return json.dumps(response)

        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def run(self):
        print(f"Server listening on port {self.port}")
        while True:
            message = self.socket.recv_string()
            with self.lock:
                response = self.handle_request(message)
            self.socket.send_string(response)

if __name__ == "__main__":
    server = Server()
    server.run()