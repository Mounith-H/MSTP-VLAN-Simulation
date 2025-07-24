import sys
import os
import requests
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QMessageBox,
    QHBoxLayout, QPushButton, QComboBox, QGroupBox, QSpinBox, QTextEdit
)
from PyQt5.QtCore import QTimer, Qt
import json
from PyQt5.QtGui import QColor, QPalette
import threading
import time


# Ensure parent directory is in path to import config
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import Ip_address, Port_Number, VLANS, Link_connected, SHOW_UUID_IN_LOG # Add SHOW_UUID_IN_LOG here

# ---- CONFIGURATION ----
NODES = [(node_id, f"http://{Ip_address[node_id]}:{Port_Number[node_id]}/status") for node_id in sorted(Ip_address.keys())]
NODE_URLS = {node_id: url.replace("/status", "") for node_id, url in NODES}
REFRESH_INTERVAL_MS = 1000  # Refresh every 1 second for smoother animation

class MSTPDesktopApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MSTP VLAN Simulation Desktop App")
        self.layout = QVBoxLayout(self)
        
        # --- UI SETUP ---
        self.status_label = QLabel("Fetching node statuses...")
        self.layout.addWidget(self.status_label)

        self.vlan_graph_widget = VlanGraphWidget()
        self.layout.addWidget(self.vlan_graph_widget)

        self.transfer_group = QGroupBox("Data Transfer Simulation")
        self.transfer_layout = QHBoxLayout()
        self.src_combo = QComboBox()
        self.dst_combo = QComboBox()
        self.vlan_combo = QComboBox()
        self.file_size_spin = QSpinBox()
        self.file_size_spin.setRange(1, 1000)
        self.file_size_spin.setValue(10)
        self.file_size_spin.setSuffix(" MB")
        self.transfer_btn = QPushButton("Send Data")

        # Populate dropdowns
        node_ids = [node_id for node_id, _ in NODES]
        self.src_combo.addItems(node_ids)
        self.dst_combo.addItems(node_ids)
        self.vlan_combo.addItems([str(vlan) for vlan in VLANS])
        
        self.transfer_layout.addWidget(QLabel("Source:"))
        self.transfer_layout.addWidget(self.src_combo)
        self.transfer_layout.addWidget(QLabel("Destination:"))
        self.transfer_layout.addWidget(self.dst_combo)
        self.transfer_layout.addWidget(QLabel("VLAN:"))
        self.transfer_layout.addWidget(self.vlan_combo)
        self.transfer_layout.addWidget(QLabel("File Size:"))
        self.transfer_layout.addWidget(self.file_size_spin)
        self.transfer_layout.addWidget(self.transfer_btn)
        self.transfer_group.setLayout(self.transfer_layout)
        self.layout.addWidget(self.transfer_group)
        
        self.log_window = QTextEdit()
        self.log_window.setReadOnly(True)
        self.layout.addWidget(self.log_window)

        # --- STATE & TIMERS ---
        self.statuses = {}
        self.graph_layouts = {}
        self.prev_transfer_logs = set()

        # Animation state
        self.anim_path = []
        self.anim_hop = 0
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh)
        self.timer.start(REFRESH_INTERVAL_MS)
        
        self.transfer_btn.clicked.connect(self.initiate_transfer)

        self.refresh() # Initial refresh

    def fetch_status(self):
        statuses = {}
        for node_id, url in NODES:
            try:
                resp = requests.get(url, timeout=0.5)
                statuses[node_id] = resp.json() if resp.status_code == 200 else None
            except requests.RequestException:
                statuses[node_id] = None
        return statuses

    def refresh(self):
        self.statuses = self.fetch_status()
        
        status_msgs = [f"<span style='color:green'>{node_id} reachable</span>" if self.statuses.get(node_id) else f"<span style='color:red'>{node_id} unreachable</span>" for node_id, _ in NODES]
        self.status_label.setText(" | ".join(status_msgs))
        
        # --- NEW ANIMATION LOGIC ---
        # Find the most recent active transfer to animate
        active_transfer = None
        for node_id, node_status in self.statuses.items():
            if not node_status or 'transfers' not in node_status: continue
            for key, info in node_status['transfers'].items():
                if info.get('status') in ['transferring', 'forwarded']:
                    active_transfer = info
                    break
            if active_transfer: break

        if active_transfer and active_transfer.get('path'):
            self.anim_path = active_transfer['path']
            self.anim_hop = active_transfer.get('hops', 0)
        else:
            # If no active transfers, reset animation
            self.anim_path = []
            self.anim_hop = 0

        # Draw the graph with the current animation state
        vlan_ids = sorted([int(v) for v in VLANS])
        self.vlan_graph_widget.draw_graph(self.statuses, self.graph_layouts, vlan_ids, self.anim_path, self.anim_hop)
        
        self.update_log_window()

    def update_log_window(self):
        """
        Updates the log window, now including the hop count in the final
        success message for a completed transfer.
        """
        for node_id, node_status in self.statuses.items():
            if not node_status or 'transfers' not in node_status:
                continue

            for transfer_key, info in sorted(node_status['transfers'].items()):
                path = info.get('path')
                if not path or node_id != path[0]:
                    continue
                
                status = info.get('status', 'unknown')
                log_identifier = f"{transfer_key}-{status}"

                if log_identifier not in self.prev_transfer_logs:
                    if status == 'done':
                        # --- START OF THE HOP COUNT FIX ---
                        path_str = " -> ".join(path)
                        hop_count = 0
                        # Calculate hop count, ensuring the path is valid
                        if path and len(path) > 1:
                            hop_count = len(path) - 1

                        # Updated log message format to include the hop count
                        base_log_msg = (
                            f"[{time.strftime('%H:%M:%S')}] SUCCESS: Transfer on VLAN {info.get('vlan_id')} complete. "
                            f"Path: {path_str} ({hop_count} hops)"
                        )
                        # --- END OF THE HOP COUNT FIX ---
                        
                        # Conditionally append the UUID based on the config setting
                        if SHOW_UUID_IN_LOG:
                            full_log = f"{base_log_msg} (UUID: {transfer_key})"
                        else:
                            full_log = base_log_msg
                        
                        self.log_window.append(full_log)
                        self.prev_transfer_logs.add(log_identifier)

                    elif status == 'no path' or status == 'failed':
                        src = info.get('src', 'N/A')
                        dst = info.get('dst', 'N/A')
                        transfer_desc = f"{src}->{dst}"
                        
                        full_log = f"[{time.strftime('%H:%M:%S')}] FAILED: Transfer {transfer_desc}. Status: {status.replace('_', ' ').capitalize()}"
                        self.log_window.append(full_log)
                        self.prev_transfer_logs.add(log_identifier)

    def initiate_transfer(self):
        """
        Validates node statuses before initiating a data transfer to prevent
        race conditions where pathfinding would fail on an incomplete network map.
        """
        src = self.src_combo.currentText()
        dst = self.dst_combo.currentText()
        if src == dst:
            QMessageBox.warning(self, "Invalid Transfer", "Source and destination must be different.")
            return

        # --- START OF THE FIX ---
        # 1. Check if all nodes are currently reachable before proceeding.
        unreachable_nodes = [node_id for node_id, status in self.statuses.items() if status is None]
        if unreachable_nodes:
            msg = f"Cannot initiate transfer because the following nodes are unreachable: {', '.join(unreachable_nodes)}.\n\nPlease wait a moment for them to connect."
            QMessageBox.critical(self, "Network State Incomplete", msg)
            return
        # --- END OF THE FIX ---

        # Prepare payload for the transfer request
        payload = {
            "src": src,
            "dst": dst,
            "vlan_id": int(self.vlan_combo.currentText()),
            "file_size_mb": self.file_size_spin.value(),
            "global_port_states": self.get_global_port_states()
        }
        
        try:
            # Use the new, correct endpoint for starting a transfer
            url = NODE_URLS[src] + "/initiate-transfer" 
            requests.post(url, json=payload, timeout=2)
            self.log_window.append(f"[{time.strftime('%H:%M:%S')}] Initiating transfer {src}->{dst} on VLAN {payload['vlan_id']}...")
        except Exception as e:
            QMessageBox.warning(self, "Transfer Failed", f"Failed to initiate transfer: {e}")
            
    def get_global_port_states(self):
        # The pathfinder needs the state of ALL VLANs on ALL nodes to work correctly.
        global_states = {}
        for node_id, node_status in self.statuses.items():
            if node_status and 'vlans' in node_status:
                # Store the entire 'vlans' dictionary for this node
                global_states[node_id] = node_status['vlans']
        return global_states

    def refresh(self):
        self.statuses = self.fetch_status()
        
        status_msgs = [f"<span style='color:green'>{node_id} reachable</span>" if self.statuses.get(node_id) else f"<span style='color:red'>{node_id} unreachable</span>" for node_id, _ in NODES]
        self.status_label.setText(" | ".join(status_msgs))
        
        # ---- START OF FINAL UI FIX ----
        # Find the most recent active transfer to animate
        active_transfer = None
        source_of_active_transfer = None
        for node_id, node_status in self.statuses.items():
            if not node_status or 'transfers' not in node_status: continue
            for key, info in node_status['transfers'].items():
                # Animate only if the source node is managing the transfer
                if info.get('status') in ['transferring', 'forwarded'] and info.get('path') and node_id == info['path'][0]:
                    active_transfer = info
                    source_of_active_transfer = node_id
                    break
            if active_transfer: break

        # Update or clear animation state based on findings
        if active_transfer and active_transfer.get('path'):
            self.anim_path = active_transfer['path']
            self.anim_hop = active_transfer.get('hops', 0)
        else:
            # If no active transfers are found, clear the animation state.
            self.anim_path = []
            self.anim_hop = 0
        # ---- END OF FINAL UI FIX ----
            
        vlan_ids = sorted([int(v) for v in VLANS])
        self.vlan_graph_widget.draw_graph(self.statuses, self.graph_layouts, vlan_ids, self.anim_path, self.anim_hop)
        
        self.update_log_window()

class VlanGraphWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.fig, self.ax = plt.subplots(figsize=(5, 4))
        self.canvas = FigureCanvas(self.fig)
        layout = QVBoxLayout(self)
        layout.addWidget(self.canvas)
        # Adjust layout to make space for the legend at the bottom
        self.fig.subplots_adjust(bottom=0.2)
        
    def draw_graph(self, statuses, graph_layouts, vlan_ids, anim_path, anim_hop):
        self.ax.clear()
        G = nx.Graph()
        
        node_ids = list(statuses.keys())
        if not node_ids: return
        
        G.add_nodes_from(node_ids)
        G.add_edges_from([tuple(link.split(':')) for link in Link_connected])
        
        if 'pos' not in graph_layouts:
             graph_layouts['pos'] = nx.spring_layout(G, seed=42)
        pos = graph_layouts['pos']

        edge_colors = {}
        blocked_vlans_on_link = {}

        for u, v in G.edges():
            key = tuple(sorted((u,v)))
            active_vlans = set()
            
            status_u_10 = statuses.get(u, {}).get('vlans', {}).get('10', {}).get(v)
            status_v_10 = statuses.get(v, {}).get('vlans', {}).get('10', {}).get(u)
            if status_u_10 == 'blocked' or status_v_10 == 'blocked':
                blocked_vlans_on_link.setdefault(key, []).append(10)
            elif status_u_10 is not None and status_v_10 is not None:
                active_vlans.add(10)

            status_u_20 = statuses.get(u, {}).get('vlans', {}).get('20', {}).get(v)
            status_v_20 = statuses.get(v, {}).get('vlans', {}).get('20', {}).get(u)
            if status_u_20 == 'blocked' or status_v_20 == 'blocked':
                blocked_vlans_on_link.setdefault(key, []).append(20)
            elif status_u_20 is not None and status_v_20 is not None:
                active_vlans.add(20)

            if len(active_vlans) == 2:
                edge_colors[key] = 'purple'
            elif 10 in active_vlans:
                edge_colors[key] = 'green'
            elif 20 in active_vlans:
                edge_colors[key] = 'blue'
            else:
                edge_colors[key] = 'lightgray'

        for (u, v), color in edge_colors.items():
            nx.draw_networkx_edges(G, pos, edgelist=[(u,v)], edge_color=color, width=4, ax=self.ax)
        
        nx.draw_networkx_nodes(G, pos, node_color='skyblue', node_size=700)
        nx.draw_networkx_labels(G, pos, font_color='white', font_size=12, font_weight='bold')

        for (u, v), blocked_list in blocked_vlans_on_link.items():
            mx = (pos[u][0] + pos[v][0]) / 2
            my = (pos[u][1] + pos[v][1]) / 2
            label = f"Blocked: {', '.join(map(str, sorted(blocked_list)))}"
            self.ax.text(mx, my, label, color='white', ha='center', va='center', 
                         fontsize=8, zorder=10,
                         bbox=dict(facecolor='#d62728', alpha=0.9, pad=2, edgecolor='none'))
        
        if anim_path and anim_hop < len(anim_path):
            current_node = anim_path[anim_hop]
            self.ax.plot(pos[current_node][0], pos[current_node][1], 'o', color='yellow', markersize=18, markeredgecolor='black', zorder=11)
            if len(anim_path) > 1:
                path_edges = list(zip(anim_path, anim_path[1:]))
                # --- START OF THE FIX ---
                # The 'zorder' argument has been removed from the following line as it is not supported.
                nx.draw_networkx_edges(G, pos, edgelist=path_edges, edge_color='#ff8c00', width=5, style='dotted')
                # --- END OF THE FIX ---

        legend_elements = [ plt.Line2D([0], [0], color='green', lw=3, label='VLAN 10 Active'),
                            plt.Line2D([0], [0], color='blue', lw=3, label='VLAN 20 Active'),
                            plt.Line2D([0], [0], color='purple', lw=3, label='Both VLANs Active'),
                            plt.Line2D([0], [0], color='#ff8c00', lw=3, ls='dotted', label='Transfer Path')]
        # --- START OF THE FIX ---
        # Move the legend to the bottom of the figure
        self.ax.legend(handles=legend_elements, loc='lower center', 
                       bbox_to_anchor=(0.5, -0.3), # Position it below the axis
                       ncol=2) # Arrange items in 2 columns
        # --- END OF THE FIX ---
        self.ax.set_title("MSTP VLAN Tree - Active and Blocked Links")
        self.ax.axis('off')
        self.canvas.draw()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MSTPDesktopApp()
    window.show()
    sys.exit(app.exec_())