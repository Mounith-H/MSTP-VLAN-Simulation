import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the parent directory to the Python path to import the main app and config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import main
from config import Current_Node_id, VLANS, get_neighbors_for_node

class TestMain(unittest.TestCase):

    @patch('main.NetworkNode')
    @patch('main.start_server')
    @patch('main.threading.Thread')
    @patch('main.bpdu_sender')
    def test_main_initialization(self, mock_bpdu_sender, mock_thread, mock_start_server, mock_network_node):
        """Test that the main function initializes the node and server correctly."""
        # Mock the return value of NetworkNode
        mock_node_instance = MagicMock()
        mock_network_node.return_value = mock_node_instance

        # Run the main function
        main()

        # Get expected values from config
        expected_node_id = Current_Node_id
        expected_vlans = VLANS
        expected_neighbors = get_neighbors_for_node(expected_node_id)

        # Assert that NetworkNode was called correctly
        mock_network_node.assert_called_once_with(expected_node_id, expected_vlans, expected_neighbors)

        # Assert that the server thread was created and started
        mock_thread.assert_called_once_with(target=mock_start_server, args=(mock_node_instance,), daemon=True)
        mock_thread.return_value.start.assert_called_once()

        # Assert that the BPDU sender was called
        mock_bpdu_sender.assert_called_once_with(mock_node_instance)

if __name__ == '__main__':
    unittest.main()