import threading
import time
import sys
import argparse
from mstp.network import NetworkNode
from mstp.server import start_server
import config

def run_node(node_id):
    """Initializes and runs a single node."""
    if node_id not in config.Ip_address:
        print(f"Error: Node ID '{node_id}' not found in config.py")
        sys.exit(1)

    port = config.Port_Number[node_id]
    ip_address = config.Ip_address[node_id]
    vlan_ids = config.VLANS
    neighbors = config.get_neighbors_for_node(node_id)
    
    print("=" * 50)
    print(f"Starting Node {node_id} on {ip_address}:{port}")
    print("=" * 50)
    
    node = NetworkNode(node_id, vlan_ids, neighbors)
    
    server_thread = threading.Thread(target=start_server, args=(node, port), daemon=True)
    server_thread.start()
    
    node.start_bpdu_loop()
    
    print(f"Node {node_id} is running. Press Ctrl+C to stop.")
    print("-" * 50)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\nShutting down Node {node_id}...")
        node.stop()
        sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a single MSTP network node.")
    parser.add_argument("node_id", type=str, help="The ID of the node to run (e.g., A, B, C).")
    args = parser.parse_args()
    
    run_node(args.node_id.upper())