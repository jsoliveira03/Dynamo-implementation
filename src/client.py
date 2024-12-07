import zmq
import json
import os
from crdt.ShoppingList import ShoppingList

CONFIG = {
    "json_file": "./client_data.json",
    "server_port": 5500,
}

def load_local_data(file_path):
    """Load local shopping list data from file."""
    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            return json.load(file)
    return {"lists": {}}

def save_local_data(file_path, data):
    """Save shopping list data to a JSON file."""
    with open(file_path, "w") as file:
        json.dump(data, file, indent=4)

def send_request(socket, action, data):
    """Send a request to the server and receive a response."""
    message = {"action": action, "data": data}
    socket.send_string(json.dumps(message))
    return json.loads(socket.recv_string())

if __name__ == "__main__":
    # Initialize ShoppingList
    shopping_list = ShoppingList(owner="client")

    # Load local data into the ShoppingList
    local_data = load_local_data(CONFIG["json_file"])
    shopping_list.merge(local_data)

    # Initialize ZMQ socket for server communication
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect(f"tcp://localhost:{CONFIG['server_port']}")

    while True:
        print("\nOptions:")
        print("1. Create List")
        print("2. Delete List")
        print("3. Add Item")
        print("4. Remove Item")
        print("5. Update Item Quantity")
        print("6. View Lists")
        print("7. Sync with Server")
        print("8. Exit")

        choice = input("Enter your choice: ")
        try:
            if choice == "1":  # Create List
                name = input("Enter list name: ")
                list_id = shopping_list.create_list(name)
                save_local_data(CONFIG["json_file"], shopping_list.info())
                print(f"List '{name}' created with ID: {list_id}")

            elif choice == "2":  # Delete List
                list_id = input("Enter list ID to delete: ")
                shopping_list.delete_list(list_id)
                save_local_data(CONFIG["json_file"], shopping_list.info())
                print(f"List '{list_id}' deleted.")

            elif choice == "3":  # Add Item
                list_id = input("Enter list ID: ")
                item_name = input("Enter item name: ")
                quantity = int(input("Enter quantity: "))
                shopping_list.create_item(list_id, item_name, quantity)
                save_local_data(CONFIG["json_file"], shopping_list.info())
                print(f"Added {quantity} of '{item_name}' to list {list_id}.")

            elif choice == "4":  # Remove Item
                list_id = input("Enter list ID: ")
                item_name = input("Enter item name: ")
                shopping_list.delete_item(list_id, item_name)
                save_local_data(CONFIG["json_file"], shopping_list.info())
                print(f"Removed '{item_name}' from list {list_id}.")

            elif choice == "5":  # Update Item Quantity
                list_id = input("Enter list ID: ")
                item_name = input("Enter item name: ")
                increment = int(input("Enter quantity to increment: "))
                decrement = int(input("Enter quantity to decrement: "))
                shopping_list.update_quantity(list_id, item_name, increment, decrement)
                save_local_data(CONFIG["json_file"], shopping_list.info())
                print(f"Updated quantity of '{item_name}' in list {list_id}.")

            elif choice == "6":  # View Lists
                lists = shopping_list.info()
                print("\nCurrent Shopping Lists:")
                for list_id, details in lists.items():
                    print(f"List ID: {list_id}, Name: {details['name']}")
                    for item in details["items"]:
                        print(f"  - {item['name']} (Quantity: {item['quantity']})")

            elif choice == "7":  # Sync with Server
                server_response = send_request(socket, "syncLists", shopping_list.info())
                if server_response.get("success"):
                    shopping_list.merge(server_response["lists"])
                    save_local_data(CONFIG["json_file"], shopping_list.info())
                    print("Synced with server successfully.")
                else:
                    print(f"Failed to sync with server: {server_response.get('error')}")

            elif choice == "8":  # Exit
                print("Exiting.")
                break

            else:
                print("Invalid choice. Please try again.")

        except Exception as e:
            print(f"Error: {e}")
