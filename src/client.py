import json
import os
import zmq

CONFIG = {
    "json_file": "./client_data.json",
    "port": 5500,
}

class ShoppingListClient:
    def __init__(self, server_port):
        self.server_port = server_port
        self.base_url = f"tcp://localhost:{self.server_port}"
        self.local_data_file = CONFIG["json_file"]
        self.local_data = self._load_local_data()
        
        # Initialize ZMQ context and socket
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(self.base_url)

    def _load_local_data(self):
        if os.path.exists(self.local_data_file):
            with open(self.local_data_file, "r") as file:
                return json.load(file)
        return {"lists": {}}

    def _save_local_data(self):
        with open(self.local_data_file, "w") as file:
            json.dump(self.local_data, file, indent=4)

    def _send_request(self, action, data):
        message = {"action": action, "data": data}
        self.socket.send_string(json.dumps(message))
        response = json.loads(self.socket.recv_string())
        return response

    def create_list(self, name):
        response = self._send_request("createList", {"name": name})
        if response.get("success"):
            list_id = response["listId"]
            self.local_data["lists"][list_id] = {"name": name, "items": []}
            self._save_local_data()
            print(f"List '{name}' created with ID: {list_id}")
        else:
            print("Failed to create list:", response.get("error"))

    def join_list(self, list_id):
        response = self._send_request("joinList", {"listId": list_id})
        if response.get("success"):
            self.local_data["lists"][list_id] = response["list"]
            self._save_local_data()
            print(f"Joined list with ID: {list_id}")
        else:
            print("Failed to join list:", response.get("error"))

    def delete_list(self, list_id):
        response = self._send_request("deleteList", {"listId": list_id})
        if response.get("success"):
            if list_id in self.local_data["lists"]:
                del self.local_data["lists"][list_id]
                self._save_local_data()
            print("List deleted successfully.")
        else:
            print("Failed to delete list:", response.get("error"))

    def add_item(self, list_id, item_name, quantity=1):
        response = self._send_request("addItem", {
            "listId": list_id,
            "item": {"name": item_name, "quantity": quantity}
        })
        if response.get("success"):
            if list_id in self.local_data["lists"]:
                self.local_data["lists"][list_id]["items"].append({
                    "name": item_name,
                    "quantity": quantity
                })
                self._save_local_data()
            print(f"Added {quantity} of '{item_name}' to list {list_id}.")
        else:
            print("Failed to add item:", response.get("error"))

    def remove_item(self, list_id, item_name):
        response = self._send_request("removeItem", {
            "listId": list_id,
            "itemName": item_name
        })
        if response.get("success"):
            if list_id in self.local_data["lists"]:
                self.local_data["lists"][list_id]["items"] = [
                    item for item in self.local_data["lists"][list_id]["items"]
                    if item["name"] != item_name
                ]
                self._save_local_data()
            print(f"Removed '{item_name}' from list {list_id}.")
        else:
            print("Failed to remove item:", response.get("error"))

    def update_item_quantity(self, list_id, item_name, increment=0, decrement=0):
        response = self._send_request("updateItem", {
            "listId": list_id,
            "itemName": item_name,
            "increment": increment,
            "decrement": decrement
        })
        if response.get("success"):
            print(f"Updated quantity of '{item_name}' in list {list_id}.")
        else:
            print("Failed to update item quantity:", response.get("error"))

    def list_all(self):
        print("\nCurrent Shopping Lists:")
        for list_id, details in self.local_data["lists"].items():
            print(f"\nList ID: {list_id}, Name: {details['name']}")
            for item in details["items"]:
                print(f"  - {item['name']} (Quantity: {item['quantity']})")

    def sync_with_server(self):
        response = self._send_request("syncLists", {})
        if response.get("success"):
            self.local_data["lists"] = response["lists"]
            self._save_local_data()
            print("Sync complete.")
        else:
            print("Failed to sync:", response.get("error"))

    def __del__(self):
        self.socket.close()
        self.context.term()

if __name__ == "__main__":
    client = ShoppingListClient(server_port=CONFIG["port"])

    while True:
        print("\nOptions:")
        print("1. Create List")
        print("2. Join List")
        print("3. Delete List")
        print("4. Add Item")
        print("5. Remove Item")
        print("6. Update Item Quantity")
        print("7. List All")
        print("8. Sync with Server")
        print("9. Exit")

        choice = input("Enter your choice: ")
        try:
            if choice == "1":
                name = input("Enter list name: ")
                client.create_list(name)
            elif choice == "2":
                list_id = input("Enter list ID: ")
                client.join_list(list_id)
            elif choice == "3":
                list_id = input("Enter list ID to delete: ")
                client.delete_list(list_id)
            elif choice == "4":
                list_id = input("Enter list ID: ")
                item = input("Enter item name: ")
                qty = int(input("Enter quantity: "))
                client.add_item(list_id, item, qty)
            elif choice == "5":
                list_id = input("Enter list ID: ")
                item = input("Enter item name: ")
                client.remove_item(list_id, item)
            elif choice == "6":
                list_id = input("Enter list ID: ")
                item = input("Enter item name: ")
                inc = int(input("Enter quantity to increment: "))
                dec = int(input("Enter quantity to decrement: "))
                client.update_item_quantity(list_id, item, increment=inc, decrement=dec)
            elif choice == "7":
                client.list_all()
            elif choice == "8":
                client.sync_with_server()
            elif choice == "9":
                print("Exiting.")
                break
            else:
                print("Invalid choice. Please try again.")
        except Exception as e:
            print(f"Error: {e}")