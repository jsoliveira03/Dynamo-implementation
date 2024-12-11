import hashlib
import bisect
from collections import defaultdict
import random

class HashRing:
    def __init__(self, servers, replicas=3):
        self.replicas = replicas
        self.servers = set(servers)  
        self.ring = []  
        self.server_load = defaultdict(int)
        self.load_threshold = 0.2
        self.populate_ring()

    def populate_ring(self):
        """Populate the hash ring using a simple hash of server names."""
        self.ring = []
        for server in self.servers:
            for i in range(self.replicas):
                virtual_node = f"{server}:{i}"
                server_hash = self.hash_server(virtual_node)
                self.ring.append((server_hash, server))
        self.ring.sort() 

    def hash_server(self, server):
        """Generate a hash for a server name."""
        return int(hashlib.sha256(server.encode('utf-8')).hexdigest(), 16)

    def get_server(self, key):
        """Get the server responsible for the given key."""
        if not self.ring:
            raise ValueError("Hash ring is empty")
            
        key_hash = self.hash_server(str(key))
        pos = bisect.bisect_right([h for h, _ in self.ring], key_hash)
        if pos == len(self.ring):
            pos = 0
        server = self.ring[pos][1]
        self.server_load[server] += 1
        
        if self.needs_rebalancing():
            self.rebalance()
            
        return server
    
    def needs_rebalancing(self):
        """Check if the ring needs rebalancing based on load distribution."""
        if not self.servers:
            return False
            
        total_load = sum(self.server_load.values())
        if total_load == 0:
            return False
            
        avg_load = total_load / len(self.servers)
        
        for server_load in self.server_load.values():
            if server_load > 0: 
                deviation = abs(server_load - avg_load) / avg_load
                if deviation > self.load_threshold:
                    return True
        return False
    
    def add_server(self, server):
        """Add a new server to the ring."""
        if server not in self.servers:
            self.servers.add(server)
            self.populate_ring()
            self.rebalance()

    def remove_server(self, server):
        """Remove a server from the ring."""
        if server in self.servers:
            self.servers.remove(server)
            self.populate_ring()
            self.rebalance()
            del self.server_load[server]
    

    def get_neighbors(self, key):
        """Get neighbors of the key's server in the ring."""
        if not self.ring:
            return []
            
        key_hash = self.hash_server(str(key))
        pos = bisect.bisect_right([h for h, _ in self.ring], key_hash)
        if pos == len(self.ring):
            pos = 0

        neighbors = []
        seen_servers = set()
        current_pos = pos
        
        while len(neighbors) < 2 and len(seen_servers) < len(self.servers):
            server = self.ring[current_pos][1]
            if server not in seen_servers:
                neighbors.append(server)
                seen_servers.add(server)
            current_pos = (current_pos + 1) % len(self.ring)

        return neighbors
    
    def rebalance(self):
        """Rebalance the load across servers."""
        if not self.servers:
            return
            
        total_load = sum(self.server_load.values())
        target_load = total_load / len(self.servers)
        
        overloaded = [s for s in self.servers 
                     if self.server_load[s] > target_load * (1 + self.load_threshold)]
        underloaded = [s for s in self.servers 
                      if self.server_load[s] < target_load * (1 - self.load_threshold)]
        
        for server in overloaded:
            while (self.server_load[server] > target_load * (1 + self.load_threshold) 
                   and underloaded):
                target_server = min(underloaded, 
                                  key=lambda s: self.server_load[s])
                
                moved_load = self._move_virtual_nodes(server, target_server)
                self.server_load[server] -= moved_load
                self.server_load[target_server] += moved_load
                
                if self.server_load[target_server] >= target_load:
                    underloaded.remove(target_server)

    def _move_virtual_nodes(self, source, target, num_nodes=1):
        """Move virtual nodes from source to target server."""
        source_nodes = [(h, s) for h, s in self.ring if s == source]
        moved_load = 0
        
        if source_nodes:
            nodes_to_move = random.sample(source_nodes, 
                                        min(num_nodes, len(source_nodes)))
            for node in nodes_to_move:
                self.ring.remove(node)
                new_hash = self.hash_server(f"{target}:{random.randint(0, 1000)}")
                self.ring.append((new_hash, target))
                moved_load += 1
                
            self.ring.sort()
        
        return moved_load

    def get_load_distribution(self):
        """Get the current load distribution across servers."""
        return dict(self.server_load)

    def get_server_status(self):
        """Get detailed status of all servers."""
        status = {}
        for server in self.servers:
            virtual_nodes = sum(1 for _, s in self.ring if s == server)
            status[server] = {
                'load': self.server_load[server],
                'virtual_nodes': virtual_nodes,
                'neighbors': self.get_neighbors(server)
            }
        return status

if __name__ == "__main__":
    servers = [f'9001', '9002', '9003', '9004', '9005']
    hash_ring = HashRing(servers)

    test_keys = [f'key{i}' for i in range(20)]
    for key in test_keys:
        server = hash_ring.get_server(key)
        print(f"Key '{key}' is assigned to server: {server}")
        neighbors = hash_ring.get_neighbors(key)
        print(f"Backup servers for '{key}': {neighbors}")

    print("\nLoad distribution:")
    print(hash_ring.get_load_distribution())

    print("\nServer status:")
    print(hash_ring.get_server_status())