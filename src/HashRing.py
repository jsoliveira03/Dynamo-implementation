import hashlib
import bisect

class HashRing:
    def __init__(self, servers):
        self.servers = servers
        self.ring = []
        self.node_map = {}
        self.build_ring()

    def _hash(self, key):
        """Create a hash value for the given key"""
        # Ensure that the key (server) is converted to a string before hashing
        key_str = str(key)  # Convert the key to string
        return int(hashlib.md5(key_str.encode('utf-8')).hexdigest(), 16)

    def build_ring(self):
        """Build the hash ring with each server's hash"""
        for server in self.servers:
            hash_value = self._hash(server)
            self.ring.append(hash_value)
            self.node_map[hash_value] = server
        self.ring.sort()

    def add_server(self, server):
        """Add a server to the ring"""
        hash_value = self._hash(server)
        bisect.insort(self.ring, hash_value)
        self.node_map[hash_value] = server

    def remove_server(self, server):
        """Remove a server from the ring"""
        hash_value = self._hash(server)
        self.ring.remove(hash_value)
        del self.node_map[hash_value]

    def get_server(self, key):
        """Get the server for a given key"""
        if not self.ring:
            return None
        hash_value = self._hash(key)
        idx = bisect.bisect(self.ring, hash_value)
        if idx == len(self.ring):
            idx = 0
        return self.node_map[self.ring[idx]]
