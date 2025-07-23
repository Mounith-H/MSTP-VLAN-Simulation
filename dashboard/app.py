import streamlit as st
import requests
import networkx as nx
import matplotlib.pyplot as plt
import sys
import os

# Add the parent directory to the Python path to import config.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Ip_address, Port_Number

# ---- CONFIGURATION ----
# Dynamically create NODES from config.py
node_ids = sorted(Ip_address.keys())
NODES = [
    (node_id, f"http://{Ip_address[node_id]}:{Port_Number[node_id]}/status")
    for node_id in node_ids
]

st.title("MSTP VLAN Simulation Dashboard")

# Fetch status from all nodes
def fetch_status():
    statuses = {}
    for node_id, url in NODES:
        try:
            resp = requests.get(url, timeout=2)
            if resp.status_code == 200:
                statuses[node_id] = resp.json()
            else:
                statuses[node_id] = None
        except Exception as e:
            statuses[node_id] = None
    return statuses

statuses = fetch_status()

# Show connection status
def connection_status():
    st.header("Connection Status")
    for node_id, url in NODES:
        if statuses[node_id] is not None:
            st.success(f"{node_id} reachable")
        else:
            st.error(f"{node_id} unreachable")

connection_status()

# Collect all VLANs
all_vlans = set()
for node_status in statuses.values():
    if node_status:
        all_vlans.update(node_status['vlans'].keys())

# Visualize MST tree for each VLAN
def draw_vlan_graph(vlan_id):
    G = nx.Graph()
    # Add nodes
    for node_id, _ in NODES:
        G.add_node(node_id)
    # Add edges with port state as edge attribute
    for node_id, node_status in statuses.items():
        if not node_status:
            continue
        vlan_ports = node_status['vlans'].get(vlan_id, {})
        for neighbor, state in vlan_ports.items():
            # Add edge with port state (from node_id to neighbor)
            G.add_edge(node_id, neighbor, state=state)
    # Draw
    pos = nx.spring_layout(G)
    edge_colors = []
    edge_styles = []
    for u, v, d in G.edges(data=True):
        # Use the most severe state if edges are bidirectional
        states = []
        if 'state' in d:
            states.append(d['state'])
        if 'state' in G.get_edge_data(v, u, default={}):
            states.append(G.get_edge_data(v, u)['state'])
        if 'root' in states:
            edge_colors.append('green')
            edge_styles.append('solid')
        elif 'designated' in states:
            edge_colors.append('blue')
            edge_styles.append('solid')
        elif 'blocked' in states:
            edge_colors.append('red')
            edge_styles.append('dashed')
        else:
            edge_colors.append('gray')
            edge_styles.append('dotted')
    plt.figure(figsize=(5, 4))
    nx.draw_networkx_nodes(G, pos, node_color='lightblue', node_size=800)
    for style in set(edge_styles):
        idxs = [i for i, s in enumerate(edge_styles) if s == style]
        edges = [list(G.edges)[i] for i in idxs]
        color = edge_colors[idxs[0]] if idxs else 'gray'
        nx.draw_networkx_edges(G, pos, edgelist=edges, edge_color=color, style=style, width=2)
    nx.draw_networkx_labels(G, pos, font_size=14)
    plt.title(f"VLAN {vlan_id} MST Tree")
    plt.axis('off')
    st.pyplot(plt)
    plt.close()

st.header("MST Trees by VLAN")
for vlan_id in sorted(all_vlans):
    draw_vlan_graph(vlan_id) 