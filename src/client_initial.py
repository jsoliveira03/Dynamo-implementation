import zmq
import uuid
import hashlib

class ShoppingListClient:
    def __init__(self, username, servers):
        self.username = username
        self.servers = servers
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.current_list_id = None
    
    def _hash_list_id(self, list_id):
        """Determine server for a list based on consistent hashing."""
        hash_value = hashlib.md5(list_id.encode()).hexdigest()
        server_index = int(hash_value, 16) % len(self.servers)
        return self.servers[server_index]
    
    def create_shopping_list(self):
        """Create a new shopping list with a unique ID."""
        list_id = str(uuid.uuid4())
        server = self._hash_list_id(list_id)
        
        self.socket.connect(server)
        request = {
            "action": "create_list",
            "list_id": list_id,
            "owner": self.username
        }
        self.socket.send_json(request)
        response = self.socket.recv_json()
        
        return list_id if response.get("status") == "success" else None
    
    def add_product(self, list_id, product_name, quantity):
        """Add a product to a shopping list."""
        server = self._hash_list_id(list_id)
        
        self.socket.connect(server)
        request = {
            "action": "add_product",
            "list_id": list_id,
            "product": {
                "name": product_name,
                "quantity": quantity,
                "added_by": self.username
            }
        }
        self.socket.send_json(request)
        response = self.socket.recv_json()
        
        return response.get("status") == "success"
    
    def get_shareable_link(self, list_id):
        """Generate a shareable link (in this case, just the list ID)."""
        server = self._hash_list_id(list_id)
        
        self.socket.connect(server)
        request = {
            "action": "get_shareable_link",
            "list_id": list_id
        }
        self.socket.send_json(request)
        response = self.socket.recv_json()
        
        return list_id if response.get("status") == "success" else None
    
    def import_shared_list(self, shared_list_id):
        """Import a shared list using its ID."""
        new_list_id = str(uuid.uuid4())
        server = self._hash_list_id(shared_list_id)
        
        self.socket.connect(server)
        request = {
            "action": "import_shared_list",
            "original_list_id": shared_list_id,
            "new_list_id": new_list_id,
            "importer": self.username
        }
        self.socket.send_json(request)
        response = self.socket.recv_json()
        
        return new_list_id if response.get("status") == "success" else None

def main():
    servers = [
        "tcp://localhost:5001",
        "tcp://localhost:5002",
        "tcp://localhost:5003",
        "tcp://localhost:5004",
        "tcp://localhost:5005"
    ]
    
    # como é que guardamos quem é o user e a quem pertence a lista tanto localmente como no server?
    username = input("Enter your username: ")
    client = ShoppingListClient(username=username, servers=servers)
    
    while True:
        print("\n--- Shopping List Menu ---")
        print("1. Create a new shopping list")
        print("2. Add product to current list")
        print("3. Get shareable list link")
        print("4. Import shared list")
        print("5. Exit")
        
        choice = input("Enter your choice (1-5): ")
        
        if choice == '1':
            list_id = client.create_shopping_list()
            if list_id:
                print(f"Created shopping list: {list_id}")
                client.current_list_id = list_id
            else:
                print("Failed to create shopping list")
        
        elif choice == '2':
            if not client.current_list_id:
                print("No current list. Create a list first.")
                continue
            
            product_name = input("Enter product name: ")
            try:
                quantity = int(input("Enter quantity: "))
                success = client.add_product(client.current_list_id, product_name, quantity)
                print("Product added successfully" if success else "Product addition failed")
            except ValueError:
                print("Invalid quantity. Please enter a number.")
        
        elif choice == '3':
            if not client.current_list_id:
                print("No current list to share.")
                continue
            
            shareable_link = client.get_shareable_link(client.current_list_id)
            if shareable_link:
                print(f"Shareable list ID: {shareable_link}")
            else:
                print("Failed to get shareable link")
        
        elif choice == '4':
            shared_list_id = input("Enter the shared list ID: ")
            imported_list_id = client.import_shared_list(shared_list_id)
            if imported_list_id:
                print(f"List imported with ID: {imported_list_id}")
                client.current_list_id = imported_list_id
            else:
                print("List import failed")
        
        elif choice == '5':
            print("Exiting...")
            break
        
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()