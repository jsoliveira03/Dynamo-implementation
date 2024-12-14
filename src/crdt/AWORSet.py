import uuid
from crdt.PN_Counter import PNCounter

class AWORSet:
    def __init__(self, owner):
        self.owner = owner
        self.items = {}  
        self.adds = {}
        self.removes = {}
        self.bought = {}
    
    def _get_next_timestamp(self):
        """Get the next logical timestamp based on the current state."""
        max_timestamp = 0
        for container in [self.items.values(), self.adds.values(), self.removes.values(), self.bought.values()]:
            for entry in container:
                if isinstance(entry, dict):  
                    max_timestamp = max(max_timestamp, entry.get('timestamp', 0))
                else:  
                    max_timestamp = max(max_timestamp, entry)
        return max_timestamp + 1  
    
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
            product_uuid = str(uuid.uuid4())  
        if timestamp is None:
            timestamp = self._get_next_timestamp()  

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
            timestamp = self._get_next_timestamp()
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
            timestamp = self._get_next_timestamp()
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

    def merge(self, other):
        """Merge another AWORSet into this one."""
        for product_uuid, remove_info in other.removes.items():
            if (product_uuid not in self.removes or 
                remove_info['timestamp'] > self.removes[product_uuid]['timestamp']):
                self.removes[product_uuid] = remove_info.copy()
                
                if product_uuid in self.items:
                    self.items[product_uuid]['deleted'] = True
                    self.items[product_uuid]['timestamp'] = remove_info['timestamp']
                    
                    if self.owner == "client":
                        del self.items[product_uuid]

        for product_uuid, timestamp in other.adds.items():
            is_not_deleted = (
                product_uuid not in self.removes or 
                self.removes[product_uuid]['type'] != 'deleted'
            )
            
            is_newer = (
                product_uuid not in self.items or 
                (product_uuid in other.items and 
                other.items[product_uuid]['timestamp'] > self.items[product_uuid].get('timestamp', 0))
            )

            
            if is_not_deleted and is_newer:
                self.adds[product_uuid] = timestamp
                if product_uuid in other.items:
                    self.items[product_uuid] = other.items[product_uuid].copy()

        for product_uuid, item in list(self.items.items()):
            if product_uuid in other.items:
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