import uuid
import time
from crdt.PN_Counter import PNCounter


class AWORSet:
    def __init__(self, owner):
        self.owner = owner
        self.items = {}  # Stores items with their states (uuid, name, quantity)
        self.adds = {}   # Tracks added items (with timestamps)
        self.removes = {}  # Tracks removed items (tombstones)

    def add(self, product_name, quantity):
        """Add a product to the set."""
        product_uuid = str(uuid.uuid4())  # Generate a unique UUID for the product
        timestamp = time.time()  # Use timestamp for versioning

        # Add product details with a PN-Counter for quantity
        self.items[product_uuid] = {
            'product_name': product_name,
            'product_quantity': PNCounter(),
            'deleted': False,
            'bought': False,
        }
        self.items[product_uuid]['product_quantity'].increment(quantity)
        self.adds[product_uuid] = timestamp
        self.removes.pop(product_uuid, None) 
        print(f"Added {product_name} with quantity {quantity}.")

    def remove(self, product_uuid):
        """Mark a product as deleted (tombstone)."""
        if product_uuid in self.items:
            timestamp = time.time()
            self.removes[product_uuid] = {'timestamp': timestamp, 'type': 'deleted'}
            self.items[product_uuid]['deleted'] = True
            print(f"Product {self.items[product_uuid]['product_name']} marked as deleted.")
        else:
            print("Item not found to remove.")

    def buy(self, product_uuid):
        """Mark a product as bought."""
        if product_uuid in self.items:
            timestamp = time.time()
            self.removes[product_uuid] = {'timestamp': timestamp, 'type': 'bought'}
            self.items[product_uuid]['bought'] = True
            print(f"Product {self.items[product_uuid]['product_name']} marked as bought.")
        else:
            print("Item not found to mark as bought.")

    def update_quantity(self, product_uuid, increment=0, decrement=0):
        """Update the quantity of an item using its PN-Counter."""
        if product_uuid in self.items:
            if self.items[product_uuid]['deleted']:
                raise ValueError(f"Cannot update quantity for deleted item: {self.items[product_uuid]['product_name']}.")

            counter = self.items[product_uuid]['product_quantity']
            if increment > 0:
                counter.increment(increment)
            if decrement > 0:
                counter.decrement(decrement)
            print(f"Updated quantity for {self.items[product_uuid]['product_name']}: {counter.get_value()}")
        else:
            raise ValueError("Item not found to update.")

    def merge(self, other):
        """Merge another AWORSet into this one."""
        # Merge adds: Take the most recent addition (based on timestamp)
        for product_uuid, timestamp in other.adds.items():
            if product_uuid not in self.adds or timestamp > self.adds[product_uuid]:
                self.adds[product_uuid] = timestamp
                self.items[product_uuid] = other.items[product_uuid]

        # Merge removes (ensure to respect tombstones)
        for product_uuid, remove_info in other.removes.items():
            if product_uuid in self.items:
                # If the remove tombstone is for a deletion
                if remove_info['type'] == 'deleted' and not self.items[product_uuid]['deleted']:
                    self.remove(product_uuid)
                # If the remove tombstone is for a bought item
                elif remove_info['type'] == 'bought' and not self.items[product_uuid]['bought']:
                    self.buy(product_uuid)

        # Merge quantities for items
        for product_uuid, item in self.items.items():
            if product_uuid in other.items:
                item['product_quantity'].merge(other.items[product_uuid]['product_quantity'])

    def get_items(self):
        """Get items in the set, excluding deleted ones."""
        return [
            {
                "uuid": product_uuid,
                "product_name": item['product_name'],
                "product_quantity": item['product_quantity'].get_value(),
                "deleted": item['deleted'],
                "bought": item['bought']
            }
            for product_uuid, item in self.items.items() if not item['deleted']
        ]

    def __str__(self):
        """Return string representation of AWORSet."""
        return f"AWORSet: {self.get_items()}"
    
    def find_uuid_by_name(self, product_name):
        """Find the UUID of an item by its name."""
        for product_uuid, item in self.items.items():
            if item['product_name'] == product_name:
                return product_uuid
        return None

