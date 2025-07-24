# Network Configuration File

# --- LOGGING CONFIGURATION ---
# Set to True to display the full UUID in the dashboard log for debugging.
# Set to False for a cleaner, more user-friendly log view.
SHOW_UUID_IN_LOG = False

# --- START OF THE CONFIGURATION ---
# Number of nodes in the network
Number_of_nodes = 3

# IP addresses of all nodes
Ip_address = {
    "A": "127.0.0.1",
    "B": "127.0.0.1", 
    "C": "127.0.0.1",
}

# Port numbers for all nodes
Port_Number = {
    "A": 5000,
    "B": 5001,
    "C": 5002,
}

# Links between nodes (format: "Node1:Node2")
# This defines the physical connections
Link_connected = [
    "A:B",
    "B:C", 
    "C:A",
]

# VLAN IDs in the network
VLANS = [10, 20]

# VLAN assignments to links.
# We will make BOTH VLANs a full triangle to force MSTP to block a port on each.

Vlan10 = [
    "A:B",
    "B:C",
    "C:A",
]

Vlan20 = [
    "A:B",
    "B:C",
    "C:A",
]

# --- END OF THE CONFIGURATION ---

# Helper functions to get configuration data
def get_node_urls():
    """Returns a dictionary mapping node IDs to their URLs"""
    return {node_id: f"http://{Ip_address[node_id]}:{Port_Number[node_id]}" for node_id in Ip_address}

def get_neighbors_for_node(node_id):
    """Returns list of (neighbor_id, neighbor_url) for a given node"""
    neighbors = []
    node_urls = get_node_urls()
    
    for link in Link_connected:
        if ":" in link:
            node1, node2 = link.split(":")
            if node1 == node_id:
                neighbors.append((node2, node_urls[node2]))
            elif node2 == node_id:
                neighbors.append((node1, node_urls[node1]))
    
    return neighbors

def get_vlan_links(vlan_id):
    """Returns list of links for a specific VLAN"""
    if vlan_id == 10:
        return Vlan10
    elif vlan_id == 20:
        return Vlan20
    return []

def get_all_vlan_links():
    """Returns dictionary mapping VLAN IDs to their links"""
    return {
        10: Vlan10,
        20: Vlan20
    }

def is_link_in_vlan(vlan_id, node1, node2):
    """Check if a link between two nodes is part of a specific VLAN"""
    link1 = f"{node1}:{node2}"
    link2 = f"{node2}:{node1}"
    vlan_links = get_vlan_links(vlan_id)
    return link1 in vlan_links or link2 in vlan_links

def get_vlan_neighbors_for_node(node_id, vlan_id):
    """Returns list of (neighbor_id, neighbor_url) for a given node that are in the specified VLAN"""
    all_neighbors = get_neighbors_for_node(node_id)
    vlan_neighbors = []
    
    for neighbor_id, neighbor_url in all_neighbors:
        if is_link_in_vlan(vlan_id, node_id, neighbor_id):
            vlan_neighbors.append((neighbor_id, neighbor_url))
    
    return vlan_neighbors