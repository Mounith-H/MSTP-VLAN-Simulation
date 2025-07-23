import random

class MSTP:
    """
    A corrected and more complete implementation of the Spanning Tree Protocol.
    This version includes path cost in its calculations, which is essential for
    correctly identifying and blocking redundant paths in a network loop.
    """
    PORT_ROOT = 'root'
    PORT_DESIGNATED = 'designated'
    PORT_BLOCKED = 'blocked'

    def __init__(self, bridge_id=None, ports=None):
        # A lower bridge_id is "better" in STP elections
        self.bridge_id = bridge_id
        self.ports = ports or []
        
        # Core state of this bridge
        self.root_id = self.bridge_id
        self.cost_to_root = 0
        self.root_port = None # The port that provides the best path to the root
        
        self.port_states = {port: self.PORT_DESIGNATED for port in self.ports}
        self.received_bpdus = {} # Cache BPDUs from neighbors: {port: bpdu}

    def _create_bpdu(self):
        """Creates the BPDU this bridge will send out on its ports."""
        return {
            'sender_id': self.bridge_id,
            'root_id': self.root_id,
            'cost': self.cost_to_root
        }

    def _is_bpdu_superior(self, bpdu1, bpdu2):
        """Compares two BPDUs to see if bpdu1 is better than bpdu2."""
        if not bpdu2: return True # Anything is better than nothing
        
        # Lower Root ID is always better
        if bpdu1['root_id'] < bpdu2['root_id']: return True
        if bpdu1['root_id'] > bpdu2['root_id']: return False
        
        # If roots are the same, lower cost is better
        if bpdu1['cost'] < bpdu2['cost']: return True
        if bpdu1['cost'] > bpdu2['cost']: return False
        
        # If costs are the same, lower sender ID is the tie-breaker
        if bpdu1['sender_id'] < bpdu2['sender_id']: return True
        
        return False

    def receive_bpdu(self, from_port, received_bpdu):
        """This is the main STP logic engine. Processes a received BPDU and updates state."""
        self.received_bpdus[from_port] = received_bpdu
        
        # 1. Find the best BPDU this bridge knows about (either its own or one it received)
        potential_root_bpdu = self._create_bpdu() # Start by assuming I am the root
        potential_root_port = None

        for port, bpdu in self.received_bpdus.items():
            # Create a prospective BPDU from the neighbor's perspective
            prospective_bpdu = {
                'root_id': bpdu['root_id'],
                'cost': bpdu['cost'] + 1, # Cost increases by 1 for each hop
                'sender_id': bpdu['sender_id']
            }
            if self._is_bpdu_superior(prospective_bpdu, potential_root_bpdu):
                potential_root_bpdu = prospective_bpdu
                potential_root_port = port

        # 2. Update self if a better path to the root was found
        self.root_id = potential_root_bpdu['root_id']
        self.cost_to_root = potential_root_bpdu['cost']
        self.root_port = potential_root_port

        # 3. Determine the final state for each port
        for port in self.ports:
            if self.root_id == self.bridge_id:
                # If I am the root, all my ports are Designated
                self.port_states[port] = self.PORT_DESIGNATED
            elif port == self.root_port:
                # This port is my Root Port (best path to the root)
                self.port_states[port] = self.PORT_ROOT
            else:
                # This is a non-root port. Is it Designated or Blocked?
                # Compare the BPDU I would send with the one I received on this port.
                my_bpdu = self._create_bpdu()
                neighbor_bpdu = self.received_bpdus.get(port)
                
                if self._is_bpdu_superior(my_bpdu, neighbor_bpdu):
                    # My BPDU is better, so I am the Designated bridge for this link.
                    self.port_states[port] = self.PORT_DESIGNATED
                else:
                    # My BPDU is worse, so I must block this port to prevent a loop.
                    self.port_states[port] = self.PORT_BLOCKED

    def generate_bpdu(self):
        """Generates the BPDU to be sent from this bridge."""
        return self._create_bpdu()

    def get_port_states(self):
        """Returns a copy of the current port states."""
        return self.port_states.copy()