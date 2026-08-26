# Dynamo-Inspired Distributed Key-Value Store

A distributed key-value store inspired by Amazon Dynamo, implementing **eventual consistency**, **consistent hashing**, and **CRDT-based conflict resolution**, developed for the Large-Scale Distributed Systems (SDLE) course at [FEUP](https://www.fe.up.pt/).

## Overview

The system replicates data across multiple nodes using a hash ring for partitioning and supports concurrent operations without coordination, resolving conflicts automatically using CRDTs (Conflict-free Replicated Data Types).

## Features

- **Consistent hashing** — scalable data partitioning across nodes via a hash ring; nodes can join and leave with minimal data movement
- **Replication & eventual consistency** — writes are propagated to multiple replicas; all replicas converge without coordination
- **CRDT-based conflict resolution** — PN-Counters, Add-Wins Observed-Remove Sets (AWOR-Set), and a shopping list CRDT guarantee strong eventual consistency
- **Client–proxy–server architecture** — clients interact with a proxy layer that routes requests to the correct nodes and handles fault tolerance
- **Concurrent operation support** — multiple clients can read and write simultaneously without locking

## Architecture

```
Client(s) ──► Proxy ──► Node ring (consistent hashing)
                              │
                    Replication to N nodes
                    CRDT merge on conflict
```

## How to Run

### Prerequisites

Install Python 3.x and dependencies:

```bash
cd src
pip3 install -r requirements.txt
```

### Start the system

```bash
./startup.sh
```

### Run a client

```bash
python3 client.py
```

Multiple clients can run simultaneously in separate terminals.

## Group

- João Sousa (up202106996)
- José Oliveira (up202108764)
- Alexandre Correia (up202007042)
