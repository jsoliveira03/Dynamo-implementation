import uuid
import time
from crdt.PN_Counter import PNCounter

class AWORSet:
    def __init__(self, owner):
        self.owner = owner
        self.items = {}  # Stores items with their states (uuid, name, quantity)
        self.adds = {}   # Tracks added items (with timestamps)
        self.removes = {}  # Tracks removed items (tombstones)
        self.bought = {}

    def add(self, product_name, quantity, product_uuid=None):
        """Add a product to the set."""
        if product_uuid is None:
            product_uuid = str(uuid.uuid4())  # Generate a unique UUID if none provided
        timestamp = time.time()  # Use timestamp for versioning

        if product_uuid not in self.removes or timestamp > self.removes[product_uuid].get('timestamp', 0):
            if product_uuid not in self.items:
                self.items[product_uuid] = {
                    'product_name': product_name,
                    'product_quantity': PNCounter(),
                    'deleted': False,
                    'bought': False,
                    'timestamp': timestamp  
                }
            self.items[product_uuid]['product_quantity'].increment(quantity)
            self.adds[product_uuid] = timestamp
            self.removes.pop(product_uuid, None)  

    def remove(self, product_uuid):
        """Mark a product as deleted and remove it locally."""
        if product_uuid in self.items:
            timestamp = time.time()
            self.removes[product_uuid] = {
                'timestamp': timestamp,
                'type': 'deleted',
                'by': self.owner
            }
            if self.items[product_uuid]:
                item_data = self.items[product_uuid].copy()
                item_data['deleted'] = True
                item_data['timestamp'] = timestamp
                self.items[product_uuid] = item_data
            del self.items[product_uuid]
            print(f"Product removed locally.")
        else:
            print("Item not found to remove.")

    def buy_item(self, product_uuid):
        """Mark a product as bought and set quantity to 0."""
        if product_uuid in self.items:
            timestamp = time.time()
            # Store bought info
            self.bought[product_uuid] = {
                'timestamp': timestamp,
                'by': self.owner
            }
            
            # Set quantity to 0 by calculating current quantity and decrementing it
            current_quantity = self.items[product_uuid]['product_quantity'].get_value()
            self.items[product_uuid]['product_quantity'].decrement(current_quantity)
            
            # Mark as bought
            self.items[product_uuid]['bought'] = True
            self.items[product_uuid]['timestamp'] = timestamp
            
            # If this is a client, remove the item locally
            if self.owner == "client":
                del self.items[product_uuid]
            
            print(f"Product marked as bought.")
            return True
        else:
            print("Item not found to buy.")
            return False

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
            self.items[product_uuid]['timestamp'] = time.time()
            print(f"Updated quantity for {self.items[product_uuid]['product_name']}: {counter.get_value()}")
        else:
            raise ValueError("Item not found to update.")

    def merge(self, other):
        """Merge another AWORSet into this one."""
        # First, handle removals and bought items which can affect the items dictionary
        for product_uuid, remove_info in other.removes.items():
            if (product_uuid not in self.removes or 
                remove_info['timestamp'] > self.removes[product_uuid]['timestamp']):
                self.removes[product_uuid] = remove_info.copy()
                if product_uuid in self.items:
                    if self.owner != "client":  
                        self.items[product_uuid]['deleted'] = True
                        self.items[product_uuid]['timestamp'] = remove_info['timestamp']
                    else:  
                        del self.items[product_uuid]

        # Handle bought items with proper timestamp comparison
        for product_uuid, bought_info in other.bought.items():
            if (product_uuid not in self.bought or 
                bought_info['timestamp'] > self.bought[product_uuid]['timestamp']):
                self.bought[product_uuid] = bought_info.copy()
                
                # Update or create the item with bought status
                if product_uuid in other.items:
                    if self.owner != "client":
                        if product_uuid not in self.items:
                            self.items[product_uuid] = other.items[product_uuid].copy()
                        self.items[product_uuid]['bought'] = True
                        self.items[product_uuid]['product_quantity'].set_to_zero()
                        self.items[product_uuid]['timestamp'] = bought_info['timestamp']
                    else:
                        # Client should remove bought items
                        if product_uuid in self.items:
                            del self.items[product_uuid]

        # Then handle additions and updates
        for product_uuid, timestamp in other.adds.items():
            if (product_uuid not in self.items or 
                (product_uuid in other.items and 
                 other.items[product_uuid]['timestamp'] > self.items[product_uuid].get('timestamp', 0))):
                
                # Only add if not bought or removed (for client)
                if ((product_uuid not in self.bought and 
                     product_uuid not in self.removes) or 
                    self.owner != "client"):
                    self.adds[product_uuid] = timestamp
                    if product_uuid in other.items:
                        if product_uuid not in self.items:
                            self.items[product_uuid] = other.items[product_uuid].copy()
                        if product_uuid in self.bought:
                            self.items[product_uuid]['bought'] = True
                            self.items[product_uuid]['product_quantity'].set_to_zero()

        # Finally, merge PN-Counters for quantities
        for product_uuid, item in list(self.items.items()):
            if product_uuid in other.items:
                item['product_quantity'].merge(other.items[product_uuid]['product_quantity'])
                # Ensure bought status is preserved
                if product_uuid in self.bought:
                    item['bought'] = True
                    item['product_quantity'].set_to_zero()


    def get_items(self):
        """Get items in the set."""
        items_list = []
        for product_uuid, item in self.items.items():
            items_list.append({
                "uuid": product_uuid,
                "product_name": item['product_name'],
                "product_quantity": item['product_quantity'].get_value(),
                "deleted": item['deleted'],
                "bought": product_uuid in self.bought,
                "timestamp": item['timestamp']
            })
        return items_list

    def __str__(self):
        """Return string representation of AWORSet."""
        return f"AWORSet: {self.get_items()}"
    
    def find_uuid_by_name(self, product_name):
        """Find the UUID of an item by its name."""
        for product_uuid, item in self.items.items():
            if item['product_name'] == product_name and not item['deleted']:
                return product_uuid
        return None