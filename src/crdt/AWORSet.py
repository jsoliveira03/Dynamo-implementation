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
    
    def __repr__(self):
        """Provide a string representation of the AWORSet."""
        items_repr = ", ".join(f"{uuid}: {item['product_name']} (Quantity: {item['product_quantity'].get_value()}, Timestamp: {item['timestamp']})"
                               for uuid, item in self.items.items())
        
        removes_repr = ", ".join(f"{uuid}: {remove_info}" for uuid, remove_info in self.removes.items())
        
        adds_repr = ", ".join(f"{uuid}: {timestamp}" for uuid, timestamp in self.adds.items())
        
        return (f"AWORSet(owner={self.owner}, "
                f"Items={{ {items_repr} }}, "
                f"Adds={{ {adds_repr} }}, "
                f"Removes={{ {removes_repr} }})")
    
    def add(self, product_name, quantity, product_uuid=None, deleted=False, bought=False, timestamp=None):
        """Add a product to the set."""
        if product_uuid is None:
            product_uuid = str(uuid.uuid4())  # Generate a unique UUID if none provided
        if timestamp is None:
            timestamp = time.time()  # Use current time if no timestamp is provided

        # Only add if it's not removed, or the new timestamp is greater than the removal timestamp
        if product_uuid not in self.removes or timestamp > self.removes[product_uuid].get('timestamp', 0):
            if product_uuid not in self.items:
                self.items[product_uuid] = {
                    'product_name': product_name,
                    'product_quantity': PNCounter(),
                    'deleted': deleted,
                    'bought': bought,
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
                'type': 'bought',
                'by': self.owner
            }
            
            if self.items[product_uuid]:
                item_data = self.items[product_uuid].copy()
                item_data['bought'] = True
                item_data['product_quantity'] = PNCounter()
                item_data['timestamp'] = timestamp
                self.items[product_uuid] = item_data
            
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
        # Merge removals first - more aggressive tombstone propagation
        # print("self")
        # print(self.items)
        # print("other")
        # print(other.items)
        for product_uuid, remove_info in other.removes.items():
            if (product_uuid not in self.removes or 
                remove_info['timestamp'] > self.removes[product_uuid]['timestamp']):
                self.removes[product_uuid] = remove_info.copy()
                
                # Ensure deletion is handled properly, even on client
                if product_uuid in self.items:
                    self.items[product_uuid]['deleted'] = True
                    self.items[product_uuid]['timestamp'] = remove_info['timestamp']
                    
                    # For the client, the item should be removed locally when deleted
                    if self.owner == "client":
                        del self.items[product_uuid]

        # Merge additions
        # print( "ADDDDDDSSSSSS" + other.adds.items())
        for product_uuid, timestamp in other.adds.items():
            # Conditions for adding/updating the item
            is_not_deleted = (
                product_uuid not in self.removes or 
                self.removes[product_uuid]['type'] != 'deleted'
            )
            
            is_newer = (
                product_uuid not in self.items or 
                (product_uuid in other.items and 
                other.items[product_uuid]['timestamp'] > self.items[product_uuid].get('timestamp', 0))
            )

            # print("is Newer")
            # print(is_newer)
            
            if is_not_deleted and is_newer:
                self.adds[product_uuid] = timestamp
                if product_uuid in other.items:
                    self.items[product_uuid] = other.items[product_uuid].copy()

        # print("self11111")
        # print(self.items)
        # print("other11111")
        # print(other.items)

        # Merge item quantities
        for product_uuid, item in list(self.items.items()):
            if product_uuid in other.items:
                # Only merge if not deleted
                if not item.get('deleted', False):
                    item['product_quantity'].merge(other.items[product_uuid]['product_quantity'])




    def get_items(self):
        """Get items in the set."""
        items_list = []
        for product_uuid, item in self.items.items():
            items_list.append({
                "uuid": product_uuid,
                "product_name": item['product_name'],
                "product_quantity": item['product_quantity'].get_value(),
                "deleted": item['deleted'],
                "bought": item['bought'],
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