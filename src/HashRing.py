import hashlib
import bisect

class HashRing:
    def __init__(self, servers):
        self.servers = sorted(servers)  # Sort servers in order for efficient search
        self.ring = []  # The actual hash ring
        self.populate_ring()

    def populate_ring(self):
        """Populate the hash ring using a simple hash of server names."""
        for server in self.servers:
            server_hash = self.hash_server(server)
            self.ring.append((server_hash, server))
        # Sorting the ring is only necessary here as we populate the ring
        self.ring.sort()  # Ensure the ring is sorted by hash values

    def hash_server(self, server):
        """Generate a hash for a server name."""
        return int(hashlib.sha256(server.encode('utf-8')).hexdigest(), 16)

    def get_server(self, key):
        """Get the server responsible for the given key."""
        key_hash = self.hash_server(key)
        # Bisect to find the correct server position
        pos = bisect.bisect_right([h for h, _ in self.ring], key_hash)
        if pos == len(self.ring):  # If it exceeds the ring, wrap around to the first server
            pos = 0
        return self.ring[pos][1]  # Return the server's name

    def get_neighbors(self, key, num_neighbors=2):
        """Get N neighbors of the key's server in the ring."""
        server = self.get_server(key)
        idx = self.servers.index(server)
        neighbors = [self.servers[(idx + i) % len(self.servers)] for i in range(1, num_neighbors + 1)]
        return neighbors

if __name__ == "__main__":
    servers = ['server1', 'server2', 'server3', 'server4']
    hash_ring = HashRing(servers)

    # Example keys
    keys = ['key1', 'key2', 'key3', 'key4', 'key5']

    for key in keys:
        server = hash_ring.get_server(key)
        print(f"Key '{key}' is assigned to server: {server}")