import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the parent directory to the Python path to import the main app and config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mstp.server import app, start_server
from config import Current_Node_id, Port_Number

class TestServer(unittest.TestCase):

    def setUp(self):
        """Set up a test client for the Flask application."""
        app.config['TESTING'] = True
        self.client = app.test_client()

    @patch('mstp.server.node')  # Mock the global node object
    def test_receive_bpdu_success(self, mock_node):
        """Test that the /bpdu endpoint correctly receives a BPDU."""
        mock_node.receive_bpdu = MagicMock()

        bpdu_data = {
            'vlan_id': 10,
            'from': 'B',
            'bpdu': {'root_id': 'A', 'bridge_id': 'B', 'cost': 10}
        }

        response = self.client.post('/bpdu', json=bpdu_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {'status': 'received'})
        mock_node.receive_bpdu.assert_called_once_with(10, 'B', bpdu_data['bpdu'])

    def test_receive_bpdu_no_node(self):
        """Test /bpdu endpoint when the node is not initialized."""
        with patch('mstp.server.node', None):
            bpdu_data = {'vlan_id': 10, 'from': 'B', 'bpdu': {}}
            response = self.client.post('/bpdu', json=bpdu_data)
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json, {'error': 'Node not initialized'})

    @patch('mstp.server.node')
    def test_status_endpoint(self, mock_node):
        """Test the /status endpoint to ensure it returns the correct node status."""
        mock_node.node_id = 'A'
        mock_node.vlans = [10, 20]
        mock_node.get_vlan_port_states.side_effect = [
            {'B': 'root', 'C': 'designated'},  # VLAN 10
            {'B': 'blocked', 'C': 'root'}      # VLAN 20
        ]
        mock_node.get_transfer_status.return_value = []

        response = self.client.get('/status')
        self.assertEqual(response.status_code, 200)
        expected_json = {
            'node_id': 'A',
            'vlans': {
                '10': {'B': 'root', 'C': 'designated'},
                '20': {'B': 'blocked', 'C': 'root'}
            },
            'transfers': []
        }
        # The JSON response will have string keys for VLANs
        self.assertEqual(response.json['node_id'], expected_json['node_id'])
        self.assertEqual(response.json['transfers'], expected_json['transfers'])
        self.assertDictEqual(response.json['vlans'], expected_json['vlans'])

    def test_start_server_initialization(self):
        """Test that the server is initialized with the correct port from config."""
        mock_network_node = MagicMock()
        with patch('mstp.server.app.run') as mock_run:
            start_server(mock_network_node)
            expected_port = Port_Number[Current_Node_id]
            mock_run.assert_called_once_with(host='0.0.0.0', port=expected_port)

if __name__ == '__main__':
    unittest.main()
