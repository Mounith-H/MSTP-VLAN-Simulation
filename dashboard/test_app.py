import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the parent directory to the Python path to import the main app and config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dashboard.app import fetch_status, NODES
from config import Ip_address, Port_Number

class TestDashboard(unittest.TestCase):

    @patch('requests.get')
    def test_fetch_status_success(self, mock_get):
        """Test that fetch_status correctly processes a successful response."""
        # Mock a successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_get.return_value = mock_response

        # Call the function
        statuses = fetch_status()

        # Assert that the status is correctly parsed
        for node_id, _ in NODES:
            self.assertEqual(statuses[node_id], {"status": "ok"})

    @patch('requests.get')
    def test_fetch_status_error(self, mock_get):
        """Test that fetch_status handles a failed response."""
        # Mock a failed response
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        # Call the function
        statuses = fetch_status()

        # Assert that the status is None for all nodes
        for node_id, _ in NODES:
            self.assertIsNone(statuses[node_id])

    @patch('requests.get', side_effect=Exception("Connection error"))
    def test_fetch_status_exception(self, mock_get):
        """Test that fetch_status handles exceptions during the request."""
        # Call the function
        statuses = fetch_status()

        # Assert that the status is None for all nodes
        for node_id, _ in NODES:
            self.assertIsNone(statuses[node_id])

    def test_nodes_are_configured_correctly(self):
        """Test that the NODES list is created correctly from the config."""
        # Recreate the NODES list from the config to compare
        expected_nodes = []
        for node_id in sorted(Ip_address.keys()):
            url = f"http://{Ip_address[node_id]}:{Port_Number[node_id]}/status"
            expected_nodes.append((node_id, url))
        
        # Assert that the generated NODES list matches the expected one
        self.assertEqual(NODES, expected_nodes)

if __name__ == '__main__':
    unittest.main()
