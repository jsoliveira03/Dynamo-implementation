from ShoppingList import ShoppingList  # Assuming the ShoppingList class is in shopping_list.py
from AWORSet import AWORSet  # Correctly importing AWORSet class
from PN_Counter import PNCounter  # Assuming PNCounter is available in pn_counter.py

def test_shopping_list():
    # Initialize ShoppingList instance
    shopping_list = ShoppingList(owner="user1")

    # Test Case 1: Create a new shopping list
    print("Test Case 1: Creating a Shopping List")
    list_id = shopping_list.create_list("Groceries")
    print(f"Created list with ID: {list_id}")
    print(shopping_list.get_list(list_id))

    # Test Case 2: Add items and update their quantities
    print("\nTest Case 2: Adding Items and Updating Quantities")
    shopping_list.create_item(list_id, "Apple", 10)  # Add 10 apples
    shopping_list.create_item(list_id, "Banana", 5)  # Add 5 bananas
    shopping_list.update_quantity(list_id, "Apple", increment=3)  # Increment apples by 3
    shopping_list.update_quantity(list_id, "Banana", decrement=2)  # Decrement bananas by 2
    print(shopping_list.get_list(list_id))

    # Test Case 3: Delete an item
    print("\nTest Case 3: Deleting an Item")
    shopping_list.delete_item(list_id, "Banana")  # Mark banana as deleted
    print(shopping_list.get_list(list_id))

    # Test Case 4: Merge with remote data
    print("\nTest Case 4: Merging with Remote Data")
    remote_data = {
        list_id: {
            "name": "Groceries",
            "deleted": False,
            "items": {}  # Make sure this is initialized properly
        }
    }

    # Initialize items in remote data (including "Apple" and "Banana")
    remote_data[list_id]["items"]["Apple"] = {
        "counter": PNCounter(),
        "deleted": False
    }
    remote_data[list_id]["items"]["Banana"] = {
        "counter": PNCounter(),
        "deleted": False
    }

    # Simulate changes in remote data
    remote_data[list_id]["items"]["Apple"]["counter"].increment(2)  # Increment Apple quantity
    remote_data[list_id]["items"]["Banana"]["counter"].increment(1)  # Add back 1 banana

    # Add new item to remote data
    remote_data[list_id]["items"]["Orange"] = {
        "counter": PNCounter(),
        "deleted": False
    }
    remote_data[list_id]["items"]["Orange"]["counter"].increment(7)  # Add 7 oranges

    # Merge remote data into the local shopping list
    shopping_list.merge(remote_data)
    print(shopping_list.get_list(list_id))

    # Test Case 5: Checking if the shopping list has changed
    print("\nTest Case 5: Checking Changes")
    print(f"Has shopping list changed? {shopping_list.changed()}")
    print(f"Has shopping list changed again? {shopping_list.changed()}")

if __name__ == "__main__":
    test_shopping_list()

