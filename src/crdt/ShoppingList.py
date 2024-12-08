import uuid
from crdt.AWORSet import AWORSet

class ShoppingList:
    def __init__(self, owner):
        self.owner = owner
        self.lists = {}
        self.has_change = True

    def create_list(self, name):
        """Create a new shopping list."""
        list_id = str(uuid.uuid4())
        self.lists[list_id] = {
            "name": name,
            "deleted": False,
            "items": AWORSet(owner=self.owner)  # Use AWORSet for managing items
        }
        self.has_change = True
        return list_id
    
    def buy_item(self, list_id, item_name):
        """Mark an item as bought."""
        if list_id not in self.lists or self.lists[list_id]["deleted"]:
            raise ValueError("List not found or deleted.")

        item_uuid = self.lists[list_id]["items"].find_uuid_by_name(item_name)
        if item_uuid:
            success = self.lists[list_id]["items"].buy_item(item_uuid)
            if success:
                self.has_change = True
            return success
        else:
            raise ValueError(f"Item '{item_name}' not found in the list.")

    def delete_list(self, list_id):
        """Mark a shopping list as deleted."""
        if list_id in self.lists:
            self.lists[list_id]["deleted"] = True
            self.has_change = True
        else:
            raise ValueError("List not found.")

    def create_item(self, list_id, item_name, quantity=1):
        """Add an item to the specified shopping list."""
        if list_id not in self.lists or self.lists[list_id]["deleted"]:
            raise ValueError("List not found or deleted.")

        self.lists[list_id]["items"].add(item_name, quantity)
        self.has_change = True

    def load(self, data):
        """Load shopping list data from a JSON-like structure."""
        for list_id, list_data in data.items():
            # Initialize the list with name and deleted status
            self.lists[list_id] = {
                "name": list_data.get("name", "Unnamed List"),
                "deleted": list_data.get("deleted", False),
                "items": AWORSet(owner=self.owner)  # Create AWORSet for items
            }
            
            # Load items into the AWORSet
            items = list_data.get("items", {})
            for item_uuid, item_data in items.items():
                name = item_data["name"]
                counter_data = item_data["counter"]
                increments = counter_data.get("increments", 0)
                decrements = counter_data.get("decrements", 0)
                
                # Add the item to the AWORSet with the proper PN-Counter values
                self.lists[list_id]["items"].add(name, increments - decrements)

        self.has_change = True

    def delete_item(self, list_id, item_name):
        """Mark an item as deleted."""
        if list_id not in self.lists or self.lists[list_id]["deleted"]:
            raise ValueError("List not found or deleted.")

        item_uuid = self.lists[list_id]["items"].find_uuid_by_name(item_name)
        if item_uuid:
            self.lists[list_id]["items"].remove(item_uuid)
            self.has_change = True
        else:
            raise ValueError(f"Item '{item_name}' not found in the list.")

    def update_quantity(self, list_id, item_name, increment=0, decrement=0):
        """Update the quantity of an item using AWORSet's PN-Counter."""
        if list_id not in self.lists or self.lists[list_id]["deleted"]:
            raise ValueError("List not found or deleted.")

        item_uuid = self.lists[list_id]["items"].find_uuid_by_name(item_name)
        if not item_uuid:
            raise ValueError(f"Item '{item_name}' not found in the list.")

        item = self.lists[list_id]["items"].items[item_uuid]
        if item["deleted"]:
            raise ValueError(f"Item '{item_name}' is marked as deleted.")

        if increment > 0:
            item["product_quantity"].increment(increment)
        if decrement > 0:
            item["product_quantity"].decrement(decrement)

        self.has_change = True

    def get_list(self, list_id):
        """Retrieve a shopping list in JSON-like format."""
        if list_id not in self.lists:
            raise ValueError("List not found.")

        shopping_list = self.lists[list_id]
        if shopping_list["deleted"]:
            return None

        return {
            "name": shopping_list["name"],
            "deleted": shopping_list["deleted"],
            "items": shopping_list["items"].get_items()
        }

    def merge(self, remote_data):
        """Merge this ShoppingList instance with a remote replica."""
        for list_id, remote_list in remote_data.items():
            if list_id not in self.lists:
                # Create a new list locally
                self.lists[list_id] = {
                    "name": remote_list["name"],
                    "deleted": remote_list["deleted"],
                    "items": AWORSet(owner=self.owner),
                }

            local_list = self.lists[list_id]
            
            # Update name and deletion status based on the remote data
            if not local_list["deleted"] or remote_list["deleted"]:
                local_list["name"] = remote_list["name"]
                local_list["deleted"] = remote_list["deleted"]

                # Only merge items if the list is not deleted
                if not local_list["deleted"]:
                    remote_aworset = AWORSet(owner=self.owner)
                    for item in remote_list["items"]:
                        remote_aworset.add(
                            product_name=item["product_name"],
                            quantity=item["product_quantity"],
                            product_uuid=item["uuid"],
                            deleted=item["deleted"],
                            bought=item["bought"]
                        )
                    # Merge items using AWORSet
                    local_list["items"].merge(remote_aworset)

        self.has_change = True


    def info(self):
        """Return all lists and their items in a JSON-like format."""
        return {
            list_id: {
                "name": lst["name"],
                "deleted": lst["deleted"],
                "items": lst["items"].get_items()
            }
            for list_id, lst in self.lists.items()
            if not lst["deleted"]
        }

    def changed(self):
        """Check if the ShoppingList has changed since last sync."""
        state = self.has_change
        self.has_change = False
        return state
