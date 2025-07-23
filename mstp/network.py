import sys
import os
import uuid
import requests
import threading
import time

# Add parent directory to path to allow direct import of modules from other project directories
# This is crucial for the execution environment.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from mstp.vlan import VLAN
import config

TRANSFER_SPEED_MBPS = 5

class NetworkNode:
    def __init__(self, node_id, vlan_ids, neighbors):
        self.node_id = node_id
        self.neighbors = neighbors
        self.vlans = {}
        self.transfer_status = {}
        self.transfer_lock = threading.Lock()
        self._stop_event = threading.Event()

        for vlan_id in vlan_ids:
            vlan_neighbors = [n_id for n_id, _ in neighbors if config.is_link_in_vlan(vlan_id, node_id, n_id)]
            self.vlans[vlan_id] = VLAN(vlan_id, self.node_id, vlan_neighbors)

    def _bpdu_sender_loop(self):
        time.sleep(4)
        while not self._stop_event.is_set(): self.send_bpdus(); time.sleep(2)
    def start_bpdu_loop(self):
        threading.Thread(target=self._bpdu_sender_loop, daemon=True).start()
    def stop(self): self._stop_event.set()

    def receive_bpdu(self, vlan_id, port, bpdu):
        if vlan_id in self.vlans:
            self.vlans[vlan_id].receive_bpdu(port, bpdu)

    def send_bpdus(self):
        for vlan_id, vlan in self.vlans.items():
            bpdu = vlan.mstp.generate_bpdu()
            for neighbor_id, neighbor_url in self.neighbors:
                if config.is_link_in_vlan(vlan_id, self.node_id, neighbor_id):
                    data = {'vlan_id': vlan_id, 'from': self.node_id, 'bpdu': bpdu}
                    try:
                        requests.post(f'{neighbor_url}/bpdu', json=data, timeout=1.5)
                    except requests.RequestException:
                        pass # Ignore nodes that are down

    def find_mstp_path(self, dst_id, vlan_id, global_port_states=None):
        if not global_port_states: return None
        vlan_id_str = str(vlan_id)
        adj, nodes = {}, list(global_port_states.keys())
        for node in nodes:
            port_states = global_port_states.get(node, {}).get(vlan_id_str, {})
            for neighbor, state in port_states.items():
                if neighbor in nodes:
                    neighbor_state = global_port_states.get(neighbor, {}).get(vlan_id_str, {}).get(node, 'blocked')
                    if state != 'blocked' and neighbor_state != 'blocked':
                        if node not in adj: adj[node] = []
                        if neighbor not in adj: adj[neighbor] = []
                        adj[node].append(neighbor)
                        adj[neighbor].append(node)
        if dst_id not in adj: return None
        from collections import deque
        q, visited = deque([[self.node_id]]), {self.node_id}
        while q:
            path = q.popleft()
            node = path[-1]
            if node == dst_id: return path
            for neighbor in adj.get(node, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    q.append(path + [neighbor])
        return None

    def _cleanup_transfer_status(self, transfer_id):
        time.sleep(15)
        with self.transfer_lock:
            self.transfer_status.pop(transfer_id, None)

    def send_transfer(self, dst_id, payload, file_size_mb, vlan_id, global_port_states):
        transfer_id = str(uuid.uuid4())
        path = self.find_mstp_path(dst_id, vlan_id, global_port_states)
        if not path or len(path) < 2:
            with self.transfer_lock:
                self.transfer_status[transfer_id] = {'status': 'no path', 'path': None, 'src': self.node_id, 'dst': dst_id}
            threading.Thread(target=self._cleanup_transfer_status, args=(transfer_id,), daemon=True).start()
            return

        with self.transfer_lock:
            self.transfer_status[transfer_id] = {'status': 'transferring', 'progress': 0, 'hops': 0, 'path': path, 'vlan_id': vlan_id, 'src': self.node_id, 'dst': dst_id}

        def forward_task():
            next_node_id = path[1]
            next_node_url = next((url for nid, url in self.neighbors if nid == next_node_id), None)
            if not next_node_url: self.fail_transfer(transfer_id); return
            data = {'transfer_id': transfer_id, 'src': self.node_id, 'dst': dst_id, 'payload': payload, 'file_size_mb': file_size_mb, 'vlan_id': vlan_id, 'hops': 1, 'path': path}
            try: requests.post(f'{next_node_url}/transfer', json=data, timeout=10)
            except Exception: self.fail_transfer(transfer_id)
        threading.Thread(target=forward_task, daemon=True).start()

    def receive_transfer(self, transfer_id, src, dst, payload, file_size_mb, vlan_id, hops, path):
        """
        Receives a transfer. Intermediate hops will now create a *transient*
        status to allow the UI to track animation, which is cleaned up shortly after.
        """
        # Logic for the Final Destination Node (remains the same)
        if self.node_id == dst:
            def final_hop_task():
                # Simulate download time
                time.sleep(file_size_mb / TRANSFER_SPEED_MBPS)
                # Notify the original source that the transfer is complete
                source_node_url = f"http://{config.Ip_address[src]}:{config.Port_Number[src]}"
                try: requests.post(f'{source_node_url}/complete-transfer', json={'transfer_id': transfer_id}, timeout=5)
                except Exception: pass # Source node might be down
            threading.Thread(target=final_hop_task, daemon=True).start()
        
        # Logic for Intermediate Hops (This is the corrected part)
        else:
            # 1. Create a transient status entry for this hop on THIS node.
            # This is the snapshot the UI needs to see the current hop number.
            with self.transfer_lock:
                self.transfer_status[transfer_id] = {
                    'status': 'forwarded', # A specific status for this state
                    'progress': int((hops / (len(path) - 1)) * 100),
                    'hops': hops,
                    'path': path,
                    'src': src,
                    'dst': dst
                }
            
            # 2. Immediately start a cleanup timer for this transient entry.
            # This prevents the stale state bug from ever returning.
            # The 5-second delay is more than enough for the UI to poll the status.
            threading.Thread(target=self._cleanup_transfer_status, args=(transfer_id,), daemon=True).start()
            
            # 3. Start the task to forward the packet to the next hop.
            def forward_task():
                # Validate the path to prevent errors
                if hops >= len(path) -1: self.fail_transfer(transfer_id); return

                next_node_id = path[hops + 1]
                next_node_url = next((url for nid, url in self.neighbors if nid == next_node_id), None)
                if not next_node_url: self.fail_transfer(transfer_id); return

                # Prepare and send the data to the next hop
                data = {'transfer_id': transfer_id, 'src': src, 'dst': dst, 'payload': payload, 'file_size_mb': file_size_mb, 'vlan_id': vlan_id, 'hops': hops + 1, 'path': path}
                try:
                    requests.post(f'{next_node_url}/transfer', json=data, timeout=10)
                except Exception:
                    # If forwarding fails, notify the original source node
                    source_node_url = f"http://{config.Ip_address[src]}:{config.Port_Number[src]}"
                    try: requests.post(f'{source_node_url}/fail-transfer', json={'transfer_id': transfer_id}, timeout=5)
                    except Exception: pass
            
            threading.Thread(target=forward_task, daemon=True).start()

    def complete_transfer(self, transfer_id):
        with self.transfer_lock:
            if transfer_id in self.transfer_status:
                self.transfer_status[transfer_id]['status'] = 'done'; self.transfer_status[transfer_id]['progress'] = 100
                threading.Thread(target=self._cleanup_transfer_status, args=(transfer_id,), daemon=True).start()

    def fail_transfer(self, transfer_id):
        with self.transfer_lock:
            if transfer_id in self.transfer_status and self.transfer_status[transfer_id]['status'] != 'done':
                self.transfer_status[transfer_id]['status'] = 'failed'
                threading.Thread(target=self._cleanup_transfer_status, args=(transfer_id,), daemon=True).start()

    def get_transfer_status(self):
        with self.transfer_lock: return dict(self.transfer_status)
    def get_vlan_port_states(self, vlan_id):
        if vlan_id in self.vlans: return self.vlans[vlan_id].get_port_states()
        return None
        