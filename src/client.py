import zmq
import json
import os
import threading
import time
from crdt.ShoppingList import ShoppingList

CONFIG = {
    "json_file": "./client_data.json",
    "proxy_port": 9000,  # The port where the proxy is running
    "sync_interval": 15,
}

class ShoppingListClient:
    def __init__(self):
        self.shopping_list = ShoppingList(owner="client")
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        
        self.sync_lock = threading.Lock()
        self.running = True
        
        # Load initial data
        self._load_local_data()
        
        # Start sync thread for automatic synchronization
        self.sync_thread = threading.Thread(target=self._auto_sync, daemon=True)
        self.sync_thread.start()

    def _load_local_data(self):
        """Load local shopping list data from file."""
        if os.path.exists(CONFIG["json_file"]):
            try:
                with open(CONFIG["json_file"], "r") as file:
                    content = file.read().strip()
                    if content:
                        data = json.loads(content)  # Parse JSON data
                        self.shopping_list.merge(data)  # Merge with local shopping list
                    else:
                        print(f"Warning: {CONFIG['json_file']} is empty, initializing with empty data.")
            except json.JSONDecodeError:
                print(f"Warning: {CONFIG['json_file']} contains invalid JSON, initializing with empty data.")
            except Exception as e:
                print(f"Error loading data from {CONFIG['json_file']}: {e}")
        else:
            print(f"Warning: {CONFIG['json_file']} does not exist, initializing with empty data.")
            # You can optionally initialize an empty shopping list here if needed

    def _save_local_data(self):
        """Save shopping list data to a JSON file."""
        with open(CONFIG["json_file"], "w") as file:
            json.dump(self.shopping_list.info(), file, indent=4)

    def _send_request(self, action, data):
        """Send a request to the proxy and receive a response."""
        message = {"action": action, "data": data}
        try:
            # Connect to the proxy that will route the request to the correct server
            self.socket.connect(f"tcp://localhost:{CONFIG['proxy_port']}")
            self.socket.send_string(json.dumps(message))
            response = self.socket.recv_string()
            return json.loads(response)
        except zmq.error.Again:
            print("Proxy not responding")
            return {"success": False, "error": "Proxy not responding"}
        except Exception as e:
            print(f"Error communicating with proxy: {e}")
            return {"success": False, "error": str(e)}

    def _auto_sync(self):
        """Background thread for automatic synchronization."""
        while self.running:
            time.sleep(CONFIG["sync_interval"])
            self.sync_with_server()

    def sync_with_server(self):
        """Synchronize with the proxy and handle conflicts."""
        with self.sync_lock:
            try:
                # Fetch the server's state and merge with local state
                response = self._send_request("syncLists", self.shopping_list.info())
                if response.get("success"):

                    self.shopping_list.merge(response.get("lists"))
                    self._save_local_data()
                    print("\nSynced with server successfully.")
                else:
                    print(f"\nFailed to sync with server: {response.get('error')}")
            except Exception as e:
                print(f"\nSync error: {e}")

    def create_list(self, name):
        """Create a new shopping list."""
        list_id = self.shopping_list.create_list(name)
        self._save_local_data()
        return list_id

    def delete_list(self, list_id):
        """Delete a shopping list."""
        self.shopping_list.delete_list(list_id)
        self._save_local_data()

    def buy_item(self, list_id, item_name):
        """Buy an item from a shopping list."""
        self.shopping_list.buy_item(list_id, item_name)
        self._save_local_data()

    def create_item(self, list_id, item_name, quantity):
        """Add an item to a shopping list."""
        self.shopping_list.create_item(list_id, item_name, quantity)
        self._save_local_data()

    def delete_item(self, list_id, item_name):
        """Remove an item from a shopping list."""
        self.shopping_list.delete_item(list_id, item_name)
        self._save_local_data()

    def update_quantity(self, list_id, item_name, increment, decrement):
        """Update the quantity of an item."""
        self.shopping_list.update_quantity(list_id, item_name, increment, decrement)
        self._save_local_data()

    def get_lists(self):
        """Get all shopping lists."""
        return self.shopping_list.info()

    def shutdown(self):
        """Clean shutdown of the client."""
        self.running = False
        self.sync_thread.join()
        self.socket.close()
        self.context.term()

if __name__ == "__main__":
    client = ShoppingListClient()
    
    while True:
        print("\nOptions:")
        print("1. Create List")
        print("2. Delete List")
        print("3. Add Item")
        print("4. Remove Item")
        print("5. Update Item Quantity")
        print("6. View Lists")
        print("7. Buy Item")
        print("8. Exit")

        choice = input("Enter your choice: ")
        try:
            if choice == "1":
                name = input("Enter list name: ")
                list_id = client.create_list(name)
                print(f"List '{name}' created with ID: {list_id}")

            elif choice == "2":
                list_id = input("Enter list ID to delete: ")
                client.delete_list(list_id)
                print(f"List '{list_id}' deleted.")

            elif choice == "3":
                list_id = input("Enter list ID: ")
                item_name = input("Enter item name: ")
                quantity = int(input("Enter quantity: "))
                client.create_item(list_id, item_name, quantity)
                print(f"Added {quantity} of '{item_name}' to list {list_id}.")

            elif choice == "4":
                list_id = input("Enter list ID: ")
                item_name = input("Enter item name: ")
                client.delete_item(list_id, item_name)
                print(f"Removed '{item_name}' from list {list_id}.")

            elif choice == "5":
                list_id = input("Enter list ID: ")
                item_name = input("Enter item name: ")
                increment = int(input("Enter quantity to increment: "))
                decrement = int(input("Enter quantity to decrement: "))
                client.update_quantity(list_id, item_name, increment, decrement)
                print(f"Updated quantity of '{item_name}' in list {list_id}.")

            elif choice == "6":
                lists = client.get_lists()
                print("\nCurrent Shopping Lists:")
                for list_id, details in lists.items():
                    print(f"List ID: {list_id}, Name: {details['name']}")
                    for item in details["items"]:
                        print(f"  - {item['product_name']} (Quantity: {item['product_quantity']})")
            
            elif choice == "7":
                list_id = input("Enter list ID: ")
                item_name = input("Enter item name: ")
                try:
                    client.buy_item(list_id, item_name)
                    print(f"Marked '{item_name}' as bought.")
                except ValueError as e:
                    print(f"Error: {e}")

            elif choice == "8":
                print("Exiting.")
                client.shutdown()
                break

            else:
                print("Invalid choice. Please try again.")

        except Exception as e:
            print(f"Error: {e}")
