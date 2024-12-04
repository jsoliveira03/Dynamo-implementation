import json
import os
import requests
import zmq

# Configuration
CONFIG = {
    "server_url": "http://localhost",  # Base URL for the server
    "json_file": "./client_data.json",  # Local file for storing client state
    "port": 5500,  # Default server port
}

class ShoppingListClient:
    def __init__(self, server_port):
        self.server_port = server_port
        self.base_url = f"tcp://localhost:{self.server_port}"  # Correct the protocol
        self.local_data_file = CONFIG["json_file"]
        self.local_data = self._load_local_data()

    def _load_local_data(self):
        """Load the client's state from a JSON file."""
        if os.path.exists(self.local_data_file):
            with open(self.local_data_file, "r") as file:
                return json.load(file)
        else:
            return {"lists": {}}  # Initialize with an empty structure

    def _save_local_data(self):
        """Save the client's state to a JSON file."""
        with open(self.local_data_file, "w") as file:
            json.dump(self.local_data, file, indent=4)

    def create_list(self, name):
        """Create a new shopping list."""
        response = requests.post(f"{self.base_url}/createList", json={"name": name})
        if response.status_code == 200:
            data = response.json()
            list_id = data["url"]
            self.local_data["lists"][list_id] = {"name": name, "items": []}
            self._save_local_data()
            print(f"List '{name}' created with ID: {list_id}")
        else:
            print("Failed to create list:", response.text)

    def join_list(self, list_url):
        """Join an existing shopping list."""
        response = requests.post(f"{self.base_url}/joinList", json={"listUrl": list_url})
        if response.status_code == 200:
            data = response.json()
            self.local_data["lists"][list_url] = data["list"]
            self._save_local_data()
            print(f"Joined list with ID: {list_url}")
        else:
            print("Failed to join list:", response.text)

    def delete_list(self, list_id):
        """Delete a shopping list."""
        response = requests.post(f"{self.base_url}/deleteList", json={"url": list_id})
        if response.status_code == 200:
            if list_id in self.local_data["lists"]:
                del self.local_data["lists"][list_id]
                self._save_local_data()
            print("List deleted successfully.")
        else:
            print("Failed to delete list:", response.text)

    def add_item(self, list_id, item_name, quantity=1):
        """Add an item to a shopping list."""
        changes = [{"name": item_name, "total": quantity}]
        response = requests.post(
            f"{self.base_url}/changeItems",
            json={"listUrl": list_id, "changes": [changes, [], []]},
        )
        if response.status_code == 200:
            if list_id in self.local_data["lists"]:
                self.local_data["lists"][list_id]["items"].append(
                    {"name": item_name, "quantity": quantity}
                )
                self._save_local_data()
            print(f"Added {quantity} of '{item_name}' to list {list_id}.")
        else:
            print("Failed to add item:", response.text)

    def remove_item(self, list_id, item_name):
        """Remove an item from a shopping list."""
        changes = [{"name": item_name}]
        response = requests.post(
            f"{self.base_url}/changeItems",
            json={"listUrl": list_id, "changes": [[], changes, []]},
        )
        if response.status_code == 200:
            if list_id in self.local_data["lists"]:
                self.local_data["lists"][list_id]["items"] = [
                    item for item in self.local_data["lists"][list_id]["items"]
                    if item["name"] != item_name
                ]
                self._save_local_data()
            print(f"Removed '{item_name}' from list {list_id}.")
        else:
            print("Failed to remove item:", response.text)

    def update_item_quantity(self, list_id, item_name, increment=0, decrement=0):
        """Update the quantity of an item in a shopping list."""
        changes = [{"name": item_name, "current": increment, "total": decrement}]
        response = requests.post(
            f"{self.base_url}/changeItems",
            json={"listUrl": list_id, "changes": [[], [], changes]},
        )
        if response.status_code == 200:
            print(f"Updated quantity of '{item_name}' in list {list_id}.")
        else:
            print("Failed to update item quantity:", response.text)

    def list_all(self):
        """List all the shopping lists."""
        print("Current Shopping Lists:")
        for list_id, details in self.local_data["lists"].items():
            print(f"List ID: {list_id}, Name: {details['name']}")
            for item in details["items"]:
                print(f"  - {item['name']} (Quantity: {item['quantity']})")

    def sync_with_server(self):
        """Sync all local lists with the server."""
        for list_id, details in self.local_data["lists"].items():
            response = requests.get(f"{self.base_url}/lists/{list_id}")
            if response.status_code == 200:
                server_list = response.json()
                self.local_data["lists"][list_id] = server_list
            else:
                print(f"Failed to sync list {list_id}:", response.text)
        self._save_local_data()
        print("Sync complete.")

    def send_hello(self):
        """Send 'Hello' to the server and receive a response."""
        context = zmq.Context()
        socket = context.socket(zmq.REQ)  # REQ socket for request-response
        socket.connect(self.base_url)  # Connect to the server on the provided port

        print("Client is sending 'Hello' to the server...")
        message = {"message": "Hello"}
        socket.send_string(json.dumps(message))  # Send "Hello" message to the server

        response = socket.recv_string()  # Receive response from server
        print(f"Received from server: {response}")

# Main program for client
if __name__ == "__main__":
    client = ShoppingListClient(server_port=CONFIG["port"])
    client.send_hello()

    # while True:
    #     print("\nOptions:")
    #     print("1. Create List")
    #     print("2. Join List")
    #     print("3. Delete List")
    #     print("4. Add Item")
    #     print("5. Remove Item")
    #     print("6. Update Item Quantity")
    #     print("7. List All")
    #     print("8. Sync with Server")
    #     print("9. Exit")

    #     choice = input("Enter your choice: ")
    #     if choice == "1":
    #         name = input("Enter list name: ")
    #         client.create_list(name)
    #     elif choice == "2":
    #         url = input("Enter list URL: ")
    #         client.join_list(url)
    #     elif choice == "3":
    #         list_id = input("Enter list ID to delete: ")
    #         client.delete_list(list_id)
    #     elif choice == "4":
    #         list_id = input("Enter list ID: ")
    #         item = input("Enter item name: ")
    #         qty = int(input("Enter quantity: "))
    #         client.add_item(list_id, item, qty)
    #     elif choice == "5":
    #         list_id = input("Enter list ID: ")
    #         item = input("Enter item name: ")
    #         client.remove_item(list_id, item)
    #     elif choice == "6":
    #         list_id = input("Enter list ID: ")
    #         item = input("Enter item name: ")
    #         inc = int(input("Enter quantity to increment: "))
    #         dec = int(input("Enter quantity to decrement: "))
    #         client.update_item_quantity(list_id, item, increment=inc, decrement=dec)
    #     elif choice == "7":
    #         client.list_all()
    #     elif choice == "8":
    #         client.sync_with_server()
    #     elif choice == "9":
    #         print("Exiting.")
    #         break
    #     else:
    #         print("Invalid choice. Please try again.")
