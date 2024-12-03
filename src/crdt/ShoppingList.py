import uuid
from AWORSet import AWORSet

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
        return {
            "name": shopping_list["name"],
            "deleted": shopping_list["deleted"],
            "items": shopping_list["items"].get_items()
        }

    def merge(self, remote_data):
        """Merge this ShoppingList instance with a remote replica."""
        for list_id, remote_list in remote_data.items():
            if list_id not in self.lists:
                # Add new list
                self.lists[list_id] = {
                    "name": remote_list["name"],
                    "deleted": remote_list["deleted"],
                    "items": AWORSet(owner=self.owner)  # Wrap the items in AWORSet
                }
                # Now merge the items into AWORSet
                for item_name, item in remote_list["items"].items():
                    self.lists[list_id]["items"].add(item_name, item["counter"].get_value())
            else:
                # Merge lists
                local_list = self.lists[list_id]
                if remote_list["deleted"] and not local_list["deleted"]:
                    self.delete_list(list_id)
                elif not remote_list["deleted"] and local_list["deleted"]:
                    continue

                # Merge items using AWORSet
                # Ensure items are merged correctly by passing AWORSet instances
                local_list["items"].merge(AWORSet(owner=self.owner))  # Wrap the remote items in AWORSet
                for item_name, remote_item in remote_list["items"].items():
                    if item_name not in local_list["items"].items:
                        local_list["items"].add(item_name, remote_item["counter"].get_value())
                    else:
                        local_item = local_list["items"].find_uuid_by_name(item_name)
                        local_item["product_quantity"].merge(remote_item["counter"])

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
        }

    def changed(self):
        """Check if the ShoppingList has changed since last sync."""
        state = self.has_change
        self.has_change = False
        return state
