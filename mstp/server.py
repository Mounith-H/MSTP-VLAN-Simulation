

from flask import Flask, request, jsonify
import sys, os

# Corrected path handling for robust imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = Flask(__name__)
node = None # Global node instance

@app.route('/bpdu', methods=['POST'])
def receive_bpdu():
    data = request.json
    if node:
        node.receive_bpdu(data['vlan_id'], data['from'], data['bpdu'])
        return jsonify({'status': 'received'}), 200
    return jsonify({'error': 'Node not initialized'}), 400

@app.route('/initiate-transfer', methods=['POST'])
def initiate_transfer():
    data = request.json
    if node:
        # The send_transfer function now handles creating the unique ID
        node.send_transfer(
            dst_id=data['dst'],
            payload="data",
            file_size_mb=data['file_size_mb'],
            vlan_id=data['vlan_id'],
            global_port_states=data['global_port_states']
        )
        return jsonify({'status': 'transfer initiated'}), 200
    return jsonify({'error': 'Node not initialized'}), 400

@app.route('/transfer', methods=['POST'])
def receive_transfer_hop():
    data = request.json
    if node:
        # All subsequent calls must pass the unique transfer_id
        node.receive_transfer(
            transfer_id=data['transfer_id'],
            src=data['src'],
            dst=data['dst'],
            payload=data['payload'],
            file_size_mb=data['file_size_mb'],
            vlan_id=data['vlan_id'],
            hops=data['hops'],
            path=data['path']
        )
        return jsonify({'status': 'hop received'}), 200
    return jsonify({'error': 'Node not initialized'}), 400

@app.route('/complete-transfer', methods=['POST'])
def complete_transfer():
    data = request.json
    if node:
        # Must use the transfer_id to identify which transfer is complete
        node.complete_transfer(data['transfer_id'])
        return jsonify({'status': 'completion noted'}), 200
    return jsonify({'error': 'Node not initialized'}), 400

@app.route('/fail-transfer', methods=['POST'])
def fail_transfer():
    data = request.json
    if node:
        # Must use the transfer_id to identify which transfer failed
        node.fail_transfer(data['transfer_id'])
        return jsonify({'status': 'failure noted'}), 200
    return jsonify({'error': 'Node not initialized'}), 400

@app.route('/status', methods=['GET'])
def status():
    if not node:
        return jsonify({'error': 'Node not initialized'}), 400
    
    # The get_transfer_status now returns the entire dict with UUIDs as keys
    # The UI will need to handle this new structure, but the backend is now correct.
    return jsonify({
        'node_id': node.node_id,
        'vlans': {vlan_id: vlan.get_port_states() for vlan_id, vlan in node.vlans.items()},
        'transfers': node.get_transfer_status() 
    })

def start_server(network_node, port):
    global node
    node = network_node
    # Use a specific IP to bind to, as 0.0.0.0 can sometimes be inconsistent.
    # We will get this from the node's own config.
    import config
    host_ip = config.Ip_address.get(node.node_id, '127.0.0.1')
    app.run(host=host_ip, port=port, threaded=True)